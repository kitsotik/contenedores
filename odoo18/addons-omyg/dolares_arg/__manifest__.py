{
    "name": "Dolares Argentina",
    "summary": "Fetch and update Argentine dollar rates from dolarapi.com and BNA website",
    "author": "Be OnlyOne",
    "maintainers": ["onlyone-odoo"],
    "website": "https://onlyone.odoo.com/",
    "license": "AGPL-3",
    "category": "Accounting",
    "version": "18.0.1.1.1",
    "development_status": "Production/Stable",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": ["requests", "bs4"],
        "bin": [],
    },
    "depends": ["account"],
    "data": [
        "views/res_config_settings_views.xml",
        "data/ir_cron.xml",
    ],
}
