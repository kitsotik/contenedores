#!/bin/bash
#sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos.sh

rm -R /mnt/extra-addons

apt update -y
apt install git -y
apt install build-essential -y
apt install -y python3-m2crypto

## Adhoc product (replenishment cost / product planned price)
#git clone -b 17.0 https://github.com/ingadhoc/product /mnt/extra-addons/product

## OCA Reportes 
#git clone -b 17.0 https://github.com/OCA/reporting-engine /mnt/extra-addons/reporting-engine
#mv /mnt/extra-addons/reporting-engine/report_xlsx /mnt/extra-addons/report_xlsx

## OCA Account
#git clone -b 17.0 https://github.com/OCA/account-financial-reporting /mnt/extra-addons/oca-account-financial-reporting
#git clone -b 17.0 https://github.com/OCA/account-financial-tools /mnt/extra-addons/oca-account-financial-tools
#git clone -b 17.0 https://github.com/OCA/server-ux /mnt/extra-addons/server-ux

## OCA Pos
#git clone -b 17.0 https://github.com/OCA/pos /mnt/extra-addons/oca-pos
#mv /mnt/extra-addons/oca-pos/pos_order_to_sale_order /mnt/extra-addons/pos_order_to_sale_order
#mv /mnt/extra-addons/oca-pos/pos_stock_available_online /mnt/extra-addons/pos_stock_available_online
#mv /mnt/extra-addons/oca-pos/pos_order_reorder /mnt/extra-addons/pos_order_reorder
#mv /mnt/extra-addons/oca-pos/pos_default_partner /mnt/extra-addons/pos_default_partner

## OCA Stock 
#git clone -b 17.0 https://github.com/OCA/stock-logistics-availability /mnt/extra-addons/stock-logistics-availability
#mv /mnt/extra-addons/oca-stock/stock_available  /mnt/extra-addons/stock_available

## OCA Tools for removing Odoo branding
#git clone -b 17.0 https://github.com/OCA/server-brand /mnt/extra-addons/server-brand

## OCA ecommerce addons (website_sale_require_login,website_sale_product_brand,website_sale_hide_empty_category,)
#git clone -b 17.0 https://github.com/OCA/e-commerce /mnt/extra-addons/e-commerce

#git clone -b 15.0 https://github.com/OCA/product-attribute/tree/15.0/product_pricelist_supplierinfo

## OCA Agrega marcas a los productos *** mepa mejor del de cybrosys ?  permite en la web filtrar
# git clone -b 17.0 https://github.com/OCA/brand /mnt/extra-addons/brand

## enchula
#git clone -b 17.0 https://github.com/OCA/web/ /mnt/extra-addons/web
#mv /mnt/extra-addons/web/web_responsive /mnt/extra-addons/web_responsive

## backup (auto_backup)
#pip3 install paramiko pysftp
#git clone -b 17.0 https://github.com/Yenthe666/auto_backup /mnt/extra-addons/auto_backup
#chmod -R 777 /mnt/extra-addons/auto_backup

## modulo mercadolibre x moldeo
#git clone -b 17.0 https://github.com/ctmil/meli_oerp /mnt/extra-addons/meli_oerp
#pip3 install -r /mnt/extra-addons/meli_oerp/requirements.txt

#git clone -b 17.0 https://github.com/regaby/odoo-custom/ /mnt/extra-addons/pos-custom

## Cybrosys
#git clone -b 17.0 https://github.com/CybroOdoo/CybroAddons /mnt/extra-addons/CybroAddons
#mv /mnt/extra-addons/CybroAddons/product_brand_sale /mnt/extra-addons/product_brand_sale
#mv /mnt/extra-addons/CybroAddons/product_brand_ecommerce /mnt/extra-addons/product_brand_ecommerce

## Este módulo le permite crear una lista de precios de venta basada en los precios de información del proveedor del producto. Si lo desea, puede omitir la cantidad mínima en el artículo de la lista de precios.
## También podemos definir el margen de venta aplicado al precio de compra directamente en la información del proveedor. Para esto, debe agregar usuarios al grupo "Mostrar margen de venta en información del proveedor del producto".

## habilitar las funcionalidades de Contabilidad , instalar el módulo om_account_accountant de OdooMates.
#git clone -b 17.0 https://github.com/odoomates/om_account /mnt/odoo-mates
#git clone -b 17.0 https://github.com/odoomates/odooapps/ /mnt/extra-addons/odoo-mates