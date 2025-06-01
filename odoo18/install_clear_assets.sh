#!/bin/bash

if [ -z "$1" ]; then
    echo "Uso: $0 <nombre_base_de_datos>"
    exit 1
fi

ODOO_APP_CONTAINER="odoo-app"
ODOO_DB="$1"
ODOO_CONFIG="/etc/odoo/odoo.conf"  # Cambiar si tu config está en otro lado
ODOO_BIN_PATH="/usr/bin/odoo"  # <- este path debe ser correcto

echo "Iniciando Odoo en modo desarrollo para la base '$ODOO_DB'..."

docker exec -it "$ODOO_APP_CONTAINER" \
    python3 "$ODOO_BIN_PATH" -c "$ODOO_CONFIG" -d "$ODOO_DB" --dev=all
