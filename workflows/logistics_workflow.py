# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class LogisticsWorkflow(models.AbstractModel):
    """Logistics workflow automation"""
    _name = 'mp.logistics.workflow'
    _description = 'Logistics Workflow Service'
    
    def automate_order_fulfillment(self, sale_order):
        """Automate order fulfillment process"""
        try:
            # Create logistics operation
            logistics_op = self.env['mp.logistics.operation'].create({
                'operation_type': 'shipment',
                'sale_order_id': sale_order.id,
                'date': fields.Datetime.now(),
                'state': 'draft',
            })
            
            # Create stock picking if not exists
            if not sale_order.picking_ids:
                sale_order.action_confirm()
            
            # Link picking to logistics operation
            if sale_order.picking_ids:
                picking = sale_order.picking_ids[0]
                picking.write({
                    'mp_logistics_operation_id': logistics_op.id,
                })
                logistics_op.write({
                    'picking_id': picking.id,
                    'origin_location_id': picking.location_id.id,
                    'destination_location_id': picking.location_dest_id.id,
                    'origin_warehouse_id': picking.location_id.warehouse_id.id if picking.location_id.warehouse_id else False,
                    'destination_warehouse_id': picking.location_dest_id.warehouse_id.id if picking.location_dest_id.warehouse_id else False,
                })
            
            # Create operation lines from sale order lines
            for line in sale_order.order_line:
                # Skip lines without products (sections, notes, etc.)
                if not line.product_id or line.display_type:
                    continue
                
                # Ensure UOM exists
                uom_id = line.product_uom_id.id if line.product_uom_id else line.product_id.uom_id.id
                
                self.env['mp.logistics.operation.line'].create({
                    'operation_id': logistics_op.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': uom_id,
                    'quantity': line.product_uom_qty or 0.0,
                    'unit_price': line.price_unit or 0.0,
                })
            
            return logistics_op
        except Exception as e:
            _logger.error(f"Error automating order fulfillment: {str(e)}")
            raise UserError(f"Error automating order fulfillment: {str(e)}")
    
    def create_shipment(self, picking):
        """Create shipment from picking"""
        try:
            logistics_op = picking.mp_logistics_operation_id
            if not logistics_op:
                # Create new logistics operation
                logistics_op = self.env['mp.logistics.operation'].create({
                    'operation_type': 'shipment',
                    'picking_id': picking.id,
                    'date': fields.Datetime.now(),
                    'state': 'draft',
                    'origin_location_id': picking.location_id.id,
                    'destination_location_id': picking.location_dest_id.id,
                    'origin_warehouse_id': picking.location_id.warehouse_id.id if picking.location_id.warehouse_id else False,
                    'destination_warehouse_id': picking.location_dest_id.warehouse_id.id if picking.location_dest_id.warehouse_id else False,
                })
                picking.write({'mp_logistics_operation_id': logistics_op.id})
            
            # Set carrier if available
            if picking.carrier_id:
                logistics_op.write({'carrier_id': picking.carrier_id.id})
            
            # Generate tracking number if carrier supports it
            if logistics_op.carrier_id and hasattr(logistics_op.carrier_id, 'get_tracking_link'):
                try:
                    tracking_info = logistics_op.carrier_id.get_tracking_link(picking)
                    if tracking_info:
                        logistics_op.write({
                            'tracking_number': tracking_info.get('tracking_number'),
                            'tracking_url': tracking_info.get('tracking_url'),
                        })
                except:
                    pass
            
            return logistics_op
        except Exception as e:
            _logger.error(f"Error creating shipment: {str(e)}")
            raise UserError(f"Error creating shipment: {str(e)}")
    
    def process_delivery_confirmation(self, picking):
        """Process delivery confirmation"""
        try:
            logistics_op = picking.mp_logistics_operation_id
            if logistics_op:
                logistics_op.action_deliver()
                
                # Update operation lines with delivered quantities
                # Use move_line_ids which contains the actual operations with quantity
                for move_line in picking.move_line_ids:
                    if move_line.quantity > 0:
                        for line in logistics_op.operation_line_ids:
                            if line.product_id == move_line.product_id:
                                line.quantity_delivered = move_line.quantity
                                break
        except Exception as e:
            _logger.error(f"Error processing delivery confirmation: {str(e)}")
            raise UserError(f"Error processing delivery confirmation: {str(e)}")
    
    def process_return(self, picking, return_reason=None):
        """Process return/reverse logistics"""
        try:
            logistics_op = self.env['mp.logistics.operation'].create({
                'operation_type': 'return',
                'picking_id': picking.id,
                'date': fields.Datetime.now(),
                'state': 'draft',
                'return_reason': return_reason,
                'origin_location_id': picking.location_dest_id.id,  # Reverse
                'destination_location_id': picking.location_id.id,  # Reverse
            })
            
            # Create return lines
            # Use move_line_ids which contains the actual operations with quantity
            for move_line in picking.move_line_ids:
                if move_line.quantity > 0:
                    self.env['mp.logistics.operation.line'].create({
                        'operation_id': logistics_op.id,
                        'product_id': move_line.product_id.id,
                        'product_uom_id': move_line.product_uom_id.id,
                        'quantity': move_line.quantity,
                        'quantity_returned': move_line.quantity,
                    })
            
            return logistics_op
        except Exception as e:
            _logger.error(f"Error processing return: {str(e)}")
            raise UserError(f"Error processing return: {str(e)}")


class StockPicking(models.Model):
    """Extended picking with workflow automation"""
    _inherit = 'stock.picking'
    
    def button_validate(self):
        """Override to trigger logistics workflow"""
        result = super(StockPicking, self).button_validate()
        
        # Trigger delivery confirmation workflow
        workflow_service = self.env['mp.logistics.workflow']
        for picking in self:
            if picking.state == 'done':
                workflow_service.process_delivery_confirmation(picking)
        
        return result


class SaleOrder(models.Model):
    """Extended sale order with logistics workflow"""
    _inherit = 'sale.order'
    
    def action_confirm(self):
        """Override to trigger logistics workflow"""
        result = super(SaleOrder, self).action_confirm()
        
        # Trigger order fulfillment workflow
        workflow_service = self.env['mp.logistics.workflow']
        for order in self:
            workflow_service.automate_order_fulfillment(order)
        
        return result

