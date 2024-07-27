#!/bin/bash
#sudo docker exec -it -u root odoo-app sh /opt/odoo16/scripts/modulos.sh

rm -R /opt/odoo16/extra-addons

apt update -y
apt install git -y
apt install build-essential -y
apt install -y python3-m2crypto

## habilitar las funcionalidades de Contabilidad , instalar el módulo om_account_accountant de OdooMates.
git clone -b 16.0 https://github.com/odoomates/odooapps/ /opt/odoo16/extra-addons/odoo-mates

## Cybrosys
#git clone -b 16.0 https://github.com/CybroOdoo/CybroAddons /opt/odoo16/extra-addons/CybroAddons
#cp -r /opt/odoo16/extra-addons/CybroAddons/product_brand_sale /opt/odoo16/extra-addons/product_brand_sale
#cp -r /opt/odoo16/extra-addons/CybroAddons/product_brand_ecommerce /opt/odoo16/extra-addons/product_brand_ecommerce

## backup (auto_backup)
pip3 install paramiko pysftp
git clone -b 16.0 https://github.com/Yenthe666/auto_backup /opt/odoo16/extra-addons/auto_backup
chmod -R 777 /opt/odoo16/extra-addons/auto_backup

## modulo mercadolibre x moldeo
git clone -b 16.0 https://github.com/ctmil/meli_oerp /opt/odoo16/extra-addons/meli_oerp
pip3 install -r /opt/odoo16/extra-addons/meli_oerp/requirements.txt

# pos_l10n_ar_identification
git clone -b 16.0 https://github.com/kitsotik/odoo_extra-addons /opt/odoo16/extra-addons/odoo_extra-addons
cp -r /opt/odoo16/extra-addons/odoo_extra-addons/pos_l10n_ar_identification /opt/odoo16/extra-addons/pos_l10n_ar_identification
cp -r /opt/odoo16/extra-addons/odoo_extra-addons/website_floating_whatsapp_icon /opt/odoo16/extra-addons/website_floating_whatsapp_icon





