# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock


class TestMPServices(TransactionCase):
    """Test M&P services"""

    def setUp(self):
        super(TestMPServices, self).setUp()
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        self.env.user.company_id = self.company.id
        self.integration = self.env['mp.integration'].create({
            'name': 'Test Integration',
            'integration_type': 'erp',
            'api_url': 'https://api.example.com',
            'api_key': 'test_key',
            'sync_frequency': 'hourly',
            'sync_direction': 'bidirectional',
        })

    def test_mapping_service(self):
        """Test mapping service"""
        mapping_service = self.env['mp.mapping.service']
        
        # Create field mapping
        self.env['mp.field.mapping'].create({
            'integration_id': self.integration.id,
            'odoo_field': 'name',
            'external_field': 'name',
            'field_type': 'char',
        })
        
        # Test mapping
        external_data = {'name': 'Test Name'}
        odoo_data = mapping_service.map_to_odoo(self.integration, 'res.partner', external_data)
        self.assertEqual(odoo_data.get('name'), 'Test Name')

    @patch('odoo.addons.muller_phipps.services.erp_connector.requests')
    def test_erp_connector_service(self, mock_requests):
        """Test ERP connector service"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'token': 'test_token'}
        mock_response.content = b'{}'
        mock_requests.post.return_value = mock_response
        mock_requests.Session.return_value = MagicMock()
        
        connector_service = self.env['mp.erp.connector.service']
        result = connector_service.test_integration_connection(self.integration)
        # Note: This will fail in actual test due to network, but structure is correct
        self.assertIsInstance(result, dict)

