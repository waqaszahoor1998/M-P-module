# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from typing import Dict, List, Optional, Any

_logger = logging.getLogger(__name__)


class MappingService(models.AbstractModel):
    """Service for mapping data between Odoo and external systems"""
    _name = 'mp.mapping.service'
    _description = 'Data Mapping Service'
    
    def get_field_mappings(self, integration, model_name):
        """Get field mappings for a specific model"""
        mappings = self.env['mp.field.mapping'].search([
            ('integration_id', '=', integration.id),
            ('active', '=', True),
        ])
        
        # Filter by model if needed (can be extended)
        result = {}
        for mapping in mappings:
            result[mapping.odoo_field] = {
                'external_field': mapping.external_field,
                'field_type': mapping.field_type,
                'default_value': mapping.default_value,
                'required': mapping.required,
            }
        return result
    
    def map_to_odoo(self, integration, model_name, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map external system data to Odoo format"""
        mappings = self.get_field_mappings(integration, model_name)
        odoo_data = {}
        
        for odoo_field, mapping_info in mappings.items():
            external_field = mapping_info['external_field']
            field_type = mapping_info['field_type']
            default_value = mapping_info.get('default_value')
            required = mapping_info.get('required', False)
            
            # Get value from external data
            value = external_data.get(external_field)
            
            # Use default if value is missing
            if value is None and default_value:
                value = self._convert_value(default_value, field_type)
            elif value is None and required:
                _logger.warning(f"Required field {external_field} missing in external data")
                continue
            
            # Convert value based on field type
            if value is not None:
                odoo_data[odoo_field] = self._convert_value(value, field_type)
        
        return odoo_data
    
    def map_to_external(self, integration, model_name, odoo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Odoo data to external system format"""
        mappings = self.get_field_mappings(integration, model_name)
        external_data = {}
        
        # Reverse mapping: odoo_field -> external_field
        for odoo_field, mapping_info in mappings.items():
            external_field = mapping_info['external_field']
            field_type = mapping_info['field_type']
            
            # Get value from Odoo data
            value = odoo_data.get(odoo_field)
            
            if value is not None:
                # Convert value based on field type for external system
                external_data[external_field] = self._convert_for_external(value, field_type)
        
        return external_data
    
    def _convert_value(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate type for Odoo"""
        if value is None:
            return None
        
        try:
            if field_type == 'integer':
                return int(value)
            elif field_type == 'float':
                return float(value)
            elif field_type == 'boolean':
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes', 'on')
            elif field_type == 'date':
                # Handle date string conversion
                if isinstance(value, str):
                    from datetime import datetime
                    return datetime.strptime(value, '%Y-%m-%d').date()
                return value
            elif field_type == 'datetime':
                # Handle datetime string conversion
                if isinstance(value, str):
                    from datetime import datetime
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            elif field_type == 'char':
                return str(value)
            else:
                return value
        except (ValueError, TypeError) as e:
            _logger.warning(f"Error converting value {value} to {field_type}: {str(e)}")
            return value
    
    def _convert_for_external(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate format for external system"""
        if value is None:
            return None
        
        try:
            if field_type in ('date', 'datetime'):
                # Convert to ISO format string
                if hasattr(value, 'isoformat'):
                    return value.isoformat()
                return str(value)
            elif field_type == 'boolean':
                return bool(value)
            elif field_type in ('many2one', 'one2many', 'many2many'):
                # Handle relational fields - extract ID
                if isinstance(value, models.BaseModel):
                    return value.id if hasattr(value, 'id') else None
                elif isinstance(value, (list, tuple)):
                    return [v.id if hasattr(v, 'id') else v for v in value]
                return value
            else:
                return value
        except Exception as e:
            _logger.warning(f"Error converting value {value} for external: {str(e)}")
            return value
    
    def map_partner_to_external(self, integration, partner) -> Dict[str, Any]:
        """Map partner record to external format"""
        odoo_data = {
            'name': partner.name,
            'email': partner.email,
            'phone': partner.phone,
            'mobile': partner.mobile,
            'street': partner.street,
            'street2': partner.street2,
            'city': partner.city,
            'zip': partner.zip,
            'country_id': partner.country_id.id if partner.country_id else None,
            'state_id': partner.state_id.id if partner.state_id else None,
            'is_company': partner.is_company,
            'mp_partner_code': partner.mp_partner_code,
            'mp_customer_type': partner.mp_customer_type,
            'distribution_channel': partner.distribution_channel,
        }
        return self.map_to_external(integration, 'res.partner', odoo_data)
    
    def map_sale_order_to_external(self, integration, sale_order) -> Dict[str, Any]:
        """Map sale order to external format"""
        odoo_data = {
            'name': sale_order.name,
            'partner_id': sale_order.partner_id.id,
            'date_order': sale_order.date_order,
            'amount_total': sale_order.amount_total,
            'state': sale_order.state,
            'order_line': [
                {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                }
                for line in sale_order.order_line
            ],
        }
        return self.map_to_external(integration, 'sale.order', odoo_data)
    
    def map_purchase_order_to_external(self, integration, purchase_order) -> Dict[str, Any]:
        """Map purchase order to external format"""
        odoo_data = {
            'name': purchase_order.name,
            'partner_id': purchase_order.partner_id.id,
            'date_order': purchase_order.date_order,
            'amount_total': purchase_order.amount_total,
            'state': purchase_order.state,
            'order_line': [
                {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                }
                for line in purchase_order.order_line
            ],
        }
        return self.map_to_external(integration, 'purchase.order', odoo_data)

