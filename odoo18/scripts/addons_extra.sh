#!/bin/bash

## habilitar las funcionalidades de Contabilidad , instalar el módulo om_account_accountant de OdooMates.
git clone -b 18.0 https://github.com/odoomates/odooapps/ ./addons-extra/odoo-mates 

## modulo mercadolibre x moldeo
git clone -b 18.0 https://github.com/ctmil/meli_oerp ./addons-extra/meli_oerp
#pip3 install -r /addons-extra/meli_oerp/requirements.txt --break-system-packages

## Cybrosys
#git clone -b 18.0 https://github.com/CybroOdoo/CybroAddons /addons-extra/CybroAddons
#cp -r /opt/odoo18/extra-addons/CybroAddons/product_brand_sale /addons-extra/product_brand_sale
#cp -r /opt/odoo18/extra-addons/CybroAddons/product_brand_ecommerce /addons-extra/product_brand_ecommerce


