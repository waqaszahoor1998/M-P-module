# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    """Extended warehouse model for M&P multi-warehouse operations"""
    _inherit = 'stock.warehouse'

    # M&P specific fields
    mp_warehouse_code = fields.Char(string='M&P Warehouse Code', copy=False, index=True)
    region_id = fields.Many2one('mp.region', string='Region')
    
    # Warehouse type
    warehouse_type = fields.Selection([
        ('distribution', 'Distribution Center'),
        ('regional', 'Regional Warehouse'),
        ('local', 'Local Warehouse'),
        ('cross_dock', 'Cross-Dock Facility'),
    ], string='Warehouse Type', default='distribution')
    
    # Cross-warehouse transfer settings
    allow_cross_warehouse_transfer = fields.Boolean(string='Allow Cross-Warehouse Transfer', default=True)
    preferred_supply_warehouse_ids = fields.Many2many('stock.warehouse', 
                                                      'warehouse_supply_rel', 
                                                      'warehouse_id', 
                                                      'supply_warehouse_id',
                                                      string='Preferred Supply Warehouses')
    
    # Replenishment rules
    auto_replenishment = fields.Boolean(string='Auto Replenishment', default=False)
    min_stock_level = fields.Float(string='Minimum Stock Level')
    reorder_point = fields.Float(string='Reorder Point')
    
    # Integration
    external_system_id = fields.Char(string='External System ID')
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    
    _sql_constraints = [
        ('mp_warehouse_code_unique', 'unique(mp_warehouse_code)', 'M&P Warehouse Code must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Generate M&P warehouse code if not provided"""
        for vals in vals_list:
            if not vals.get('mp_warehouse_code'):
                vals['mp_warehouse_code'] = self.env['ir.sequence'].next_by_code('mp.warehouse.code') or 'NEW'
        return super(StockWarehouse, self).create(vals_list)


class StockLocation(models.Model):
    """Extended location model for M&P"""
    _inherit = 'stock.location'

    mp_location_code = fields.Char(string='M&P Location Code', copy=False)
    location_type = fields.Selection([
        ('storage', 'Storage'),
        ('picking', 'Picking Zone'),
        ('packing', 'Packing Zone'),
        ('shipping', 'Shipping Zone'),
        ('receiving', 'Receiving Zone'),
        ('quarantine', 'Quarantine'),
        ('repair', 'Repair Area'),
    ], string='Location Type', default='storage')
    
    # Capacity management
    max_capacity = fields.Float(string='Maximum Capacity')
    current_utilization = fields.Float(string='Current Utilization', compute='_compute_utilization', store=True)
    
    # Integration
    external_system_id = fields.Char(string='External System ID')
    
    @api.depends('quant_ids', 'max_capacity')
    def _compute_utilization(self):
        """Compute current utilization percentage"""
        for location in self:
            if location.max_capacity > 0:
                total_qty = sum(location.quant_ids.mapped('quantity'))
                location.current_utilization = (total_qty / location.max_capacity) * 100
            else:
                location.current_utilization = 0.0


class StockPicking(models.Model):
    """Extended picking model for M&P logistics"""
    _inherit = 'stock.picking'

    # M&P logistics operation link
    mp_logistics_operation_id = fields.Many2one('mp.logistics.operation', string='M&P Logistics Operation')
    
    # Cross-warehouse transfer
    is_cross_warehouse_transfer = fields.Boolean(string='Cross-Warehouse Transfer', compute='_compute_cross_warehouse', store=True)
    source_warehouse_id = fields.Many2one('stock.warehouse', string='Source Warehouse', compute='_compute_warehouses', store=True)
    dest_warehouse_id = fields.Many2one('stock.warehouse', string='Destination Warehouse', compute='_compute_warehouses', store=True)
    
    # Enhanced tracking
    mp_tracking_number = fields.Char(string='M&P Tracking Number')
    estimated_delivery_date = fields.Datetime(string='Estimated Delivery Date')
    
    # Integration
    external_system_id = fields.Char(string='External System ID')
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    
    @api.depends('location_id', 'location_dest_id')
    def _compute_cross_warehouse(self):
        """Determine if this is a cross-warehouse transfer"""
        for picking in self:
            source_wh = picking.location_id.warehouse_id
            dest_wh = picking.location_dest_id.warehouse_id
            picking.is_cross_warehouse_transfer = bool(source_wh and dest_wh and source_wh != dest_wh)
    
    @api.depends('location_id', 'location_dest_id')
    def _compute_warehouses(self):
        """Compute source and destination warehouses"""
        for picking in self:
            picking.source_warehouse_id = picking.location_id.warehouse_id
            picking.dest_warehouse_id = picking.location_dest_id.warehouse_id


class StockMove(models.Model):
    """Extended stock move for M&P operations"""
    _inherit = 'stock.move'

    # M&P specific tracking
    mp_operation_type = fields.Selection([
        ('normal', 'Normal'),
        ('replenishment', 'Replenishment'),
        ('transfer', 'Transfer'),
        ('return', 'Return'),
    ], string='M&P Operation Type', default='normal')
    
    # Integration
    external_system_id = fields.Char(string='External System ID')
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)

