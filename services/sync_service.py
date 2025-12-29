# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

_logger = logging.getLogger(__name__)


class SyncService(models.AbstractModel):
    """Service for synchronizing data between Odoo and external systems"""
    _name = 'mp.sync.service'
    _description = 'Data Synchronization Service'
    
    def sync_integration(self, integration, model_name=None, direction=None):
        """Synchronize data for an integration"""
        if not integration.active:
            raise UserError(f"Integration {integration.name} is not active")
        
        direction = direction or integration.sync_direction
        model_name = model_name or 'all'
        
        log_entry = self.env['mp.integration.log'].create({
            'integration_id': integration.id,
            'sync_date': fields.Datetime.now(),
            'status': 'success',
            'operation_type': 'sync',
            'model_name': model_name,
        })
        
        try:
            records_processed = 0
            records_failed = 0
            
            if direction in ('inbound', 'bidirectional'):
                result = self.sync_inbound(integration, model_name)
                records_processed += result.get('processed', 0)
                records_failed += result.get('failed', 0)
            
            if direction in ('outbound', 'bidirectional'):
                result = self.sync_outbound(integration, model_name)
                records_processed += result.get('processed', 0)
                records_failed += result.get('failed', 0)
            
            # Update log entry
            log_entry.write({
                'records_processed': records_processed,
                'records_failed': records_failed,
                'status': 'success' if records_failed == 0 else 'partial',
                'message': f"Processed {records_processed} records, {records_failed} failed",
            })
            
            # Update integration status
            integration.write({
                'last_sync_date': fields.Datetime.now(),
                'last_sync_status': 'success' if records_failed == 0 else 'partial',
                'last_sync_message': f"Processed {records_processed} records",
            })
            
            return {
                'success': True,
                'processed': records_processed,
                'failed': records_failed,
            }
        except Exception as e:
            _logger.error(f"Sync error for integration {integration.name}: {str(e)}")
            log_entry.write({
                'status': 'failed',
                'error_details': str(e),
                'message': f"Sync failed: {str(e)}",
            })
            integration.write({
                'last_sync_date': fields.Datetime.now(),
                'last_sync_status': 'failed',
                'last_sync_message': str(e),
            })
            raise UserError(f"Sync failed: {str(e)}")
    
    def sync_inbound(self, integration, model_name='all'):
        """Sync data from external system to Odoo"""
        connector_service = self.env['mp.erp.connector.service']
        mapping_service = self.env['mp.mapping.service']
        
        models_to_sync = self._get_models_to_sync(model_name)
        processed = 0
        failed = 0
        
        for model in models_to_sync:
            try:
                # Fetch data from external system
                endpoint = f"/api/{model.replace('.', '/')}"
                result = connector_service.fetch_from_external(integration, endpoint)
                
                if not result.get('success'):
                    _logger.error(f"Failed to fetch {model} from external system")
                    failed += 1
                    continue
                
                external_data = result.get('data', {})
                
                # Handle list of records
                if isinstance(external_data, list):
                    records = external_data
                elif isinstance(external_data, dict) and 'data' in external_data:
                    records = external_data['data']
                else:
                    records = [external_data]
                
                # Map and create/update records
                odoo_model = self.env[model]
                for record_data in records:
                    try:
                        mapped_data = mapping_service.map_to_odoo(integration, model, record_data)
                        
                        # Check if record exists by external_system_id
                        external_id = record_data.get('id') or record_data.get('external_id')
                        existing = None
                        
                        if external_id and hasattr(odoo_model, 'external_system_id'):
                            existing = odoo_model.search([
                                ('external_system_id', '=', str(external_id)),
                                ('company_id', '=', integration.company_id.id),
                            ], limit=1)
                        
                        if existing:
                            existing.write(mapped_data)
                        else:
                            mapped_data['external_system_id'] = str(external_id) if external_id else None
                            mapped_data['company_id'] = integration.company_id.id
                            odoo_model.create(mapped_data)
                        
                        processed += 1
                    except Exception as e:
                        _logger.error(f"Error processing record in {model}: {str(e)}")
                        failed += 1
                        continue
            except Exception as e:
                _logger.error(f"Error syncing {model}: {str(e)}")
                failed += 1
                continue
        
        return {'processed': processed, 'failed': failed}
    
    def sync_outbound(self, integration, model_name='all'):
        """Sync data from Odoo to external system"""
        connector_service = self.env['mp.erp.connector.service']
        mapping_service = self.env['mp.mapping.service']
        
        models_to_sync = self._get_models_to_sync(model_name)
        processed = 0
        failed = 0
        
        for model in models_to_sync:
            try:
                # Get records that need syncing
                odoo_model = self.env[model]
                domain = [('company_id', '=', integration.company_id.id)]
                
                # Only sync records that have been modified since last sync
                if integration.last_sync_date and hasattr(odoo_model, 'write_date'):
                    domain.append(('write_date', '>', integration.last_sync_date))
                
                records = odoo_model.search(domain, limit=100)  # Limit to avoid timeout
                
                for record in records:
                    try:
                        # Map record to external format
                        if model == 'res.partner':
                            external_data = mapping_service.map_partner_to_external(integration, record)
                        elif model == 'sale.order':
                            external_data = mapping_service.map_sale_order_to_external(integration, record)
                        elif model == 'purchase.order':
                            external_data = mapping_service.map_purchase_order_to_external(integration, record)
                        else:
                            # Generic mapping
                            record_data = record.read()[0]
                            external_data = mapping_service.map_to_external(integration, model, record_data)
                        
                        # Determine endpoint
                        endpoint = f"/api/{model.replace('.', '/')}"
                        
                        # Send to external system
                        if record.external_system_id:
                            # Update existing
                            endpoint = f"{endpoint}/{record.external_system_id}"
                            result = connector_service.send_to_external(integration, endpoint, external_data, method='PUT')
                        else:
                            # Create new
                            result = connector_service.send_to_external(integration, endpoint, external_data, method='POST')
                        
                        if result.get('success'):
                            # Update external_system_id if returned
                            if 'id' in result.get('data', {}):
                                record.write({'external_system_id': str(result['data']['id'])})
                            record.write({'last_sync_date': fields.Datetime.now()})
                            processed += 1
                        else:
                            _logger.error(f"Failed to sync {model} record {record.id}: {result.get('error')}")
                            failed += 1
                    except Exception as e:
                        _logger.error(f"Error syncing record {record.id} in {model}: {str(e)}")
                        failed += 1
                        continue
            except Exception as e:
                _logger.error(f"Error syncing {model}: {str(e)}")
                failed += 1
                continue
        
        return {'processed': processed, 'failed': failed}
    
    def _get_models_to_sync(self, model_name):
        """Get list of models to sync"""
        if model_name == 'all':
            return ['res.partner', 'sale.order', 'purchase.order', 'stock.picking']
        elif isinstance(model_name, str):
            return [model_name]
        elif isinstance(model_name, list):
            return model_name
        else:
            return []
    
    def resolve_conflict(self, integration, model_name, odoo_record, external_data, conflict_type='timestamp'):
        """Resolve conflicts between Odoo and external data"""
        if conflict_type == 'timestamp':
            # Use timestamp-based resolution
            odoo_date = odoo_record.write_date if hasattr(odoo_record, 'write_date') else None
            external_date = external_data.get('updated_at') or external_data.get('modified_date')
            
            if odoo_date and external_date:
                from datetime import datetime
                if isinstance(external_date, str):
                    external_date = datetime.fromisoformat(external_date.replace('Z', '+00:00'))
                
                # Use the most recent version
                if odoo_date > external_date:
                    return 'odoo'
                else:
                    return 'external'
        
        # Default: prefer external (can be configured)
        return 'external'

