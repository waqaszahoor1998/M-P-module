# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json
import logging
from werkzeug.exceptions import BadRequest, Unauthorized

_logger = logging.getLogger(__name__)


class MPAPIController(http.Controller):
    """REST API controller for M&P integration"""
    
    def _authenticate(self, api_key=None):
        """Authenticate API request"""
        if not api_key:
            api_key = request.httprequest.headers.get('X-API-Key')
        
        if not api_key:
            raise Unauthorized('API Key required')
        
        # Find integration by API key
        integration = request.env['mp.integration'].sudo().search([
            ('api_key', '=', api_key),
            ('active', '=', True),
        ], limit=1)
        
        if not integration:
            raise Unauthorized('Invalid API Key')
        
        return integration
    
    def _json_response(self, data, status=200):
        """Return JSON response"""
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
            status=status
        )
    
    @http.route('/api/mp/v1/health', type='http', auth='none', methods=['GET'], csrf=False)
    def health_check(self):
        """Health check endpoint"""
        return self._json_response({'status': 'ok', 'service': 'M&P Integration API'})
    
    @http.route('/api/mp/v1/sync', type='jsonrpc', auth='none', methods=['POST'], csrf=False)
    def trigger_sync(self, integration_id=None, model_name=None, direction=None):
        """Trigger synchronization"""
        try:
            api_key = request.httprequest.headers.get('X-API-Key')
            integration = self._authenticate(api_key)
            
            if integration_id and integration_id != integration.id:
                raise BadRequest('Integration ID mismatch')
            
            sync_service = request.env['mp.sync.service'].sudo()
            result = sync_service.sync_integration(integration, model_name, direction)
            
            return {
                'success': True,
                'message': 'Sync completed',
                'data': result,
            }
        except Exception as e:
            _logger.error(f"Sync API error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/api/mp/v1/partners', type='jsonrpc', auth='none', methods=['GET', 'POST'], csrf=False)
    def partners_api(self, partner_id=None, **kwargs):
        """Partners API endpoint"""
        try:
            api_key = request.httprequest.headers.get('X-API-Key')
            integration = self._authenticate(api_key)
            
            if request.httprequest.method == 'GET':
                # Get partner(s)
                if partner_id:
                    partner = request.env['res.partner'].sudo().browse(partner_id)
                    if not partner.exists():
                        raise BadRequest('Partner not found')
                    
                    mapping_service = request.env['mp.mapping.service'].sudo()
                    data = mapping_service.map_partner_to_external(integration, partner)
                    return {'success': True, 'data': data}
                else:
                    # List partners
                    domain = [('company_id', '=', integration.company_id.id)]
                    partners = request.env['res.partner'].sudo().search(domain, limit=100)
                    
                    mapping_service = request.env['mp.mapping.service'].sudo()
                    data = [mapping_service.map_partner_to_external(integration, p) for p in partners]
                    return {'success': True, 'data': data, 'count': len(data)}
            
            elif request.httprequest.method == 'POST':
                # Create/update partner
                partner_data = request.jsonrequest
                mapping_service = request.env['mp.mapping.service'].sudo()
                odoo_data = mapping_service.map_to_odoo(integration, 'res.partner', partner_data)
                
                external_id = partner_data.get('id')
                if external_id:
                    partner = request.env['res.partner'].sudo().search([
                        ('external_system_id', '=', str(external_id)),
                    ], limit=1)
                    if partner:
                        partner.write(odoo_data)
                    else:
                        odoo_data['external_system_id'] = str(external_id)
                        partner = request.env['res.partner'].sudo().create(odoo_data)
                else:
                    partner = request.env['res.partner'].sudo().create(odoo_data)
                
                return {
                    'success': True,
                    'data': {'id': partner.id, 'external_id': partner.external_system_id},
                }
        except Exception as e:
            _logger.error(f"Partners API error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/mp/v1/sale-orders', type='jsonrpc', auth='none', methods=['GET', 'POST'], csrf=False)
    def sale_orders_api(self, order_id=None, **kwargs):
        """Sale orders API endpoint"""
        try:
            api_key = request.httprequest.headers.get('X-API-Key')
            integration = self._authenticate(api_key)
            
            if request.httprequest.method == 'GET':
                if order_id:
                    order = request.env['sale.order'].sudo().browse(order_id)
                    if not order.exists():
                        raise BadRequest('Order not found')
                    
                    mapping_service = request.env['mp.mapping.service'].sudo()
                    data = mapping_service.map_sale_order_to_external(integration, order)
                    return {'success': True, 'data': data}
                else:
                    domain = [('company_id', '=', integration.company_id.id)]
                    orders = request.env['sale.order'].sudo().search(domain, limit=100)
                    
                    mapping_service = request.env['mp.mapping.service'].sudo()
                    data = [mapping_service.map_sale_order_to_external(integration, o) for o in orders]
                    return {'success': True, 'data': data, 'count': len(data)}
            
            elif request.httprequest.method == 'POST':
                order_data = request.jsonrequest
                mapping_service = request.env['mp.mapping.service'].sudo()
                odoo_data = mapping_service.map_to_odoo(integration, 'sale.order', order_data)
                
                external_id = order_data.get('id')
                if external_id:
                    order = request.env['sale.order'].sudo().search([
                        ('external_system_id', '=', str(external_id)),
                    ], limit=1)
                    if order:
                        order.write(odoo_data)
                    else:
                        odoo_data['external_system_id'] = str(external_id)
                        order = request.env['sale.order'].sudo().create(odoo_data)
                else:
                    order = request.env['sale.order'].sudo().create(odoo_data)
                
                return {
                    'success': True,
                    'data': {'id': order.id, 'external_id': order.external_system_id},
                }
        except Exception as e:
            _logger.error(f"Sale orders API error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/mp/v1/webhook', type='jsonrpc', auth='none', methods=['POST'], csrf=False)
    def webhook_handler(self, event_type=None, data=None, **kwargs):
        """Webhook handler for external system events"""
        try:
            api_key = request.httprequest.headers.get('X-API-Key')
            integration = self._authenticate(api_key)
            
            webhook_data = request.jsonrequest or {}
            event_type = event_type or webhook_data.get('event_type')
            data = data or webhook_data.get('data', {})
            
            _logger.info(f"Webhook received: {event_type} for integration {integration.name}")
            
            # Handle different event types
            if event_type == 'partner.updated':
                # Handle partner update
                sync_service = request.env['mp.sync.service'].sudo()
                sync_service.sync_inbound(integration, 'res.partner')
            
            elif event_type == 'order.created':
                # Handle order creation
                sync_service = request.env['mp.sync.service'].sudo()
                sync_service.sync_inbound(integration, 'sale.order')
            
            elif event_type == 'sync.request':
                # Handle sync request
                model_name = data.get('model')
                direction = data.get('direction')
                sync_service = request.env['mp.sync.service'].sudo()
                sync_service.sync_integration(integration, model_name, direction)
            
            return {
                'success': True,
                'message': f'Webhook {event_type} processed',
            }
        except Exception as e:
            _logger.error(f"Webhook error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/mp/track/<string:tracking_number>', type='http', auth='user', methods=['GET'], website=True)
    def track_shipment(self, tracking_number):
        """Display tracking information for M&P shipment"""
        try:
            # Find the delivery carrier with M&P type
            carrier = request.env['delivery.carrier'].sudo().search([
                ('delivery_type', '=', 'mp_logistics'),
                ('active', '=', True),
            ], limit=1)
            
            if not carrier:
                return request.render('muller_phipps.tracking_error', {
                    'error': 'M&P carrier not configured',
                    'tracking_number': tracking_number,
                })
            
            # Get tracking info from M&P API
            api_service = request.env['mp.cod.api.service'].sudo()
            tracking_info = api_service.get_tracking(carrier, tracking_number)
            
            if tracking_info.get('success'):
                # Format tracking data for display
                tracking_data = tracking_info.get('data', {})
                if isinstance(tracking_data, dict):
                    # Convert dict to readable format
                    formatted_info = json.dumps(tracking_data, indent=2)
                else:
                    formatted_info = str(tracking_data)
                
                return request.render('muller_phipps.tracking_result', {
                    'tracking_number': tracking_number,
                    'tracking_info': formatted_info,
                    'success': True,
                })
            else:
                return request.render('muller_phipps.tracking_error', {
                    'error': tracking_info.get('error', 'Unable to fetch tracking information'),
                    'tracking_number': tracking_number,
                })
        except Exception as e:
            _logger.error(f"Tracking error: {str(e)}")
            return request.render('muller_phipps.tracking_error', {
                'error': str(e),
                'tracking_number': tracking_number,
            })

