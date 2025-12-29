# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SupplyChainWorkflow(models.AbstractModel):
    """Supply chain workflow automation"""
    _name = 'mp.supply.chain.workflow'
    _description = 'Supply Chain Workflow Service'
    
    def check_stock_levels(self, warehouse=None):
        """Check stock levels and trigger replenishment if needed"""
        try:
            warehouses = warehouse or self.env['stock.warehouse'].search([])
            replenishment_orders = []
            
            for wh in warehouses:
                if not wh.auto_replenishment:
                    continue
                
                # Get products in warehouse
                quants = self.env['stock.quant'].search([
                    ('location_id.warehouse_id', '=', wh.id),
                    ('quantity', '>', 0),
                ])
                
                products = quants.mapped('product_id')
                
                for product in products:
                    # Get current stock level
                    current_qty = sum(quants.filtered(lambda q: q.product_id == product).mapped('quantity'))
                    
                    # Check against reorder point
                    if wh.reorder_point and current_qty <= wh.reorder_point:
                        # Trigger replenishment
                        order = self.create_replenishment_order(wh, product, wh.min_stock_level - current_qty)
                        if order:
                            replenishment_orders.append(order)
            
            return replenishment_orders
        except Exception as e:
            _logger.error(f"Error checking stock levels: {str(e)}")
            raise UserError(f"Error checking stock levels: {str(e)}")
    
    def create_replenishment_order(self, warehouse, product, quantity):
        """Create replenishment order"""
        try:
            # Find preferred supply warehouse
            supply_warehouse = warehouse.preferred_supply_warehouse_ids[:1] if warehouse.preferred_supply_warehouse_ids else None
            
            if not supply_warehouse:
                # Use internal transfer from any warehouse with stock
                source_quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('quantity', '>', 0),
                    ('location_id.warehouse_id', '!=', warehouse.id),
                ], limit=1)
                
                if not source_quants:
                    _logger.warning(f"No stock available for replenishment of {product.name}")
                    return False
                
                source_warehouse = source_quants.location_id.warehouse_id
            else:
                source_warehouse = supply_warehouse
            
            # Create internal transfer
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', warehouse.id),
                ('code', '=', 'internal'),
            ], limit=1)
            
            if not picking_type:
                _logger.error(f"No internal picking type found for warehouse {warehouse.name}")
                return False
            
            # Create picking
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': source_warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'origin': f'Replenishment: {product.name}',
            })
            
            # Create move
            self.env['stock.move'].create({
                'name': f'Replenishment: {product.name}',
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': quantity,
                'location_id': source_warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'picking_id': picking.id,
                'mp_operation_type': 'replenishment',
            })
            
            # Confirm picking
            picking.action_confirm()
            
            return picking
        except Exception as e:
            _logger.error(f"Error creating replenishment order: {str(e)}")
            raise UserError(f"Error creating replenishment order: {str(e)}")
    
    def automate_cross_warehouse_transfer(self, source_warehouse, dest_warehouse, product, quantity):
        """Automate cross-warehouse transfer"""
        try:
            if not source_warehouse.allow_cross_warehouse_transfer:
                raise UserError(f"Cross-warehouse transfers not allowed for {source_warehouse.name}")
            
            if not dest_warehouse.allow_cross_warehouse_transfer:
                raise UserError(f"Cross-warehouse transfers not allowed for {dest_warehouse.name}")
            
            # Create internal transfer
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('code', '=', 'internal'),
            ], limit=1)
            
            if not picking_type:
                raise UserError(f"No internal picking type found for warehouse {dest_warehouse.name}")
            
            # Create picking
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': source_warehouse.lot_stock_id.id,
                'location_dest_id': dest_warehouse.lot_stock_id.id,
                'origin': f'Cross-warehouse transfer: {product.name}',
            })
            
            # Create move
            self.env['stock.move'].create({
                'name': f'Cross-warehouse transfer: {product.name}',
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': quantity,
                'location_id': source_warehouse.lot_stock_id.id,
                'location_dest_id': dest_warehouse.lot_stock_id.id,
                'picking_id': picking.id,
                'mp_operation_type': 'transfer',
            })
            
            # Create logistics operation
            logistics_op = self.env['mp.logistics.operation'].create({
                'operation_type': 'transfer',
                'picking_id': picking.id,
                'date': fields.Datetime.now(),
                'state': 'draft',
                'origin_warehouse_id': source_warehouse.id,
                'destination_warehouse_id': dest_warehouse.id,
            })
            picking.write({'mp_logistics_operation_id': logistics_op.id})
            
            # Confirm picking
            picking.action_confirm()
            
            return picking
        except Exception as e:
            _logger.error(f"Error automating cross-warehouse transfer: {str(e)}")
            raise UserError(f"Error automating cross-warehouse transfer: {str(e)}")
    
    def monitor_stock_alerts(self):
        """Monitor stock levels and send alerts"""
        try:
            warehouses = self.env['stock.warehouse'].search([
                ('auto_replenishment', '=', True),
            ])
            
            alerts = []
            for warehouse in warehouses:
                quants = self.env['stock.quant'].search([
                    ('location_id.warehouse_id', '=', warehouse.id),
                ])
                
                products = quants.mapped('product_id')
                
                for product in products:
                    current_qty = sum(quants.filtered(lambda q: q.product_id == product).mapped('quantity'))
                    
                    if warehouse.reorder_point and current_qty <= warehouse.reorder_point:
                        alerts.append({
                            'warehouse': warehouse.name,
                            'product': product.name,
                            'current_qty': current_qty,
                            'reorder_point': warehouse.reorder_point,
                        })
            
            # Send alerts (can be extended to send emails/notifications)
            if alerts:
                _logger.warning(f"Stock alerts: {alerts}")
                # TODO: Send email notifications or create activities
            
            return alerts
        except Exception as e:
            _logger.error(f"Error monitoring stock alerts: {str(e)}")
            raise UserError(f"Error monitoring stock alerts: {str(e)}")

