# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestMPWorkflows(TransactionCase):
    """Test M&P workflows"""

    def setUp(self):
        super(TestMPWorkflows, self).setUp()
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        self.env.user.company_id = self.company.id
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
        })

    def test_logistics_workflow_service(self):
        """Test logistics workflow service"""
        workflow_service = self.env['mp.logistics.workflow']
        self.assertTrue(workflow_service)

    def test_supply_chain_workflow_service(self):
        """Test supply chain workflow service"""
        workflow_service = self.env['mp.supply.chain.workflow']
        self.assertTrue(workflow_service)

