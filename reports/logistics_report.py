# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class LogisticsReport(models.AbstractModel):
    """Logistics performance reporting"""
    _name = 'mp.logistics.report'
    _description = 'Logistics Report Service'
    
    def get_logistics_performance(self, date_from=None, date_to=None, warehouse_ids=None):
        """Get logistics performance metrics"""
        date_from = date_from or (datetime.now() - timedelta(days=30)).date()
        date_to = date_to or datetime.now().date()
        
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        
        if warehouse_ids:
            domain.append(('origin_warehouse_id', 'in', warehouse_ids))
        
        operations = self.env['mp.logistics.operation'].search(domain)
        
        # Calculate metrics
        total_operations = len(operations)
        delivered = operations.filtered(lambda o: o.state == 'delivered')
        in_transit = operations.filtered(lambda o: o.state == 'in_transit')
        cancelled = operations.filtered(lambda o: o.state == 'cancelled')
        
        # Calculate average delivery time
        delivered_with_dates = delivered.filtered(lambda o: o.actual_delivery_date and o.date)
        avg_delivery_time = 0
        if delivered_with_dates:
            total_time = sum([
                (o.actual_delivery_date - o.date).total_seconds() / 3600
                for o in delivered_with_dates
            ])
            avg_delivery_time = total_time / len(delivered_with_dates)
        
        return {
            'total_operations': total_operations,
            'delivered': len(delivered),
            'in_transit': len(in_transit),
            'cancelled': len(cancelled),
            'delivery_rate': (len(delivered) / total_operations * 100) if total_operations > 0 else 0,
            'avg_delivery_time_hours': avg_delivery_time,
            'operations_by_type': self._get_operations_by_type(operations),
            'operations_by_warehouse': self._get_operations_by_warehouse(operations),
        }
    
    def _get_operations_by_type(self, operations):
        """Group operations by type"""
        result = {}
        for op_type in ['shipment', 'reverse', 'transfer', 'return', 'repair']:
            ops = operations.filtered(lambda o: o.operation_type == op_type)
            result[op_type] = len(ops)
        return result
    
    def _get_operations_by_warehouse(self, operations):
        """Group operations by warehouse"""
        result = {}
        warehouses = operations.mapped('origin_warehouse_id')
        for warehouse in warehouses:
            ops = operations.filtered(lambda o: o.origin_warehouse_id == warehouse)
            result[warehouse.name] = len(ops)
        return result


class SupplyChainReport(models.AbstractModel):
    """Supply chain efficiency reporting"""
    _name = 'mp.supply.chain.report'
    _description = 'Supply Chain Report Service'
    
    def get_supply_chain_metrics(self, date_from=None, date_to=None, warehouse_ids=None):
        """Get supply chain efficiency metrics"""
        date_from = date_from or (datetime.now() - timedelta(days=30)).date()
        date_to = date_to or datetime.now().date()
        
        # Get stock movements
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        
        if warehouse_ids:
            domain.append(('location_id.warehouse_id', 'in', warehouse_ids))
        
        moves = self.env['stock.move'].search(domain)
        
        # Calculate metrics
        total_moves = len(moves)
        completed_moves = moves.filtered(lambda m: m.state == 'done')
        replenishment_moves = moves.filtered(lambda m: m.mp_operation_type == 'replenishment')
        transfer_moves = moves.filtered(lambda m: m.mp_operation_type == 'transfer')
        
        # Calculate inventory turnover
        turnover_rate = self._calculate_inventory_turnover(warehouse_ids, date_from, date_to)
        
        return {
            'total_movements': total_moves,
            'completed_movements': len(completed_moves),
            'replenishment_orders': len(replenishment_moves),
            'transfers': len(transfer_moves),
            'completion_rate': (len(completed_moves) / total_moves * 100) if total_moves > 0 else 0,
            'inventory_turnover': turnover_rate,
            'warehouse_utilization': self._get_warehouse_utilization(warehouse_ids),
        }
    
    def _calculate_inventory_turnover(self, warehouse_ids, date_from, date_to):
        """Calculate inventory turnover rate"""
        # Simplified calculation
        # In production, this would be more sophisticated
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ]
        
        if warehouse_ids:
            domain.append(('location_id.warehouse_id', 'in', warehouse_ids))
        
        outgoing_moves = self.env['stock.move'].search(domain + [('location_dest_id.usage', '=', 'customer')])
        total_outgoing = sum(outgoing_moves.mapped('quantity_done'))
        
        # Average inventory (simplified)
        quants = self.env['stock.quant'].search([
            ('location_id.warehouse_id', 'in', warehouse_ids) if warehouse_ids else []
        ])
        avg_inventory = sum(quants.mapped('quantity')) / 2 if quants else 1
        
        return total_outgoing / avg_inventory if avg_inventory > 0 else 0
    
    def _get_warehouse_utilization(self, warehouse_ids):
        """Get warehouse utilization rates"""
        warehouses = self.env['stock.warehouse'].browse(warehouse_ids) if warehouse_ids else self.env['stock.warehouse'].search([])
        result = {}
        
        for warehouse in warehouses:
            locations = self.env['stock.location'].search([
                ('warehouse_id', '=', warehouse.id),
                ('usage', '=', 'internal'),
            ])
            
            total_capacity = sum(locations.mapped('max_capacity'))
            total_utilization = sum(locations.mapped('current_utilization'))
            
            result[warehouse.name] = {
                'utilization_percent': total_utilization / len(locations) if locations else 0,
                'total_capacity': total_capacity,
            }
        
        return result

