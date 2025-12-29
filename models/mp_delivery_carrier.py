# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    """Extended delivery carrier for M&P logistics integration"""
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('mp_logistics', "M&P Logistics")
    ], ondelete={'mp_logistics': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    # M&P specific configuration
    mp_api_url = fields.Char(string="M&P API URL", groups="base.group_system",
                             help="Base URL for M&P COD API (default: http://mnpcourier.com/mycodapi)")
    mp_api_key = fields.Char(string="M&P Username", groups="base.group_system",
                             help="Username provided by M&P for API access")
    mp_api_secret = fields.Char(string="M&P Password", groups="base.group_system", password=True,
                                help="Password for M&P API access")
    mp_account_no = fields.Char(string="M&P Account Number", groups="base.group_system",
                                help="Account number provided by M&P for API access")
    mp_service_type = fields.Selection([
        ('overnight', 'Overnight (O)'),
        ('standard', 'Second Day (S)'),
    ], string="M&P Service Type", default='standard',
       help="Overnight: Next day delivery. Second Day: Delivery within 2 days")
    mp_auto_create_operation = fields.Boolean(
        string="Auto-create Logistics Operation",
        default=True,
        help="Automatically create M&P Logistics Operation when shipping is sent"
    )
    
    # Shipping rate calculation settings (in Pakistani Rupees - PKR)
    mp_base_fee = fields.Float(string="Base Shipping Fee (PKR)", default=500.0,
                               help="Base fee for all shipments in Pakistani Rupees (e.g., PKR 500)")
    mp_price_per_kg = fields.Float(string="Price per Kilogram (PKR)", default=250.0,
                                    help="Additional cost per kg of weight in Pakistani Rupees (e.g., PKR 250/kg)")
    mp_min_weight = fields.Float(string="Minimum Weight (kg)", default=0.5,
                                  help="Minimum weight for calculation (default: 0.5 kg)")
    mp_max_weight = fields.Float(string="Maximum Weight (kg)", default=30.0,
                                  help="Maximum weight for standard shipping (default: 30 kg)")
    mp_overweight_fee = fields.Float(string="Overweight Fee per kg (PKR)", default=500.0,
                                      help="Additional fee per kg if weight exceeds maximum in Pakistani Rupees")
    mp_cod_fee_percent = fields.Float(string="COD Fee (%)", default=2.0,
                                       help="Percentage fee for COD orders (e.g., 2% of order value)")
    mp_cod_min_fee = fields.Float(string="COD Minimum Fee (PKR)", default=250.0,
                                   help="Minimum COD fee in Pakistani Rupees even for small orders")
    
    def action_test_mp_api_connection(self):
        """Test M&P API connection"""
        self.ensure_one()
        
        if not self.mp_api_key or not self.mp_api_secret:
            raise UserError(_(
                "Please configure M&P Username and Password before testing the connection."
            ))
        
        # AccountNo is optional - if not provided, we'll try using username as fallback
        
        try:
            api_service = self.env['mp.cod.api.service']
            # Use Get_Cities endpoint (confirmed to exist in Swagger)
            # This is GET /api/Branches/Get_Cities with query parameters
            result = api_service.get_cities(self)
            
            if result.get('success'):
                cities_data = result.get('data', [])
                city_count = len(cities_data) if isinstance(cities_data, list) else 0
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _(
                            'M&P API connection is working!\n'
                            'Successfully retrieved %s city(ies) from M&P API.',
                            city_count
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                url_info = result.get('url', '')
                data_info = result.get('data', '')
                
                # Build detailed error message
                detailed_msg = f"M&P API connection failed:\n{error_msg}"
                if url_info:
                    detailed_msg += f"\n\nURL: {url_info}"
                if data_info and len(str(data_info)) < 200:  # Only show if not too long
                    detailed_msg += f"\n\nResponse: {data_info}"
                detailed_msg += "\n\nPlease check:\n"
                detailed_msg += "1. API URL is correct (should be: http://mnpcourier.com/mycodapi)\n"
                detailed_msg += "2. Username and Password are correct\n"
                detailed_msg += "3. Your account has API access enabled\n"
                detailed_msg += "4. The endpoint exists in the API (check Swagger docs)"
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Failed'),
                        'message': detailed_msg,
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            _logger.error(f"M&P API test connection error: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Error'),
                    'message': _(
                        'Error testing M&P API connection:\n%s\n\n'
                        'Please check your configuration and try again.',
                        str(e)
                    ),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def mp_logistics_rate_shipment(self, order):
        """Calculate shipping rate for M&P logistics
        
        Tries to get rate from M&P API first (if available), 
        then falls back to local calculation.
        """
        self.ensure_one()
        
        try:
            # If API credentials are configured, try to get rate from M&P API
            if self.mp_api_key and self.mp_api_secret:
                try:
                    # Calculate order details for API call
                    total_weight = 0.0
                    for line in order.order_line:
                        if line.product_id and not line.is_delivery:
                            product_weight = line.product_id.weight or 0.0
                            quantity = line.product_uom_qty or 0.0
                            total_weight += product_weight * quantity
                    
                    if total_weight <= 0:
                        total_weight = self.mp_min_weight or 0.5
                    
                    # Get destination city
                    destination_city = 'KARACHI'  # Default
                    if order.partner_shipping_id:
                        destination_city = order.partner_shipping_id.city or destination_city
                    
                    # Map service type
                    service_map = {
                        'overnight': 'O',
                        'standard': 'S',
                    }
                    service = service_map.get(self.mp_service_type, 'S')
                    
                    # Try to get rate from M&P API
                    api_service = self.env['mp.cod.api.service']
                    rate_result = api_service.get_shipping_rate(
                        self,
                        weight=total_weight,
                        destination_city=destination_city,
                        cod_amount=order.amount_total,
                        service=service
                    )
                    
                    if rate_result.get('success') and rate_result.get('price'):
                        api_price = rate_result.get('price')
                        _logger.info(f"M&P API rate: PKR {api_price} (from {rate_result.get('endpoint', 'API')})")
                        return {
                            'success': True,
                            'price': api_price,
                            'error_message': False,
                            'warning_message': False,
                            'source': 'api',
                        }
                    else:
                        _logger.info("M&P API rate endpoint not available, using local calculation")
                except Exception as api_error:
                    _logger.warning(f"M&P API rate calculation failed: {str(api_error)}, using local calculation")
            
            # Fallback to local calculation
            # Calculate base price (can be customized based on order weight, distance, etc.)
            base_price = self._mp_calculate_base_price(order)
            
            # Add service type multiplier
            # M&P has two service types: Overnight (O) and Second Day (S)
            service_multipliers = {
                'standard': 1.0,      # Second Day (S) - standard rate
                'overnight': 1.8,    # Overnight (O) - premium rate (80% more)
            }
            multiplier = service_multipliers.get(self.mp_service_type, 1.0)
            final_price = base_price * multiplier
            
            _logger.info(f"Local calculation: Service type: {self.mp_service_type}, Multiplier: {multiplier}x, Price: PKR {final_price}")
            
            # If fixed price is set, use that instead
            if self.fixed_price:
                final_price = self.fixed_price
            
            # Ensure minimum price (in PKR)
            if final_price <= 0:
                final_price = 500.0  # Minimum shipping cost in PKR
            
            return {
                'success': True,
                'price': final_price,
                'error_message': False,
                'warning_message': False,
                'source': 'local',
            }
        except Exception as e:
            _logger.error(f"M&P rate calculation error: {str(e)}")
            # Return a default price instead of failing (in PKR)
            default_price = self.fixed_price or 1250.0  # Default PKR 1250 (approx $25)
            return {
                'success': True,
                'price': default_price,
                'error_message': False,
                'warning_message': _('Using default shipping rate due to calculation error'),
                'source': 'default',
            }

    def mp_logistics_send_shipping(self, pickings):
        """Send shipping request to M&P and create logistics operation"""
        res = []
        
        for picking in pickings:
            try:
                # Get or create logistics operation (safely access)
                logistics_op = getattr(picking, 'mp_logistics_operation_id', None)
                
                if not logistics_op and self.mp_auto_create_operation:
                    # Create logistics operation via workflow service
                    workflow_service = self.env['mp.logistics.workflow']
                    logistics_op = workflow_service.create_shipment(picking)
                
                if not logistics_op:
                    raise UserError(_("No logistics operation found or created for picking %s", picking.name))
                
                # Set carrier on logistics operation
                logistics_op.write({
                    'carrier_id': self.id,
                })
                
                # If API credentials are configured, book shipment with M&P API
                if self.mp_api_key and self.mp_api_secret:
                    api_service = self.env['mp.cod.api.service']
                    booking_result = api_service.book_shipment(self, picking, logistics_op)
                    
                    if booking_result.get('success'):
                        # Update logistics operation with M&P order reference
                        order_reference_id = booking_result.get('order_reference_id', '')
                        logistics_op.write({
                            'mp_order_reference_id': order_reference_id,
                            'tracking_number': order_reference_id,  # Use M&P order reference as tracking
                            'tracking_url': self._mp_get_tracking_url(order_reference_id),
                        })
                        
                        # Post success message
                        picking.message_post(
                            body=_(
                                "M&P Shipment Booked Successfully\n"
                                "M&P Order Reference: %s\n"
                                "Message: %s",
                                order_reference_id,
                                booking_result.get('message', '')
                            )
                        )
                    else:
                        error_msg = booking_result.get('error', 'Unknown error')
                        api_response = booking_result.get('api_response', {})
                        
                        # Build detailed error message
                        error_details = [error_msg]
                        if 'destination' in error_msg.lower() or 'invalid' in error_msg.lower():
                            partner = picking.sale_id.partner_shipping_id if picking.sale_id else None
                            if partner:
                                error_details.append(_("Customer city: %s") % (partner.city or 'N/A'))
                                error_details.append(_("Note: M&P API only accepts Pakistani cities. Use Get_Cities API to see valid cities."))
                        
                        full_error_msg = "\n".join(error_details)
                        _logger.error(f"M&P API booking failed: {full_error_msg}")
                        _logger.error(f"M&P API response: {api_response}")
                        
                        # Continue with local tracking number generation
                        if not logistics_op.tracking_number:
                            tracking_number = self._mp_generate_tracking_number(picking)
                            logistics_op.write({
                                'tracking_number': tracking_number,
                                'tracking_url': self._mp_get_tracking_url(tracking_number),
                            })
                        picking.message_post(
                            body=_("M&P API booking failed: %s\n\nUsing local tracking number: %s", full_error_msg, logistics_op.tracking_number),
                            message_type='notification'
                        )
                else:
                    # No API configured, use local tracking number
                    if not logistics_op.tracking_number:
                        tracking_number = self._mp_generate_tracking_number(picking)
                        logistics_op.write({
                            'tracking_number': tracking_number,
                            'tracking_url': self._mp_get_tracking_url(tracking_number),
                        })
                    
                    picking.message_post(
                        body=_(
                            "M&P Logistics Operation Created (Local Mode)\n"
                            "Tracking Number: %s\n"
                            "Operation Reference: %s\n"
                            "Note: M&P API credentials not configured. Shipment not booked with M&P.",
                            logistics_op.tracking_number or 'N/A',
                            logistics_op.name
                        )
                    )
                
                # Update picking with M&P tracking (safely set fields)
                update_vals = {
                    'carrier_tracking_ref': logistics_op.tracking_number,
                }
                # Only set mp_tracking_number if the field exists
                if 'mp_tracking_number' in picking._fields:
                    update_vals['mp_tracking_number'] = logistics_op.tracking_number
                picking.write(update_vals)
                
                # Calculate shipping price
                order = picking.sale_id
                if order:
                    rate_result = self.mp_logistics_rate_shipment(order)
                    carrier_price = rate_result.get('price', 0.0)
                else:
                    carrier_price = self.fixed_price or 0.0
                
                res.append({
                    'exact_price': carrier_price,
                    'tracking_number': logistics_op.tracking_number or '',
                })
                
            except Exception as e:
                _logger.error(f"M&P send shipping error for picking {picking.name}: {str(e)}")
                raise UserError(_("Error sending shipping to M&P: %s", str(e)))
        
        return res

    def mp_logistics_get_tracking_link(self, picking):
        """Get tracking URL for M&P logistics"""
        # Safely access mp_logistics_operation_id (may not exist)
        logistics_op = getattr(picking, 'mp_logistics_operation_id', None)
        if logistics_op:
            if logistics_op.mp_order_reference_id:
                # Use M&P tracking URL
                return self._mp_get_tracking_url(logistics_op.mp_order_reference_id)
            elif logistics_op.tracking_url:
                return logistics_op.tracking_url
        
        # Fallback to picking tracking number (safely access)
        mp_tracking = getattr(picking, 'mp_tracking_number', None)
        if mp_tracking:
            return self._mp_get_tracking_url(mp_tracking)
        
        return '#'

    def mp_logistics_cancel_shipment(self, picking):
        """Cancel M&P logistics operation"""
        # Safely access mp_logistics_operation_id
        logistics_op = getattr(picking, 'mp_logistics_operation_id', None)
        if not logistics_op:
            raise UserError(_("No M&P logistics operation found for this picking"))
        
        # If M&P order reference exists, void it via API
        if logistics_op.mp_order_reference_id and self.mp_api_key and self.mp_api_secret:
            try:
                api_service = self.env['mp.cod.api.service']
                void_result = api_service.void_consignment(self, logistics_op.mp_order_reference_id)
                
                if void_result.get('success'):
                    logistics_op.action_cancel()
                    picking.message_post(
                        body=_(
                            'M&P Shipment Cancelled\n'
                            'M&P Order Reference: %s\n'
                            'Operation Reference: %s',
                            logistics_op.mp_order_reference_id,
                            logistics_op.name
                        )
                    )
                else:
                    error_msg = void_result.get('error', 'Unknown error')
                    raise UserError(_("Failed to void M&P consignment: %s", error_msg))
            except Exception as e:
                _logger.error(f"M&P API void error: {str(e)}")
                raise UserError(_("Error voiding M&P consignment: %s", str(e)))
        else:
            # Local cancellation only
            if logistics_op.state == 'draft':
                logistics_op.action_cancel()
                picking.message_post(body=_('M&P Logistics Operation #%s has been cancelled', logistics_op.name))
            else:
                raise UserError(_("Cannot cancel logistics operation in state: %s", logistics_op.state))
        
        picking.write({
            'carrier_tracking_ref': '',
            'carrier_price': 0.0,
        })

    def _mp_calculate_base_price(self, order):
        """
        Calculate realistic shipping price based on:
        1. Base fee (fixed cost for all shipments)
        2. Weight-based pricing (per kg)
        3. Service type multiplier (Overnight vs Second Day)
        4. COD fee (if order is COD)
        5. Overweight charges (if exceeds max weight)
        6. Distance/Zone (if territory/region data available)
        """
        base_price = 0.0
        
        # 1. Add base fee (minimum charge for all shipments)
        base_fee = self.mp_base_fee or 10.0
        base_price += base_fee
        
        # 2. Calculate weight-based pricing
        total_weight = 0.0
        try:
            for line in order.order_line:
                if line.product_id and not line.is_delivery:
                    # Skip delivery lines (they're not physical products)
                    product_weight = line.product_id.weight or 0.0
                    quantity = line.product_uom_qty or 0.0
                    total_weight += product_weight * quantity
        except Exception as e:
            _logger.warning(f"Error calculating weight: {str(e)}")
        
        # Ensure minimum weight
        if total_weight <= 0:
            total_weight = self.mp_min_weight or 0.5
        
        # Weight-based pricing (in PKR)
        price_per_kg = self.mp_price_per_kg or 250.0
        weight_cost = total_weight * price_per_kg
        base_price += weight_cost
        
        # 3. Overweight charges (if exceeds maximum weight) (in PKR)
        max_weight = self.mp_max_weight or 30.0
        overweight_fee = self.mp_overweight_fee or 500.0
        if total_weight > max_weight:
            overweight_kg = total_weight - max_weight
            base_price += overweight_kg * overweight_fee
            _logger.info(f"Overweight charge: {overweight_kg} kg × PKR {overweight_fee}/kg = PKR {overweight_kg * overweight_fee}")
        
        # 4. COD fee (if order has COD amount)
        # Check if order is COD by checking payment terms or delivery carrier COD setting
        if order.amount_total > 0:
            # Check if this is a COD order
            # M&P typically charges COD fee as percentage of order value
            cod_fee_percent = self.mp_cod_fee_percent or 2.0
            cod_min_fee = self.mp_cod_min_fee or 5.0
            
            # Calculate COD fee (in PKR)
            cod_fee = (order.amount_total * cod_fee_percent) / 100.0
            if cod_fee < cod_min_fee:
                cod_fee = cod_min_fee
            
            # Add COD fee to shipping cost
            base_price += cod_fee
            _logger.info(f"COD fee: {cod_fee_percent}% of PKR {order.amount_total} = PKR {cod_fee}")
        
        # 5. Territory/Region-based pricing (if available)
        partner_shipping = order.partner_shipping_id
        if partner_shipping:
            # Check if partner has territory (custom M&P field)
            territory = getattr(partner_shipping, 'territory_id', None)
            if territory:
                # Could add zone-based pricing here
                # Example: Remote areas might have additional charges
                pass
            
            # Check if partner has region (custom M&P field)
            region = getattr(partner_shipping, 'region_id', None)
            if region:
                # Could add region-based pricing here
                # Example: International shipping might have different rates
                pass
        
        # 6. Distance-based pricing (if origin/destination available)
        # This would require warehouse location and customer location
        # For now, we'll use a simple approach
        warehouse = order.warehouse_id
        if warehouse and partner_shipping:
            # Could calculate distance between warehouse and customer
            # For now, we'll skip this as it requires geocoding
            pass
        
            _logger.info(f"Base price calculation: Base=PKR {base_fee}, Weight={total_weight}kg × PKR {price_per_kg}/kg=PKR {weight_cost}, Total=PKR {base_price}")
        
        return base_price

    def _mp_generate_tracking_number(self, picking):
        """Generate M&P tracking number"""
        # Generate tracking number format: MP-TRK-YYYYMMDD-XXXXXX
        from datetime import datetime
        date_str = datetime.now().strftime('%Y%m%d')
        sequence = self.env['ir.sequence'].next_by_code('mp.tracking.number') or '000001'
        return f"MP-TRK-{date_str}-{sequence}"

    def _mp_get_tracking_url(self, tracking_number):
        """Get tracking URL for M&P logistics"""
        # Use Odoo controller to fetch and display tracking info
        # This avoids 404 errors from non-existent M&P tracking pages
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or 'http://localhost:8069'
        return f"{base_url}/mp/track/{tracking_number}"

