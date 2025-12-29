# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class MPLogisticsOperation(models.Model):
    """Logistics operations model for M&P"""
    _name = 'mp.logistics.operation'
    _description = 'M&P Logistics Operation'
    _order = 'date desc, id desc'

    name = fields.Char(string='Operation Reference', required=True, copy=False, readonly=True, 
                      default='New')
    date = fields.Datetime(string='Operation Date', required=True, default=fields.Datetime.now)
    operation_type = fields.Selection([
        ('shipment', 'Shipment'),
        ('reverse', 'Reverse Logistics'),
        ('transfer', 'Warehouse Transfer'),
        ('return', 'Return'),
        ('repair', 'Repair Service'),
    ], string='Operation Type', required=True)
    
    # Related records
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    
    # Shipment details
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier')
    tracking_number = fields.Char(string='Tracking Number')
    tracking_url = fields.Char(string='Tracking URL')
    mp_order_reference_id = fields.Char(string='M&P Order Reference', 
                                         help='Order reference ID returned from M&P COD API')
    
    # Locations
    origin_location_id = fields.Many2one('stock.location', string='Origin Location')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    origin_warehouse_id = fields.Many2one('stock.warehouse', string='Origin Warehouse')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination Warehouse')
    
    # Status tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)
    
    # Dates
    estimated_delivery_date = fields.Datetime(string='Estimated Delivery Date')
    actual_delivery_date = fields.Datetime(string='Actual Delivery Date')
    
    # Reverse logistics
    return_reason = fields.Text(string='Return Reason')
    return_authorization = fields.Char(string='Return Authorization Number')
    
    # Spare parts management
    is_spare_part = fields.Boolean(string='Spare Part Operation')
    spare_part_lifecycle_stage = fields.Selection([
        ('new', 'New'),
        ('in_use', 'In Use'),
        ('repair', 'In Repair'),
        ('refurbished', 'Refurbished'),
        ('disposed', 'Disposed'),
    ], string='Lifecycle Stage')
    
    # Line items
    operation_line_ids = fields.One2many('mp.logistics.operation.line', 'operation_id', string='Operation Lines')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Integration
    external_system_id = fields.Char(string='External System ID')
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create logistics operations with auto-generated reference"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mp.logistics.operation') or 'New'
        return super(MPLogisticsOperation, self).create(vals_list)
    
    def action_confirm(self):
        """Confirm logistics operation"""
        for record in self:
            if record.state == 'draft':
                record.state = 'in_transit'
    
    def action_deliver(self):
        """Mark as delivered"""
        for record in self:
            if record.state == 'in_transit':
                record.state = 'delivered'
                record.actual_delivery_date = fields.Datetime.now()
    
    def action_cancel(self):
        """Cancel logistics operation"""
        for record in self:
            record.state = 'cancelled'


class MPLogisticsOperationLine(models.Model):
    """Line items for logistics operations"""
    _name = 'mp.logistics.operation.line'
    _description = 'M&P Logistics Operation Line'

    operation_id = fields.Many2one('mp.logistics.operation', string='Operation', required=True, ondelete='cascade')
    spare_part_id = fields.Many2one('mp.spare.part', string='Spare Part', ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    quantity_delivered = fields.Float(string='Quantity Delivered', default=0.0)
    quantity_returned = fields.Float(string='Quantity Returned', default=0.0)
    
    # Serial numbers for tracking
    lot_ids = fields.Many2many('stock.lot', string='Serial Numbers/Lots')
    
    # Pricing (if applicable)
    unit_price = fields.Float(string='Unit Price')
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price


class MPSparePart(models.Model):
    """Spare parts management for M&P"""
    _name = 'mp.spare.part'
    _description = 'M&P Spare Part'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Spare Part Name', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    serial_number = fields.Char(string='Serial Number', index=True)
    
    # Lifecycle tracking
    lifecycle_stage = fields.Selection([
        ('new', 'New'),
        ('in_use', 'In Use'),
        ('repair', 'In Repair'),
        ('refurbished', 'Refurbished'),
        ('disposed', 'Disposed'),
    ], string='Lifecycle Stage', default='new', required=True, tracking=True)
    
    # Location tracking
    current_location_id = fields.Many2one('stock.location', string='Current Location')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    
    # Assignment
    assigned_to_partner_id = fields.Many2one('res.partner', string='Assigned To')
    assigned_date = fields.Date(string='Assigned Date')
    
    # Repair information
    repair_order_id = fields.Many2one('mp.repair.order', string='Repair Order')
    repair_count = fields.Integer(string='Repair Count', default=0)
    last_repair_date = fields.Date(string='Last Repair Date')
    
    # History
    operation_line_ids = fields.One2many('mp.logistics.operation.line', 'spare_part_id', string='Operation Lines')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    _sql_constraints = [
        ('serial_number_unique', 'unique(serial_number)', 'Serial Number must be unique!'),
    ]


class MPRepairOrder(models.Model):
    """Repair orders for spare parts"""
    _name = 'mp.repair.order'
    _description = 'M&P Repair Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Repair Order Number', required=True, copy=False, readonly=True,
                      default='New')
    date = fields.Date(string='Repair Date', required=True, default=fields.Date.today)
    
    # Spare part
    spare_part_id = fields.Many2one('mp.spare.part', string='Spare Part', required=True)
    product_id = fields.Many2one('product.product', string='Product', related='spare_part_id.product_id', store=True)
    
    # Repair details
    issue_description = fields.Text(string='Issue Description', required=True)
    repair_description = fields.Text(string='Repair Description')
    repair_cost = fields.Monetary(string='Repair Cost', currency_field='currency_id')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Technician
    technician_id = fields.Many2one('res.users', string='Technician')
    completion_date = fields.Date(string='Completion Date')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create repair orders with auto-generated reference"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mp.repair.order') or 'New'
        return super(MPRepairOrder, self).create(vals_list)
    
    def action_complete(self):
        """Complete repair order"""
        for record in self:
            if record.state == 'in_progress':
                record.state = 'completed'
                record.completion_date = fields.Date.today()
                if record.spare_part_id:
                    record.spare_part_id.lifecycle_stage = 'refurbished'
                    record.spare_part_id.repair_count += 1
                    record.spare_part_id.last_repair_date = fields.Date.today()

