#!/bin/bash

BASE_PATH="addons-l10n_ar"

echo "🔎 Buscando 'account_reports' en __manifest__.py dentro de $BASE_PATH"
echo

FILES=$(find "$BASE_PATH" -type f -name "__manifest__.py" -exec grep -l '"account_reports"' {} \;)

if [ -z "$FILES" ]; then
    echo "✅ No se encontraron referencias a account_reports."
    exit 0
fi

echo "🛠 Comentando 'account_reports' en manifests..."

for FILE in $FILES; do
    echo "➡️  Procesando: $FILE"
    cp "$FILE" "$FILE.bak"

    sed -i 's/"account_reports"/#"account_reports"/g' "$FILE"
done

echo
echo "✅ Listo. Dependencias 'account_reports' comentadas."

