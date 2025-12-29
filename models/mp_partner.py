# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """Extended partner model for M&P distribution partners"""
    _inherit = 'res.partner'

    # Distribution channel fields
    distribution_channel = fields.Selection([
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('b2b', 'B2B'),
        ('carrier', 'Carrier'),
        ('independent', 'Independent Retail'),
    ], string='Distribution Channel')
    
    # Territory and region management
    territory_id = fields.Many2one('mp.territory', string='Territory')
    region_id = fields.Many2one('mp.region', string='Region')
    
    # Partner hierarchy for distribution
    parent_partner_id = fields.Many2one('res.partner', string='Parent Partner', 
                                       domain="[('is_company', '=', True)]")
    child_partner_ids = fields.One2many('res.partner', 'parent_partner_id', string='Child Partners')
    
    # M&P specific fields
    mp_partner_code = fields.Char(string='M&P Partner Code', copy=False, index=True)
    mp_customer_type = fields.Selection([
        ('distributor', 'Distributor'),
        ('reseller', 'Reseller'),
        ('end_customer', 'End Customer'),
        ('supplier', 'Supplier'),
    ], string='M&P Customer Type')
    
    # Integration fields
    external_system_id = fields.Char(string='External System ID', help='ID in external ERP system')
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    
    # Credit and payment terms
    mp_credit_limit = fields.Monetary(string='Credit Limit', currency_field='currency_id')
    mp_payment_terms_id = fields.Many2one('account.payment.term', string='M&P Payment Terms')
    
    _sql_constraints = [
        ('mp_partner_code_unique', 'unique(mp_partner_code)', 'M&P Partner Code must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Generate M&P partner code if not provided"""
        for vals in vals_list:
            if not vals.get('mp_partner_code') and vals.get('is_company'):
                vals['mp_partner_code'] = self.env['ir.sequence'].next_by_code('mp.partner.code') or 'NEW'
        return super(ResPartner, self).create(vals_list)


class MPTerritory(models.Model):
    """Territory management for M&P operations"""
    _name = 'mp.territory'
    _description = 'M&P Territory'
    _order = 'name'

    name = fields.Char(string='Territory Name', required=True)
    code = fields.Char(string='Territory Code', required=True)
    region_id = fields.Many2one('mp.region', string='Region', required=True)
    manager_id = fields.Many2one('res.users', string='Territory Manager')
    partner_ids = fields.One2many('res.partner', 'territory_id', string='Partners')
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Territory Code must be unique!'),
    ]


class MPRegion(models.Model):
    """Region management for M&P global operations"""
    _name = 'mp.region'
    _description = 'M&P Region'
    _order = 'name'

    name = fields.Char(string='Region Name', required=True)
    code = fields.Char(string='Region Code', required=True)
    country_ids = fields.Many2many('res.country', string='Countries')
    territory_ids = fields.One2many('mp.territory', 'region_id', string='Territories')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    active = fields.Boolean(string='Active', default=True)
    
    # M&P specific regions
    region_type = fields.Selection([
        ('dubai', 'Dubai - Middle East'),
        ('dallas', 'Dallas - United States'),
        ('pakistan', 'Pakistan'),
        ('sri_lanka', 'Sri Lanka'),
        ('other', 'Other'),
    ], string='Region Type')
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Region Code must be unique!'),
    ]

