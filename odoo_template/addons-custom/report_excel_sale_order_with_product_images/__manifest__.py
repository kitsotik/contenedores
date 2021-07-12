# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2020 GRIMMETTE,LLC <info@grimmette.com>

{
    'name': 'Sale Order with Product Images (XLSX)',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Sale Order with Product Images (XLSX)',     
    'price': 0.00,
    'currency': 'EUR',
    "license": "OPL-1",     
    'description': """
Sale Order with Product Images (XLSX)
====================================
Sale Order with Product Images in MS Excel format (XLSX)
Generate the Excel Report from a Template.
Report for Professional Reports Excel (XLSX, XLSM). 
    Odoo Report XLSX  Excel Report Excel Reports Accounting Reports Financial Report Financial Reports Stock Reports Inventory Reports \
    Dynamic Sale Analysis Reports Export Excel Export Project Reports Warehouse Reports Purchases Reports Marketing Reports Sales Reports \
    Report Designer Reports Designer Report Builder Reports Builder Product Report Customer Report POS Reports POS Report Analysis Report \
    BI Report BI Reports BI Business Intelligence Report Business Intelligence Reports BI Analytics BI Analytic Data Analysis
    """,
    'author': 'GRIMMETTE',
    'support': 'info@grimmette.com',
#     'live_test_url': "http://68.183.4.193:8069",
    'depends': [ 'base', 'account', 'sale', 'delivery'],
    'images': ['static/description/banner_rep.png'],
    'data': [
        'data/sale_order_with_product_images_xlsx.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    "pre_init_hook": "pre_init_check",
}



