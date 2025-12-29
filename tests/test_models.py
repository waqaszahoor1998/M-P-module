# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMPModels(TransactionCase):
    """Test M&P models"""

    def setUp(self):
        super(TestMPModels, self).setUp()
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        self.env.user.company_id = self.company.id

    def test_mp_integration_creation(self):
        """Test integration creation"""
        integration = self.env['mp.integration'].create({
            'name': 'Test Integration',
            'integration_type': 'erp',
            'api_url': 'https://api.example.com',
            'api_key': 'test_key',
            'sync_frequency': 'hourly',
            'sync_direction': 'bidirectional',
        })
        self.assertTrue(integration)
        self.assertEqual(integration.name, 'Test Integration')
        self.assertTrue(integration.active)

    def test_mp_integration_api_url_validation(self):
        """Test API URL validation"""
        with self.assertRaises(ValidationError):
            self.env['mp.integration'].create({
                'name': 'Test Integration',
                'integration_type': 'erp',
                'api_url': 'invalid_url',
                'api_key': 'test_key',
            })

    def test_mp_partner_code_generation(self):
        """Test M&P partner code generation"""
        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'is_company': True,
        })
        self.assertTrue(partner.mp_partner_code)
        self.assertTrue(partner.mp_partner_code.startswith('MP-P'))

    def test_mp_territory_creation(self):
        """Test territory creation"""
        region = self.env['mp.region'].create({
            'name': 'Test Region',
            'code': 'TR',
        })
        territory = self.env['mp.territory'].create({
            'name': 'Test Territory',
            'code': 'TT',
            'region_id': region.id,
        })
        self.assertTrue(territory)
        self.assertEqual(territory.region_id, region)

    def test_mp_logistics_operation_creation(self):
        """Test logistics operation creation"""
        from datetime import datetime
        operation = self.env['mp.logistics.operation'].create({
            'operation_type': 'shipment',
            'date': datetime.now(),
        })
        self.assertTrue(operation)
        self.assertTrue(operation.name)
        self.assertEqual(operation.state, 'draft')

