# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

_logger = logging.getLogger(__name__)


class ERPConnectorBase(ABC):
    """Base class for ERP connectors"""
    
    def __init__(self, integration):
        self.integration = integration
        self.api_url = integration.api_url
        self.api_key = integration.api_key
        self.api_secret = integration.api_secret
        self.timeout = integration.timeout or 30
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with external ERP system"""
        pass
    
    @abstractmethod
    def get_connection(self) -> requests.Session:
        """Get authenticated session"""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to external system"""
        pass
    
    @abstractmethod
    def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Fetch data from external system"""
        pass
    
    @abstractmethod
    def send_data(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to external system"""
        pass


class GenericRESTConnector(ERPConnectorBase):
    """Generic REST API connector for external ERP systems"""
    
    def __init__(self, integration):
        super().__init__(integration)
        self.session = None
        self.auth_token = None
    
    def authenticate(self) -> bool:
        """Authenticate with external ERP system using API key"""
        try:
            auth_url = f"{self.api_url}/auth" if not self.api_url.endswith('/') else f"{self.api_url}auth"
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key,
            }
            if self.api_secret:
                headers['X-API-Secret'] = self.api_secret
            
            response = requests.post(
                auth_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token') or data.get('access_token')
                return True
            else:
                _logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            _logger.error(f"Authentication error: {str(e)}")
            return False
    
    def get_connection(self) -> requests.Session:
        """Get authenticated session"""
        if not self.session:
            self.session = requests.Session()
            if self.auth_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'Content-Type': 'application/json',
                })
            else:
                self.session.headers.update({
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json',
                })
                if self.api_secret:
                    self.session.headers.update({'X-API-Secret': self.api_secret})
        return self.session
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to external system"""
        try:
            # Try to authenticate first
            if not self.authenticate():
                return {
                    'success': False,
                    'message': 'Authentication failed',
                }
            
            # Test endpoint (usually /health or /ping)
            test_endpoints = ['/health', '/ping', '/status', '/api/health']
            session = self.get_connection()
            
            for endpoint in test_endpoints:
                try:
                    url = f"{self.api_url.rstrip('/')}{endpoint}"
                    response = session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        return {
                            'success': True,
                            'message': 'Connection successful',
                            'data': response.json() if response.content else {},
                        }
                except:
                    continue
            
            return {
                'success': False,
                'message': 'Could not reach test endpoint',
            }
        except Exception as e:
            _logger.error(f"Connection test error: {str(e)}")
            return {
                'success': False,
                'message': str(e),
            }
    
    def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Fetch data from external system"""
        try:
            session = self.get_connection()
            url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json() if response.content else {},
                'status_code': response.status_code,
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error fetching data from {endpoint}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
            }
    
    def send_data(self, endpoint: str, data: Dict[str, Any], method: str = 'POST') -> Dict[str, Any]:
        """Send data to external system"""
        try:
            session = self.get_connection()
            url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            if method.upper() == 'POST':
                response = session.post(url, json=data, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = session.put(url, json=data, timeout=self.timeout)
            elif method.upper() == 'PATCH':
                response = session.patch(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json() if response.content else {},
                'status_code': response.status_code,
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error sending data to {endpoint}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
            }
    
    def delete_data(self, endpoint: str) -> Dict[str, Any]:
        """Delete data from external system"""
        try:
            session = self.get_connection()
            url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            response = session.delete(url, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json() if response.content else {},
                'status_code': response.status_code,
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error deleting data from {endpoint}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
            }


class ERPConnectorService(models.AbstractModel):
    """Service model for ERP connector operations"""
    _name = 'mp.erp.connector.service'
    _description = 'ERP Connector Service'
    
    def get_connector(self, integration):
        """Get appropriate connector instance based on integration type"""
        if integration.integration_type == 'erp':
            return GenericRESTConnector(integration)
        elif integration.integration_type == 'api':
            return GenericRESTConnector(integration)
        else:
            # Default to generic REST connector
            return GenericRESTConnector(integration)
    
    def test_integration_connection(self, integration):
        """Test connection for an integration"""
        connector = self.get_connector(integration)
        result = connector.test_connection()
        return result
    
    def fetch_from_external(self, integration, endpoint, params=None):
        """Fetch data from external system"""
        connector = self.get_connector(integration)
        return connector.fetch_data(endpoint, params)
    
    def send_to_external(self, integration, endpoint, data, method='POST'):
        """Send data to external system"""
        connector = self.get_connector(integration)
        return connector.send_data(endpoint, data, method)

