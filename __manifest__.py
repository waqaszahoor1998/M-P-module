# -*- coding: utf-8 -*-
{
    'name': 'Muller & Phipps Custom Integration',
    'version': '19.0.1.0.0',
    'category': 'Custom',
    'summary': 'Custom Odoo integration for Muller & Phipps logistics and supply chain operations',
    'description': """
        Muller & Phipps Custom Integration Module
        ==========================================
        
        This module provides comprehensive customizations for Muller & Phipps operations:
        
        * Multi-warehouse management for global operations
        * Advanced logistics and shipment tracking
        * Reverse logistics workflow
        * Spare parts management
        * External ERP system integration
        * Custom reporting and analytics
        * Multi-channel sales and distribution
        * Supply chain automation workflows
    """,
    'author': 'Muller & Phipps',
    'website': 'https://www.mullerphipps.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'website',
        'sale',
        'sale_stock',
        'purchase',
        'purchase_stock',
        'stock',
        'stock_account',
        'delivery',
        'stock_delivery',
        'account',
        'product',
        'mail',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'views/partner_views.xml',
        'views/logistics_views.xml',
        'views/integration_views.xml',
        'views/delivery_carrier_views.xml',
        'views/picking_views.xml',
        'views/templates/tracking_templates.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'muller_phipps/static/src/js/*.js',
            'muller_phipps/static/src/css/*.css',
        ],
    },
}

