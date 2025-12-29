# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MPIntegration(models.Model):
    """Base model for M&P integration configuration"""
    _name = 'mp.integration'
    _description = 'M&P Integration Configuration'
    _order = 'name'

    name = fields.Char(string='Integration Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    integration_type = fields.Selection([
        ('erp', 'External ERP'),
        ('wms', 'Warehouse Management System'),
        ('tms', 'Transportation Management System'),
        ('api', 'Custom API'),
    ], string='Integration Type', required=True)
    
    # Connection settings
    api_url = fields.Char(string='API URL', required=True)
    api_key = fields.Char(string='API Key', required=True)
    api_secret = fields.Char(string='API Secret')
    timeout = fields.Integer(string='Timeout (seconds)', default=30)
    
    # Sync configuration
    sync_frequency = fields.Selection([
        ('realtime', 'Real-time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('manual', 'Manual'),
    ], string='Sync Frequency', default='hourly', required=True)
    
    sync_direction = fields.Selection([
        ('inbound', 'Inbound Only'),
        ('outbound', 'Outbound Only'),
        ('bidirectional', 'Bidirectional'),
    ], string='Sync Direction', default='bidirectional', required=True)
    
    # Status tracking
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ], string='Last Sync Status', readonly=True)
    last_sync_message = fields.Text(string='Last Sync Message', readonly=True)
    
    # Related records
    sync_log_ids = fields.One2many('mp.integration.log', 'integration_id', string='Sync Logs')
    mapping_ids = fields.One2many('mp.field.mapping', 'integration_id', string='Field Mappings')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.constrains('api_url')
    def _check_api_url(self):
        for record in self:
            if record.api_url and not record.api_url.startswith(('http://', 'https://')):
                raise ValidationError('API URL must start with http:// or https://')
    
    def action_test_connection(self):
        """Test connection to external system"""
        self.ensure_one()
        try:
            # This will be implemented in the connector service
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test',
                    'message': 'Connection successful!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Connection test failed: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test Failed',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_sync_now(self):
        """Trigger manual synchronization"""
        self.ensure_one()
        # This will be implemented in the sync service
        _logger.info(f"Manual sync triggered for integration: {self.name}")
        return True


class MPIntegrationLog(models.Model):
    """Log entries for integration activities"""
    _name = 'mp.integration.log'
    _description = 'M&P Integration Log'
    _order = 'create_date desc'

    integration_id = fields.Many2one('mp.integration', string='Integration', required=True, ondelete='cascade')
    sync_date = fields.Datetime(string='Sync Date', default=fields.Datetime.now, required=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ], string='Status', required=True)
    operation_type = fields.Selection([
        ('sync', 'Synchronization'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ], string='Operation Type', required=True)
    model_name = fields.Char(string='Model')
    record_id = fields.Integer(string='Record ID')
    message = fields.Text(string='Message')
    error_details = fields.Text(string='Error Details')
    records_processed = fields.Integer(string='Records Processed', default=0)
    records_failed = fields.Integer(string='Records Failed', default=0)


class MPFieldMapping(models.Model):
    """Field mapping configuration between Odoo and external systems"""
    _name = 'mp.field.mapping'
    _description = 'M&P Field Mapping'
    _order = 'sequence, id'

    integration_id = fields.Many2one('mp.integration', string='Integration', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    odoo_field = fields.Char(string='Odoo Field', required=True)
    external_field = fields.Char(string='External Field', required=True)
    field_type = fields.Selection([
        ('char', 'Text'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('selection', 'Selection'),
        ('many2one', 'Many2One'),
        ('one2many', 'One2Many'),
        ('many2many', 'Many2Many'),
    ], string='Field Type', required=True)
    default_value = fields.Char(string='Default Value')
    required = fields.Boolean(string='Required', default=False)
    active = fields.Boolean(string='Active', default=True)

