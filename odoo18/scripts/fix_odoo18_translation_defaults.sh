#!/bin/bash

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

echo "🛠 Aplicando parches automáticamente..."

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
