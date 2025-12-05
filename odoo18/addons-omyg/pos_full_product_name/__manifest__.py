# -*- coding: utf-8 -*-

{
    'name': "POS Full Product Name",

    'summary': """
        Display full product name in the POS module.
    """,

    'description': """
        This module helps the user to display full product name in the POS module.
    """,

    'author': "Agung Sepruloh",
    'website': "https://github.com/agungsepruloh",
    'maintainers': ['agungsepruloh'],
    'license': 'LGPL-3',
    'category': 'Point of Sale',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale'],

    # always loaded
    'data': [],
    # only loaded in demonstration mode
    'demo': [],

    'assets': {
        'point_of_sale._assets_pos': [
            'pos_full_product_name/static/src/**/*',
        ],
    },

    'images': ['static/description/banner.gif'],
    'application': True,
}
