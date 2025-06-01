#!/bin/bash

# Verifica que se proporcione una versión como argumento
if [ -z "$1" ]; then
    echo "No se proporcionó ninguna versión como argumento."
    exit 1
else
    echo "Se recibió la versión: $1"
fi

# Almacena el argumento como la versión
VERSION=$1


## OCA Reportes 
git clone -b $VERSION https://github.com/OCA/reporting-engine /opt/odoo/extra-addons-oca/reporting-engine

## OCA Account
git clone -b $VERSION https://github.com/OCA/account-financial-reporting /opt/odoo/extra-addons-oca/account-financial-reporting
git clone -b $VERSION https://github.com/OCA/account-financial-tools /opt/odoo/extra-addons-oca/account-financial-tools
git clone -b $VERSION https://github.com/OCA/server-ux /opt/odoo/extra-addons-oca/server-ux

## OCA Pos
git clone -b $VERSION https://github.com/OCA/pos /opt/odoo/extra-addons-oca/pos

## OCA Stock 
git clone -b $VERSION https://github.com/OCA/stock-logistics-availability /opt/odoo/extra-addons-oca/stock-logistics-availability
git clone -b $VERSION https://github.com/OCA/stock-logistics-workflow /opt/odoo/extra-addons-oca/stock-logistics-workflow

##
git clone -b $VERSION https://github.com/OCA/sale-workflow /opt/odoo/extra-addons-oca/sale-workflow

## OCA Tools for removing Odoo branding
git clone -b $VERSION https://github.com/OCA/server-brand /opt/odoo/extra-addons-oca/server-brand

## OCA ecommerce addons (website_sale_require_login,website_sale_product_brand,website_sale_hide_empty_category,)
git clone -b $VERSION https://github.com/OCA/e-commerce /opt/odoo/extra-addons-oca/e-commerce

## OCA Product attribute
git clone -b $VERSION https://github.com/OCA/product-attribute /opt/odoo/extra-addons-oca/product-attribute

## OCA Product Pack
git clone -b $VERSION https://github.com/OCA/product-pack /opt/odoo/extra-addons-oca/product-pack

## OCA Agrega marcas a los productos *** mepa mejor del de cybrosys ?  permite en la web filtrar
git clone -b $VERSION https://github.com/OCA/brand /opt/odoo/extra-addons-oca/brand

## OCA Web
git clone -b $VERSION https://github.com/OCA/web/ /opt/odoo/extra-addons-oca/web/
cd /opt/odoo/extra-addons-oca/web
git fetch origin pull/2704/head:PR2704
git checkout PR2704

## OCA Widget reconciliar
git clone -b $VERSION https://github.com/OCA/account-reconcile /opt/odoo/extra-addons-oca/account-reconcile

## OCA website
git clone -b $VERSION https://github.com/OCA/website /opt/odoo/extra-addons-oca/website

## OCA server-tools
git clone -b $VERSION https://github.com/OCA/server-tools /opt/odoo/extra-addons-oca/server-tools
pip3 install -r /opt/odoo/extra-addons-oca/server-tools/requirements.txt --break-system-packages