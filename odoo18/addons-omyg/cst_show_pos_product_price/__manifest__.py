{
    "name": "POS Show Product Price | Display Price on POS Product Cards",
    "summary": "Show product prices directly on the POS product grid for better visibility and faster selection.",
    "description": """
        This module enhances the Odoo Point of Sale interface by showing product prices directly below product names. 
        It improves visibility and speeds up sales by allowing cashiers and customers to view prices instantly without 
        extra clicks. Seamlessly integrated with Odoo, the module offers a simple configuration to enable or disable 
        price display, providing flexibility and a more efficient POS experience.
        
        Product Price POS || Combo Product Supported || Show Product Price On Product Scree || POS Product Screen Price Visible
    """,
    "author": "CodeSphere Tech",
    "website": "https://www.codespheretech.in/",
    "category": "Point of Sale",
    "version": "18.0.1.0.0",
    "sequence": 0,
    "currency": "USD",
    "price": "0.00",
    "depends": ["point_of_sale"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "cst_show_pos_product_price/static/src/**/*",
        ],
    },
    "images": ["static/description/Banner.png"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
