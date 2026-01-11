#!/bin/bash

FILE="addons-l10n_ar/sale/sale_ux/views/sale_order_line_views.xml"

echo "🔎 Procesando archivo:"
echo "📄 $FILE"
echo

if [ ! -f "$FILE" ]; then
    echo "❌ El archivo no existe."
    exit 1
fi

cp "$FILE" "$FILE.bak"

# deferred_start_date
sed -i \
's|^[[:space:]]*<field name="deferred_start_date" string="Start Date" optional="hide"/>|<!-- <field name="deferred_start_date" string="Start Date" optional="hide"/> -->|g' \
"$FILE"

# deferred_end_date
sed -i \
's|^[[:space:]]*<field name="deferred_end_date" string="End Date" optional="hide"/>|<!-- <field name="deferred_end_date" string="End Date" optional="hide"/> -->|g' \
"$FILE"

echo "✅ Líneas comentadas correctamente (si no lo estaban)."
echo "📦 Backup creado: $FILE.bak"
