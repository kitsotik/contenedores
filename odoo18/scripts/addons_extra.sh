#!/bin/bash

## habilitar las funcionalidades de Contabilidad , instalar el módulo om_account_accountant de OdooMates.
git clone -b 18.0 https://github.com/odoomates/odooapps/ ./addons-extra/odoo-mates 

## Cybrosys
#git clone -b 18.0 https://github.com/CybroOdoo/CybroAddons /addons-extra/CybroAddons
#cp -r /opt/odoo18/extra-addons/CybroAddons/product_brand_sale /addons-extra/product_brand_sale
#cp -r /opt/odoo18/extra-addons/CybroAddons/product_brand_ecommerce /addons-extra/product_brand_ecommerce

## backup (auto_backup)
git clone -b 18.0 https://github.com/Yenthe666/auto_backup ./addons-extra/auto_backup
#chmod -R 777 /addons-extra/auto_backup

## modulo mercadolibre x moldeo
git clone -b 18.0 https://github.com/ctmil/meli_oerp ./addons-extra/meli_oerp
#pip3 install -r /addons-extra/meli_oerp/requirements.txt --break-system-packages

# pos_l10n_ar_identification
#git clone -b 18.0 https://github.com/kitsotik/odoo_extra-addons /opt/odoo18/extra-addons/tmp
#cp -r /opt/odoo18/extra-addons/tmp/pos_l10n_ar_identification /opt/odoo18/extra-addons/pos_l10n_ar_identification
#cp -r /opt/odoo18/extra-addons/tmp/website_floating_whatsapp_icon /opt/odoo18/extra-addons/website_floating_whatsapp_icon
#cp -r /opt/odoo18/extra-addons/tmp/currency_update_exchange_rate_bna /opt/odoo18/extra-addons/currency_update_exchange_rate_bna
#cp -r /opt/odoo18/extra-addons/tmp/l10n_ar_partner /opt/odoo18/extra-addons/l10n_ar_partner

ADDONS_PATH="addons-extra"

echo "🔎 Buscando defaults con _() incompatibles con Odoo 18..."
echo "📁 Addons path: $ADDONS_PATH"
echo

FILES=$(grep -R --include="*.py" -n "default=_(" "$ADDONS_PATH")

if [ -z "$FILES" ]; then
    echo "✅ No se encontraron defaults problemáticos."
    exit 0
fi

echo "⚠️ Se encontraron los siguientes archivos:"
echo "$FILES"
echo
read -p "¿Deseas aplicar el parche automáticamente? (s/N): " CONFIRM

if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
    echo "❌ Operación cancelada."
    exit 1
fi

echo
echo "🛠 Aplicando parches..."

echo "$FILES" | while IFS=: read -r FILE LINE CONTENT; do
    echo "➡️  Parcheando: $FILE"
    cp "$FILE" "$FILE.bak"

    sed -i \
        "s/default=_(/default=lambda self: self.env._(/g" \
        "$FILE"
done

echo
echo "✅ Parche aplicado."
echo "📦 Backups creados con extensión .bak"
echo
echo "➡️ Ahora ejecutá:"
echo "   odoo -u all  (o el módulo afectado)"


