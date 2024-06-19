#!/bin/bash
#sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos.sh

rm -R /mnt/extra-addons

apt update -y
apt install git -y
apt install build-essential -y
apt install -y python3-m2crypto

## OCA Reportes 
git clone -b 16.0 https://github.com/OCA/reporting-engine /mnt/extra-addons/oca-reporting-engine
cp -r /mnt/extra-addons/oca-reporting-engine/report_xlsx /mnt/extra-addons/report_xlsx
cp -r /mnt/extra-addons/oca-reporting-engine/report_xlsx_helper /mnt/extra-addons/oca-report_xlsx_helper

## OCA Account
git clone -b 16.0 https://github.com/OCA/account-financial-reporting /mnt/extra-addons/oca-account-financial-reporting
git clone -b 16.0 https://github.com/OCA/account-financial-tools /mnt/extra-addons/oca-account-financial-tools
git clone -b 16.0 https://github.com/OCA/server-ux /mnt/extra-addons/oca-server-ux

## OCA Pos
git clone -b 16.0 https://github.com/OCA/pos /mnt/extra-addons/oca-pos
#cp -r /mnt/extra-addons/oca-pos/pos_stock_available_online /mnt/extra-addons/oca-pos_stock_available_online
#cp -r /mnt/extra-addons/oca-pos/pos_order_reorder /mnt/extra-addons/oca-pos_order_reorder
#cp -r /mnt/extra-addons/oca-pos/pos_default_partner /mnt/extra-addons/oca-pos_default_partner
#cp -r /mnt/extra-addons/oca-pos/pos_order_to_sale_order /mnt/extra-addons/oca-pos_order_to_sale_order

## OCA Stock 
git clone -b 16.0 https://github.com/OCA/stock-logistics-availability /mnt/extra-addons/oca-stock-logistics-availability
cp -r /mnt/extra-addons/oca-stock-logistics-availability/stock_available /mnt/extra-addons/stock_available
git clone -b 16.0 https://github.com/OCA/stock-logistics-workflow /mnt/extra-addons/oca-stock-logistics-workflow
cp -r /mnt/extra-addons/oca-stock-logistics-workflow/stock_picking_invoice_link /mnt/extra-addons/stock_picking_invoice_link



##
git clone -b 16.0 https://github.com/OCA/sale-workflow /mnt/extra-addons/oca-sale-workflow
cp -r /mnt/extra-addons/oca-sale-workflow/sale_order_type /mnt/extra-addons/sale_order_type

## OCA Tools for removing Odoo branding
git clone -b 16.0 https://github.com/OCA/server-brand /mnt/extra-addons/oca-server-brand

## OCA ecommerce addons (website_sale_require_login,website_sale_product_brand,website_sale_hide_empty_category,)
git clone -b 16.0 https://github.com/OCA/e-commerce /mnt/extra-addons/oca-ecommerce

## OCA Product attribute
git clone -b 16.0 https://github.com/OCA/product-attribute /mnt/extra-addons/product-attribute
cp -r /mnt/extra-addons/product-attribute/product_pricelist_supplierinfo /mnt/extra-addons/oca-product_pricelist_supplierinfo
cp -r /mnt/extra-addons/product-attribute/product_manufacturer /mnt/extra-addons/oca-product_manufacturer

## OCA Agrega marcas a los productos *** mepa mejor del de cybrosys ?  permite en la web filtrar
git clone -b 16.0 https://github.com/OCA/brand /mnt/extra-addons/oca-brand

## OCA Web
git clone -b 16.0 https://github.com/OCA/web/ /mnt/extra-addons/oca-web
cp -r /mnt/extra-addons/oca-web/web_responsive /mnt/extra-addons/web_responsive
cp -r /mnt/extra-addons/oca-web/web_ir_actions_act_multi /mnt/extra-addons/web_ir_actions_act_multi

## OCA Widget reconciliar
git clone -b 16.0 https://github.com/OCA/account-reconcile /mnt/extra-addons/oca-account-reconcile

## OCA Product Attribute
git clone -b 16.0 https://github.com/OCA/product-attribute /mnt/extra-addons/oca-product-attribute

## backup (auto_backup)
pip3 install paramiko pysftp
git clone -b 16.0 https://github.com/Yenthe666/auto_backup /mnt/extra-addons/auto_backup
chmod -R 777 /mnt/extra-addons/auto_backup

## modulo mercadolibre x moldeo
git clone -b 16.0 https://github.com/ctmil/meli_oerp /mnt/extra-addons/meli_oerp
pip3 install -r /mnt/extra-addons/meli_oerp/requirements.txt

## habilitar las funcionalidades de Contabilidad , instalar el módulo om_account_accountant de OdooMates.
git clone -b 16.0 https://github.com/odoomates/odooapps/ /mnt/extra-addons/odoo-mates

## Cybrosys
#git clone -b 16.0 https://github.com/CybroOdoo/CybroAddons /mnt/extra-addons/CybroAddons
#cp -r /mnt/extra-addons/CybroAddons/product_brand_sale /mnt/extra-addons/product_brand_sale
#cp -r /mnt/extra-addons/CybroAddons/product_brand_ecommerce /mnt/extra-addons/product_brand_ecommerce

