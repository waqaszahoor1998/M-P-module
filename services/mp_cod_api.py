# -*- coding: utf-8 -*-

"""
M&P COD API Service
Integrates with M&P COD API for shipment booking, tracking, and reporting
API Documentation: https://mnpcourier.com/mycodapi/swagger/ui/index#!/
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

_logger = logging.getLogger(__name__)


class MPCodAPIService(models.AbstractModel):
    """Service for M&P COD API integration"""
    _name = 'mp.cod.api.service'
    _description = 'M&P COD API Service'

    # Base API URL (use HTTPS for production)
    BASE_API_URL = "https://mnpcourier.com/mycodapi"

    def _get_api_credentials(self, carrier):
        """Get API credentials from delivery carrier"""
        if not carrier.mp_api_url:
            # Use default base URL if not configured
            api_url = self.BASE_API_URL
        else:
            api_url = carrier.mp_api_url.rstrip('/')
            # Remove trailing /api if present, since endpoints already include 'api/'
            if api_url.endswith('/api'):
                api_url = api_url[:-4]  # Remove '/api'
        
        # M&P API uses username/password, not API key/secret
        # Map mp_api_key to username and mp_api_secret to password
        username = carrier.mp_api_key or ''
        password = carrier.mp_api_secret or ''
        account_no = carrier.mp_account_no or ''
        
        if not username or not password:
            raise UserError(_(
                "M&P API credentials are required. "
                "Please configure Username (API Key field) and Password (API Secret field) "
                "in the M&P Logistics delivery carrier settings."
            ))
        
        return {
            'api_url': api_url,
            'username': username,
            'password': password,
            'account_no': account_no,
        }

    def _format_phone_for_mp(self, phone: str) -> str:
        """
        Format phone number for M&P API
        M&P requires format: 03001234567 (11 digits, starts with 0, no dashes/spaces)
        """
        if not phone:
            return ''
        
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Handle different formats
        if not digits:
            return ''
        
        # If 10 digits, add leading 0 (e.g., 3001234567 -> 03001234567)
        if len(digits) == 10:
            digits = '0' + digits
        
        # If starts with country code (92 for Pakistan), remove it and add 0
        if digits.startswith('92') and len(digits) == 12:
            digits = '0' + digits[2:]
        
        # Ensure starts with 0 and max 11 digits
        if digits and not digits.startswith('0'):
            digits = '0' + digits
        
        # Return max 11 digits (M&P format)
        return digits[:11]
    
    def _make_api_request(self, endpoint: str, data: Dict[str, Any], carrier, max_retries: int = 3) -> Dict[str, Any]:
        """
        Make API request to M&P COD API with retry logic
        Retries on network errors, not on validation errors
        """
        credentials = self._get_api_credentials(carrier)
        url = f"{credentials['api_url']}/{endpoint.lstrip('/')}"
        
        # Add username and password to request data if not already present
        # (InsertBookingData includes them in the booking object, others need them added)
        if 'username' not in data:
            data['username'] = credentials['username']
        if 'password' not in data:
            data['password'] = credentials['password']
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }
                
                if attempt > 0:
                    _logger.info(f"M&P API Retry attempt {attempt + 1}/{max_retries} for {endpoint}")
                else:
                    _logger.info(f"M&P API Request to {url}: {json.dumps(data, indent=2)}")
                
                response = requests.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=30
                )
                
                _logger.info(f"M&P API Response Status: {response.status_code}")
                _logger.info(f"M&P API Response: {response.text}")
                
                response.raise_for_status()
                
                # Parse response
                try:
                    result = response.json()
                    return {
                        'success': True,
                        'data': result,
                        'status_code': response.status_code,
                    }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': 'Invalid JSON response',
                        'data': response.text,
                    }
                    
            except requests.exceptions.Timeout as e:
                last_error = f"Request timeout: {str(e)}"
                _logger.warning(f"M&P API Timeout (attempt {attempt + 1}/{max_retries}): {last_error}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                continue
                
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                _logger.warning(f"M&P API Connection Error (attempt {attempt + 1}/{max_retries}): {last_error}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            except requests.exceptions.HTTPError as e:
                # HTTP errors (4xx, 5xx) - don't retry, these are validation/server errors
                error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
                _logger.error(f"M&P API HTTP Error {response.status_code}: {error_detail}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {str(e)}",
                    'data': error_detail,
                    'url': url,  # Include URL in response for debugging
                }
                
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)}"
                _logger.error(f"M&P API Error (attempt {attempt + 1}/{max_retries}): {last_error}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
        
        # All retries failed
        _logger.error(f"M&P API failed after {max_retries} attempts: {last_error}")
        return {
            'success': False,
            'error': last_error or 'Unknown error after retries',
            'data': {},
        }

    def book_shipment(self, carrier, picking, logistics_operation) -> Dict[str, Any]:
        """
        Book a shipment with M&P COD API
        Endpoint: POST /api/Booking/InsertBookingData
        """
        # Get order and partner information
        order = picking.sale_id
        if not order:
            raise UserError(_("Picking must be linked to a sales order"))
        
        partner = order.partner_shipping_id
        if not partner:
            raise UserError(_("Sales order must have a shipping address"))
        
        # Calculate weight and pieces
        total_weight = 0.0
        pieces = 0
        product_details = []
        
        for move_line in picking.move_line_ids:
            if move_line.product_id:
                weight = move_line.product_id.weight or 0.0
                qty = move_line.quantity or 0.0
                total_weight += weight * qty
                pieces += int(qty)
                
                product_name = move_line.product_id.name
                if qty > 1:
                    product_details.append(f"{int(qty)}x {product_name}")
                else:
                    product_details.append(product_name)
        
        # Ensure minimum values
        if total_weight <= 0:
            total_weight = 0.5  # Default 0.5 kg
        if pieces <= 0:
            pieces = 1
        
        # Get destination city (standard field)
        destination_city = partner.city or ''
        if not destination_city:
            # Try to get from state (standard field)
            if partner.state_id:
                destination_city = partner.state_id.name or ''
            if not destination_city:
                destination_city = 'Karachi'  # Default
        
        # Validate city against M&P's city list (optional but recommended)
        # This helps catch invalid cities before sending to API
        if carrier.mp_api_key and carrier.mp_api_secret:
            try:
                cities_result = self.get_cities_all(carrier)  # Use Get_Cities_All for complete list
                if cities_result.get('success'):
                    # Extract cities from response structure: [{"City": ["City1", "City2", ...]}]
                    valid_cities = []
                    cities_list = cities_result.get('cities', [])
                    if cities_list:
                        # Cities are already in list format from get_cities_all
                        valid_cities = [str(city).lower() for city in cities_list if city]
                    else:
                        # Fallback: try to extract from data structure
                        cities_data = cities_result.get('data', [])
                        if isinstance(cities_data, list) and len(cities_data) > 0:
                            city_data = cities_data[0]
                            if isinstance(city_data, dict) and 'City' in city_data:
                                valid_cities = [str(city).lower() for city in city_data['City'] if city]
                    
                    # Check if city is valid (case-insensitive)
                    if valid_cities and destination_city.lower() not in valid_cities:
                        _logger.warning(
                            f"City '{destination_city}' may not be valid for M&P API. "
                            f"Valid cities include: {', '.join(valid_cities[:10])}..."
                        )
                        # Don't fail, just log warning - let API validate
            except Exception as e:
                # If validation fails, continue anyway (don't block booking)
                _logger.warning(f"Could not validate city against M&P API: {str(e)}")
        
        # Map service type to M&P API format
        # 'O' = Overnight, 'S' = Second Day
        service_map = {
            'overnight': 'O',
            'standard': 'S',
        }
        service = service_map.get(carrier.mp_service_type, 'S')
        
        # Prepare API request data
        # Standard Odoo fields (always exist): name, email, street, city, phone
        # Only use getattr for: mobile (may not exist in some versions) and custom fields
        raw_phone = getattr(partner, 'mobile', None) or partner.phone or ''
        mobile_no = self._format_phone_for_mp(raw_phone)
        
        # Build address - use street if available, otherwise city
        consignee_address = (partner.street or '')[:200] if partner.street else (partner.city or '')[:200] if partner.city else 'N/A'
        
        # Get remarks from logistics operation notes or order note
        remarks = logistics_operation.notes or order.note or ''
        
        # Make custRefNo unique by combining order name with picking name
        # M&P API requires custRefNo to be unique for one shipper
        # Format: SO00062-WH/OUT/00079 (order name + picking name)
        cust_ref_no = f"{order.name}-{picking.name}"[:100]  # Max 100 chars per API
        
        # Get AccountNo from carrier (use username as fallback)
        account_no = carrier.mp_account_no or carrier.mp_api_key or ''
        
        # Build API data according to Swagger specification
        api_data = {
            'username': carrier.mp_api_key or '',
            'password': carrier.mp_api_secret or '',
            'consigneeName': (partner.name or 'N/A')[:100],
            'consigneeAddress': consignee_address,
            'consigneeMobNo': mobile_no,
            'consigneeEmail': partner.email or '',
            'destinationCityName': destination_city,
            'pieces': int(pieces),  # Must be integer according to Swagger
            'weight': int(round(total_weight, 2)),  # Must be integer according to Swagger
            'codAmount': int(round(order.amount_total, 0)),  # Must be integer according to Swagger
            'custRefNo': cust_ref_no,  # Unique reference: order-picking
            'productDetails': ', '.join(product_details)[:600] if product_details else 'General Goods',
            'fragile': 'No',  # Can be enhanced to check product attributes
            'service': service,
            'remarks': remarks[:500] if remarks else '',  # Limit remarks length
            'insuranceValue': '0',  # Can be enhanced based on order value
            'AccountNo': account_no,  # Optional: Account number
            'InsertType': 0,  # Optional: Default to 0
            # Note: ReturnLocation should be omitted if not needed, or use valid location ID
            # 'ReturnLocation': 0,  # Removed - causes "Invalid Return Location" error if set to 0
            'subAccountId': 0,  # Optional: Default to 0
        }
        
        # Only add ReturnLocation if carrier has a valid return location configured
        if hasattr(carrier, 'mp_return_location_id') and carrier.mp_return_location_id:
            api_data['ReturnLocation'] = int(carrier.mp_return_location_id)
        
        # Optional: locationID - only for multi-location pickup users
        # If carrier has location_id configured, add it
        if hasattr(carrier, 'mp_location_id') and carrier.mp_location_id:
            api_data['locationID'] = str(carrier.mp_location_id)
        
        # Make API request
        result = self._make_api_request('api/Booking/InsertBookingData', api_data, carrier)
        
        if result.get('success'):
            response_data = result.get('data', [])
            if isinstance(response_data, list) and len(response_data) > 0:
                booking_result = response_data[0]
                # isSuccess is returned as string "true"/"false" by M&P API
                is_success = booking_result.get('isSuccess', '').lower() in ('true', '1') or booking_result.get('isSuccess') is True
                if is_success:
                    order_reference_id = booking_result.get('orderReferenceId', '')
                    return {
                        'success': True,
                        'order_reference_id': order_reference_id,
                        'message': booking_result.get('message', 'Order saved successfully.'),
                    }
                else:
                    # Get detailed error message from API
                    error_msg = booking_result.get('message', 'Unknown error')
                    # Add context about destination if it's a destination error
                    if 'destination' in error_msg.lower() or 'invalid' in error_msg.lower():
                        error_msg = f"{error_msg} (Destination city: {destination_city})"
                    return {
                        'success': False,
                        'error': error_msg,
                        'api_response': booking_result,  # Include full response for debugging
                    }
            else:
                return {
                    'success': False,
                    'error': 'Invalid API response format',
                    'api_response': response_data,
                }
        else:
            # Include more details from the failed request
            error_detail = result.get('error', 'Unknown error')
            return {
                'success': False,
                'error': error_detail,
                'api_response': result.get('data', {}),
            }

    def bulk_book_shipments(self, carrier, pickings: List) -> Dict[str, Any]:
        """
        Bulk book multiple shipments
        Endpoint: POST /api/Booking/InsertBulkBookingData
        """
        bookings = []
        
        for picking in pickings:
            order = picking.sale_id
            if not order:
                continue
            
            partner = order.partner_shipping_id
            if not partner:
                continue
            
            # Calculate weight and pieces
            total_weight = 0.0
            pieces = 0
            product_details = []
            
            for move_line in picking.move_line_ids:
                if move_line.product_id:
                    weight = move_line.product_id.weight or 0.0
                    qty = move_line.quantity or 0.0
                    total_weight += weight * qty
                    pieces += int(qty)
                    product_details.append(move_line.product_id.name)
            
            if total_weight <= 0:
                total_weight = 0.5
            if pieces <= 0:
                pieces = 1
            
            # Standard Odoo fields
            destination_city = partner.city or ''
            if not destination_city:
                if partner.state_id:
                    destination_city = partner.state_id.name or ''
                if not destination_city:
                    destination_city = 'Karachi'
            
            service_map = {
                'overnight': 'O',
                'standard': 'S',
            }
            service = service_map.get(carrier.mp_service_type, 'S')
            
            # Standard Odoo fields (always exist)
            raw_phone = getattr(partner, 'mobile', None) or partner.phone or ''
            mobile_no = self._format_phone_for_mp(raw_phone)
            consignee_address = (partner.street or '')[:200] if partner.street else (partner.city or '')[:200] if partner.city else 'N/A'
            
            # Make custRefNo unique by combining order name with picking name
            cust_ref_no = f"{order.name}-{picking.name}"[:100]  # Max 100 chars per API
            
            booking = {
                'consigneeName': (partner.name or 'N/A')[:100],
                'consigneeAddress': consignee_address,
                'consigneeMobNo': mobile_no,
                'consigneeEmail': partner.email or '',
                'destinationCityName': destination_city,
                'pieces': pieces,
                'weight': round(total_weight, 2),
                'codAmount': order.amount_total,
                'custRefNo': cust_ref_no,  # Unique reference: order-picking
                'productDetails': ', '.join(product_details)[:600] if product_details else 'General Goods',
                'fragile': 'No',
                'service': service,
                'remarks': order.note or '',
                'insuranceValue': '0',
            }
            
            bookings.append(booking)
        
        if not bookings:
            return {
                'success': False,
                'error': 'No valid shipments to book',
            }
        
        # Prepare bulk booking data
        api_data = {
            'bookings': bookings,
        }
        
        result = self._make_api_request('api/Booking/InsertBulkBookingData', api_data, carrier)
        return result

    def get_tracking(self, carrier, consignment_number: str) -> Dict[str, Any]:
        """
        Get tracking information for a consignment
        Endpoint: GET /api/Tracking/Consignment_Tracking
        According to Swagger: GET with query parameters (Username, password, consignment/consignmentNumber)
        Response can be JSON or XML (defaults to JSON)
        """
        credentials = self._get_api_credentials(carrier)
        
        # Validate consignment number
        if not consignment_number or not consignment_number.strip():
            return {
                'success': False,
                'error': 'Consignment number is required',
            }
        
        # Clean consignment number (remove spaces)
        consignment_number = consignment_number.strip()
        
        # Build URL with query parameters (GET request)
        url = f"{credentials['api_url']}/api/Tracking/Consignment_Tracking"
        
        # Try both parameter names (consignment and consignmentNumber)
        # Some API versions might use different parameter names
        params = {
            'Username': credentials['username'],  # Note: Capital U in Swagger
            'password': credentials['password'],
        }
        
        # Try 'consignment' first (most common)
        # If that doesn't work, try 'consignmentNumber'
        # Note: We'll try 'consignment' first, but the API might expect 'consignmentNumber'
        params['consignment'] = consignment_number
        
        try:
            _logger.info(f"M&P API GET Tracking Request to {url} with params")
            
            # Request JSON response (can be changed to XML if needed)
            headers = {
                'Accept': 'application/json',  # Request JSON response
            }
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            _logger.info(f"M&P API Tracking Response Status: {response.status_code}")
            _logger.info(f"M&P API Tracking Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response (try JSON first, fallback to XML if needed)
            try:
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'xml' in content_type:
                    # If XML, try to parse or return as text
                    _logger.warning("Received XML response, returning as text")
                    return {
                        'success': True,
                        'data': response.text,
                        'status_code': response.status_code,
                        'content_type': 'xml',
                    }
                else:
                    # Try JSON
                    result = response.json()
                    return {
                        'success': True,
                        'data': result,
                        'status_code': response.status_code,
                        'content_type': 'json',
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, return as text
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code,
                    'content_type': 'text',
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Tracking HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Tracking Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_tracking_location(self, carrier, consignment_number: str) -> Dict[str, Any]:
        """
        Get tracking location information
        Endpoint: GET /api/Tracking/Consignment_Tracking_Location
        According to Swagger: GET with query parameters (Username, password, locationID, consignment)
        Response can be JSON or XML (defaults to JSON)
        """
        credentials = self._get_api_credentials(carrier)
        
        # Build URL with query parameters (GET request)
        url = f"{credentials['api_url']}/api/Tracking/Consignment_Tracking_Location"
        params = {
            'Username': credentials['username'],  # Note: Capital U in Swagger
            'password': credentials['password'],
            'consignment': consignment_number,  # Note: parameter name is 'consignment' not 'consignmentNumber'
        }
        
        # Add locationID if available (optional but recommended)
        location_id = credentials.get('account_no') or credentials.get('username') or ''
        if location_id:
            params['locationID'] = location_id
        
        try:
            _logger.info(f"M&P API GET Tracking Location Request to {url} with params")
            
            # Request JSON response (can be changed to XML if needed)
            headers = {
                'Accept': 'application/json',  # Request JSON response
            }
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            _logger.info(f"M&P API Tracking Location Response Status: {response.status_code}")
            _logger.info(f"M&P API Tracking Location Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response (try JSON first, fallback to XML if needed)
            try:
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'xml' in content_type:
                    # If XML, try to parse or return as text
                    _logger.warning("Received XML response, returning as text")
                    return {
                        'success': True,
                        'data': response.text,
                        'status_code': response.status_code,
                        'content_type': 'xml',
                    }
                else:
                    # Try JSON
                    result = response.json()
                    return {
                        'success': True,
                        'data': result,
                        'status_code': response.status_code,
                        'content_type': 'json',
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, return as text
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code,
                    'content_type': 'text',
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Tracking Location HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Tracking Location Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def void_consignment(self, carrier, consignment_number: str) -> Dict[str, Any]:
        """
        Void a consignment
        Endpoint: POST /api/Booking/VoidConsignment
        According to Swagger: requires 'lsp' parameter with Username, password, locationID, consignmentNumberList
        """
        credentials = self._get_api_credentials(carrier)
        
        # Build request according to Swagger structure
        # Parameter name is 'lsp' containing the actual data
        lsp_data = {
            'Username': credentials['username'],  # Note: Capital U in Swagger
            'password': credentials['password'],
            'consignmentNumberList': [consignment_number],  # Array of consignment numbers
        }
        
        # Add locationID if available (optional)
        if hasattr(carrier, 'mp_location_id') and carrier.mp_location_id:
            lsp_data['locationID'] = str(carrier.mp_location_id)
        elif credentials.get('account_no'):
            # Use account_no as locationID if available
            lsp_data['locationID'] = credentials['account_no']
        
        # The API expects 'lsp' as the parameter name
        api_data = {
            'lsp': lsp_data
        }
        
        # Make direct API request (not using _make_api_request since structure is different)
        url = f"{credentials['api_url']}/api/Booking/VoidConsignment"
        
        try:
            _logger.info(f"M&P API VoidConsignment Request to {url}: {json.dumps(api_data, indent=2)}")
            
            response = requests.post(
                url,
                json=api_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                timeout=30
            )
            
            _logger.info(f"M&P API VoidConsignment Response Status: {response.status_code}")
            _logger.info(f"M&P API VoidConsignment Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response
            # Response structure: [{"isSuccess": "true"/"false", "message": "...", ...}]
            try:
                result = response.json()
                
                # Handle array response (same structure as InsertBookingData)
                if isinstance(result, list) and len(result) > 0:
                    void_result = result[0]
                    # isSuccess is returned as string "true"/"false" by M&P API
                    is_success = void_result.get('isSuccess', '').lower() in ('true', '1') or void_result.get('isSuccess') is True
                    
                    if is_success:
                        return {
                            'success': True,
                            'data': result,
                            'message': void_result.get('message', 'Consignment voided successfully.'),
                            'status_code': response.status_code,
                        }
                    else:
                        return {
                            'success': False,
                            'error': void_result.get('message', 'Void failed'),
                            'data': result,
                            'status_code': response.status_code,
                        }
                else:
                    # If not array, return as-is
                    return {
                        'success': True,
                        'data': result,
                        'status_code': response.status_code,
                    }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'data': response.text,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API VoidConsignment HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API VoidConsignment Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_branches(self, carrier) -> Dict[str, Any]:
        """
        Get list of branches
        Try both GET (with query params) and POST (with JSON body) methods
        """
        credentials = self._get_api_credentials(carrier)
        account_no = credentials['account_no'] or credentials['username'] or ''
        
        # Try GET method first (like Get_Cities)
        url_get = f"{credentials['api_url']}/api/Branches/Get_Branches"
        params_get = {
            'username': credentials['username'],
            'password': credentials['password'],
            'AccountNo': account_no,
        }
        
        try:
            _logger.info(f"M&P API GET Request to {url_get} with params")
            response = requests.get(url_get, params=params_get, headers={'Accept': 'application/json'}, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return {'success': True, 'data': result, 'status_code': response.status_code}
        except Exception as e:
            _logger.info(f"GET method failed, trying POST: {str(e)}")
        
        # Fallback to POST method
        url_post = f"{credentials['api_url']}/api/Branch/Get_Branches"
        api_data = {}
        result = self._make_api_request('api/Branch/Get_Branches', api_data, carrier)
        return result

    def get_locations(self, carrier) -> Dict[str, Any]:
        """
        Get list of locations
        Endpoint: GET /api/Locations/Get_locations (note: Locations plural, lowercase Get_locations)
        According to Swagger: GET with query parameters (username, password, AccountNo)
        """
        credentials = self._get_api_credentials(carrier)
        account_no = credentials['account_no'] or credentials['username'] or ''
        
        # Build URL with query parameters (GET request)
        # Note: Path is /api/Locations/Get_locations (Locations plural, lowercase Get_locations)
        url = f"{credentials['api_url']}/api/Locations/Get_locations"
        params = {
            'username': credentials['username'],  # Note: lowercase in Swagger
            'password': credentials['password'],
            'AccountNo': account_no,  # Required according to Swagger
        }
        
        try:
            _logger.info(f"M&P API GET Request to {url} with params")
            
            response = requests.get(
                url,
                params=params,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            _logger.info(f"M&P API Get Locations Response Status: {response.status_code}")
            _logger.info(f"M&P API Get Locations Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response
            try:
                result = response.json()
                return {
                    'success': True,
                    'data': result,
                    'status_code': response.status_code,
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'data': response.text,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Get Locations HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Get Locations Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_cities(self, carrier) -> Dict[str, Any]:
        """
        Get list of cities
        Endpoint: GET /api/Branches/Get_Cities
        Requires: username, password, AccountNo as query parameters
        """
        credentials = self._get_api_credentials(carrier)
        
        # Build URL with query parameters (GET request)
        url = f"{credentials['api_url']}/api/Branches/Get_Cities"
        
        # AccountNo might be same as username, or might be optional
        # Try username as AccountNo if not provided
        account_no = credentials['account_no'] or credentials['username'] or ''
        
        params = {
            'username': credentials['username'],
            'password': credentials['password'],
            'AccountNo': account_no,
        }
        
        # Log if using username as AccountNo fallback
        if not credentials['account_no']:
            _logger.info(f"AccountNo not provided, using username '{credentials['username']}' as AccountNo")
        
        try:
            _logger.info(f"M&P API GET Request to {url} with params: {params}")
            
            response = requests.get(
                url,
                params=params,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            _logger.info(f"M&P API Response Status: {response.status_code}")
            _logger.info(f"M&P API Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response
            # Response structure: [{"City": ["City1", "City2", ...]}]
            try:
                result = response.json()
                
                # Extract city list from nested structure
                cities_list = []
                if isinstance(result, list) and len(result) > 0:
                    city_data = result[0]
                    if isinstance(city_data, dict) and 'City' in city_data:
                        cities_list = city_data['City']
                
                return {
                    'success': True,
                    'data': result,  # Full response
                    'cities': cities_list,  # Extracted city list for convenience
                    'status_code': response.status_code,
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'data': response.text,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_qsr_report(self, carrier, month: int, year: int, location_id: str = None) -> Dict[str, Any]:
        """
        Get QSR Report
        Endpoint: POST /api/Reports/QSR_Report
        """
        api_data = {
            'MonthNumber': month,
            'year': year,
        }
        
        if location_id:
            api_data['locationID'] = location_id
        
        result = self._make_api_request('api/Reports/QSR_Report', api_data, carrier)
        return result

    def get_cities_all(self, carrier) -> Dict[str, Any]:
        """
        Get all cities (complete list)
        Endpoint: GET /api/Branches/Get_Cities_All
        According to Swagger: GET with query parameters (username, password, AccountNo)
        Similar to Get_Cities but might return more comprehensive data
        """
        credentials = self._get_api_credentials(carrier)
        
        # Build URL with query parameters (GET request)
        url = f"{credentials['api_url']}/api/Branches/Get_Cities_All"
        
        # AccountNo might be same as username, or might be optional
        account_no = credentials['account_no'] or credentials['username'] or ''
        
        params = {
            'username': credentials['username'],
            'password': credentials['password'],
            'AccountNo': account_no,
        }
        
        try:
            _logger.info(f"M&P API GET Request to {url} with params: {params}")
            
            response = requests.get(
                url,
                params=params,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            _logger.info(f"M&P API Get Cities All Response Status: {response.status_code}")
            _logger.info(f"M&P API Get Cities All Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response
            # Response structure: [{"City": ["City1", "City2", ...]}]
            try:
                result = response.json()
                
                # Extract city list from nested structure
                cities_list = []
                if isinstance(result, list) and len(result) > 0:
                    city_data = result[0]
                    if isinstance(city_data, dict) and 'City' in city_data:
                        cities_list = city_data['City']
                
                return {
                    'success': True,
                    'data': result,  # Full response
                    'cities': cities_list,  # Extracted city list for convenience
                    'status_code': response.status_code,
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'data': response.text,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Get Cities All HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Get Cities All Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def bulk_consignment_tracking(self, carrier, consignment_numbers: List[str]) -> Dict[str, Any]:
        """
        Track multiple consignments at once
        Endpoint: POST /api/Tracking/Bulk_Consignment_Tracking
        According to Swagger: POST with JSON body
        Structure: Username, Password, AccountNo, Consignments (array)
        """
        credentials = self._get_api_credentials(carrier)
        account_no = credentials.get('account_no') or credentials.get('username') or ''
        
        # Build API data according to Swagger structure
        # Swagger shows: Username (capital U), Password (capital P), AccountNo, Consignments (capital C)
        api_data = {
            'Username': credentials['username'],  # Note: Capital U in Swagger
            'Password': credentials['password'],  # Note: Capital P in Swagger
            'AccountNo': account_no,  # Note: Capital A in Swagger
            'Consignments': consignment_numbers,  # Note: Capital C, array of strings
        }
        
        url = f"{credentials['api_url']}/api/Tracking/Bulk_Consignment_Tracking"
        
        try:
            _logger.info(f"M&P API Bulk Tracking Request to {url}: {json.dumps(api_data, indent=2)}")
            
            response = requests.post(
                url,
                json=api_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                timeout=30
            )
            
            _logger.info(f"M&P API Bulk Tracking Response Status: {response.status_code}")
            _logger.info(f"M&P API Bulk Tracking Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response
            # Response structure: [{"City": ["City1", "City2", ...]}]
            try:
                result = response.json()
                
                # Extract city list from nested structure
                cities_list = []
                if isinstance(result, list) and len(result) > 0:
                    city_data = result[0]
                    if isinstance(city_data, dict) and 'City' in city_data:
                        cities_list = city_data['City']
                
                return {
                    'success': True,
                    'data': result,  # Full response
                    'cities': cities_list,  # Extracted city list for convenience
                    'status_code': response.status_code,
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'data': response.text,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Bulk Tracking HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Bulk Tracking Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_proof_of_delivery(self, carrier, consignment_number: str) -> Dict[str, Any]:
        """
        Get proof of delivery for a consignment
        Endpoint: GET /api/Reports/GetProofOfDelivery
        According to Swagger: GET with query parameters (username, password, consignmentNumber)
        Note: No AccountNo required according to Swagger
        """
        credentials = self._get_api_credentials(carrier)
        
        # Build URL with query parameters (GET request)
        url = f"{credentials['api_url']}/api/Reports/GetProofOfDelivery"
        
        params = {
            'username': credentials['username'],
            'password': credentials['password'],
            'consignmentNumber': consignment_number,  # Note: camelCase in Swagger
        }
        
        # Note: Swagger doesn't show AccountNo as required for this endpoint
        
        try:
            _logger.info(f"M&P API GET Proof of Delivery Request to {url} with params")
            
            response = requests.get(
                url,
                params=params,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            _logger.info(f"M&P API Proof of Delivery Response Status: {response.status_code}")
            _logger.info(f"M&P API Proof of Delivery Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response (could be JSON, PDF, or image)
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'json' in content_type:
                try:
                    result = response.json()
                    return {
                        'success': True,
                        'data': result,
                        'status_code': response.status_code,
                        'content_type': 'json',
                    }
                except json.JSONDecodeError:
                    return {
                        'success': True,
                        'data': response.text,
                        'status_code': response.status_code,
                        'content_type': 'text',
                    }
            elif 'pdf' in content_type or 'image' in content_type:
                # Return binary data for PDF/image
                return {
                    'success': True,
                    'data': response.content,  # Binary data
                    'status_code': response.status_code,
                    'content_type': content_type,
                }
            else:
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code,
                    'content_type': content_type,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Proof of Delivery HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Proof of Delivery Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_shipping_rate(self, carrier, weight: float, destination_city: str, cod_amount: float = 0.0, service: str = 'S') -> Dict[str, Any]:
        """
        Get shipping rate from M&P API (if available)
        This endpoint may or may not exist - check Swagger for:
        - Get_Price
        - Calculate_Rate
        - Get_Shipping_Rate
        - Get_Quote
        Or similar endpoints
        
        If the endpoint doesn't exist, this will return an error and you should use local calculation.
        
        Parameters:
        - weight: Weight in kg
        - destination_city: Destination city name
        - cod_amount: COD amount (optional)
        - service: Service type ('S' for Second Day, 'O' for Overnight)
        """
        credentials = self._get_api_credentials(carrier)
        
        # Try common rate calculation endpoints
        # NOTE: These endpoints may not exist - check Swagger first!
        possible_endpoints = [
            'api/Rates/Get_Price',
            'api/Rates/Calculate_Rate',
            'api/Booking/Get_Price',
            'api/Pricing/Get_Rate',
            'api/Quote/Get_Shipping_Rate',
        ]
        
        # Build request data
        api_data = {
            'username': credentials['username'],
            'password': credentials['password'],
            'weight': int(round(weight, 2)),
            'destinationCityName': destination_city,
            'service': service,
        }
        
        if cod_amount > 0:
            api_data['codAmount'] = int(round(cod_amount, 0))
        
        if credentials.get('account_no'):
            api_data['AccountNo'] = credentials['account_no']
        
        # Try each possible endpoint
        for endpoint in possible_endpoints:
            try:
                url = f"{credentials['api_url']}/{endpoint}"
                _logger.info(f"Trying rate endpoint: {url}")
                
                response = requests.post(
                    url,
                    json=api_data,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    },
                    timeout=10  # Short timeout for rate queries
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Check if response contains price/rate
                    if isinstance(result, list) and len(result) > 0:
                        rate_data = result[0]
                    else:
                        rate_data = result
                    
                    # Try to extract price from response
                    price = None
                    if 'price' in rate_data:
                        price = float(rate_data['price'])
                    elif 'rate' in rate_data:
                        price = float(rate_data['rate'])
                    elif 'shippingCost' in rate_data:
                        price = float(rate_data['shippingCost'])
                    elif 'amount' in rate_data:
                        price = float(rate_data['amount'])
                    
                    if price and price > 0:
                        _logger.info(f"M&P API rate calculation successful: PKR {price}")
                        return {
                            'success': True,
                            'price': price,
                            'data': rate_data,
                            'source': 'api',
                            'endpoint': endpoint,
                        }
                
            except requests.exceptions.HTTPError as e:
                # 404 means endpoint doesn't exist, try next one
                if response.status_code == 404:
                    _logger.debug(f"Endpoint {endpoint} not found (404), trying next...")
                    continue
                else:
                    _logger.warning(f"Rate endpoint {endpoint} error: {e}")
                    continue
            except Exception as e:
                _logger.debug(f"Rate endpoint {endpoint} error: {e}")
                continue
        
        # No rate API found or all endpoints failed
        _logger.info("No M&P rate calculation API endpoint found. Using local calculation.")
        return {
            'success': False,
            'error': 'Rate calculation API endpoint not found. Please check Swagger for available endpoints.',
            'source': 'local_fallback',
        }

    def update_booking(self, carrier, consignment_number: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing booking
        Endpoint: POST /api/Booking/UpdateBooking
        According to Swagger: POST with JSON body containing booking update data
        Note: Swagger shows 'consignmnetNumber' (typo - missing 'e') but we'll use correct spelling
        """
        credentials = self._get_api_credentials(carrier)
        account_no = credentials.get('account_no') or credentials.get('username') or ''
        
        # Build API data according to Swagger structure
        # Swagger shows: username, password, accountNo, consignmnetNumber, plus update fields
        api_data = {
            'username': credentials['username'],
            'password': credentials['password'],
            'accountNo': account_no,  # Note: lowercase 'a' in Swagger
            'consignmnetNumber': consignment_number,  # Note: Swagger has typo - missing 'e' in "consignment"
        }
        
        # Add update fields (consigneeName, consigneeAddress, consigneeMobNo, etc.)
        # Only include fields that are being updated
        allowed_fields = [
            'consigneeName', 'consigneeAddress', 'consigneeMobNo',
            'destinationCityName', 'pieces', 'weight', 'codAmount',
            'custRefNo', 'productDetails', 'remarks'
        ]
        
        for field in allowed_fields:
            if field in update_data:
                api_data[field] = update_data[field]
        
        url = f"{credentials['api_url']}/api/Booking/UpdateBooking"
        
        try:
            _logger.info(f"M&P API Update Booking Request to {url}: {json.dumps(api_data, indent=2)}")
            
            response = requests.post(
                url,
                json=api_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                timeout=30
            )
            
            _logger.info(f"M&P API Update Booking Response Status: {response.status_code}")
            _logger.info(f"M&P API Update Booking Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse response
            # Response structure: [{"isSuccess": "true"/"false", "message": "...", "orderReferenceId": "..."}]
            try:
                result = response.json()
                
                # Handle array response (same structure as InsertBookingData)
                if isinstance(result, list) and len(result) > 0:
                    update_result = result[0]
                    # isSuccess is returned as string "true"/"false" by M&P API
                    is_success = update_result.get('isSuccess', '').lower() in ('true', '1') or update_result.get('isSuccess') is True
                    
                    if is_success:
                        return {
                            'success': True,
                            'data': result,
                            'message': update_result.get('message', 'Booking updated successfully.'),
                            'order_reference_id': update_result.get('orderReferenceId', ''),
                            'status_code': response.status_code,
                        }
                    else:
                        return {
                            'success': False,
                            'error': update_result.get('message', 'Update failed'),
                            'data': result,
                            'status_code': response.status_code,
                        }
                else:
                    # If not array, return as-is
                    return {
                        'success': True,
                        'data': result,
                        'status_code': response.status_code,
                    }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'data': response.text,
                }
        except requests.exceptions.HTTPError as e:
            error_detail = response.text if hasattr(response, 'text') and response.text else str(e)
            _logger.error(f"M&P API Update Booking HTTP Error {response.status_code}: {error_detail}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {str(e)}",
                'data': error_detail,
                'url': url,
            }
        except Exception as e:
            _logger.error(f"M&P API Update Booking Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }

    def get_booking_summary(self, carrier, date_from: datetime, date_to: datetime, 
                           status: int = 2, location_id: str = None) -> Dict[str, Any]:
        """
        Get Booking Summary Report
        Endpoint: POST /api/Reports/BookingSummart_Report
        """
        api_data = {
            'dateFrom': date_from.isoformat(),
            'dateTo': date_to.isoformat(),
            'status': status,  # 1: Loadsheet generated, 2: Arrived at M&P, 3: Void
        }
        
        if location_id:
            api_data['locationID'] = location_id
        
        result = self._make_api_request('api/Reports/BookingSummart_Report', api_data, carrier)
        return result

