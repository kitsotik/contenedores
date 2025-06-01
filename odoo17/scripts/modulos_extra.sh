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


## habilitar las funcionalidades de Contabilidad , instalar el módulo om_account_accountant de OdooMates.
git clone -b $VERSION https://github.com/odoomates/odooapps/ /opt/odoo/extra-addons/odoo-mates 

## Cybrosys
#git clone -b $VERSION https://github.com/CybroOdoo/CybroAddons /opt/odoo/extra-addons/CybroAddons
#cp -r /opt/odoo18/extra-addons/CybroAddons/product_brand_sale /opt/odoo/extra-addons/product_brand_sale
#cp -r /opt/odoo18/extra-addons/CybroAddons/product_brand_ecommerce /opt/odoo/extra-addons/product_brand_ecommerce

## backup (auto_backup)
pip3 install paramiko pysftp --break-system-packages
git clone -b $VERSION https://github.com/Yenthe666/auto_backup /opt/odoo/extra-addons/auto_backup
chmod -R 777 /opt/odoo/extra-addons/auto_backup

## modulo mercadolibre x moldeo
git clone -b $VERSION https://github.com/ctmil/meli_oerp /opt/odoo/extra-addons/meli_oerp
pip3 install -r /opt/odoo/extra-addons/meli_oerp/requirements.txt --break-system-packages

# pos_l10n_ar_identification
#git clone -b $VERSION https://github.com/kitsotik/odoo_extra-addons /opt/odoo18/extra-addons/tmp
#cp -r /opt/odoo18/extra-addons/tmp/pos_l10n_ar_identification /opt/odoo18/extra-addons/pos_l10n_ar_identification
#cp -r /opt/odoo18/extra-addons/tmp/website_floating_whatsapp_icon /opt/odoo18/extra-addons/website_floating_whatsapp_icon
#cp -r /opt/odoo18/extra-addons/tmp/currency_update_exchange_rate_bna /opt/odoo18/extra-addons/currency_update_exchange_rate_bna
#cp -r /opt/odoo18/extra-addons/tmp/l10n_ar_partner /opt/odoo18/extra-addons/l10n_ar_partner



