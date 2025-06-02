#!/bin/bash

# Validar que se pase el nombre de la base de datos como argumento
if [ -z "$1" ]; then
    echo "Uso: $0 <nombre_base_de_datos>"
    exit 1
fi

# Variables de configuración
ODOO_APP_CONTAINER="odoo-app"
ODOO_DB="$1"  # Nombre de la base de datos como argumento
DB_HOST="odoo-db"
DB_USER="odoo_db"
DB_PASSWORD="bgt56yhn*971"
HTTP_PORT=18069

# Lista de módulos separados por espacio
MODULES="web_responsive om_account_accountant account_reconcile_model_oca account_reconcile_oca purchase_unreconciled product_internal_code product_planned_price product_replenishment_cost_sale_margin product_prices_update product_currency account_financial_report payment_mercado_pago pos_mercado_pago"

# Iterar sobre los módulos
for MODULE in $MODULES; do
    echo "Verificando si el módulo '$MODULE' ya está instalado..."

    INSTALLED=$(docker exec -i "$ODOO_APP_CONTAINER" \
        env PGPASSWORD="$DB_PASSWORD" \
        psql -h "$DB_HOST" -U "$DB_USER" -d "$ODOO_DB" -t -c \
        "SELECT state FROM ir_module_module WHERE name = '$MODULE';" | tr -d '[:space:]')

    if [ "$INSTALLED" = "installed" ]; then
        echo "El módulo '$MODULE' ya está instalado. Saltando..."
        continue
    fi

    echo "Instalando módulo: $MODULE"
    docker exec -it "$ODOO_APP_CONTAINER" odoo -i "$MODULE" -d "$ODOO_DB" \
        --db_host="$DB_HOST" -r "$DB_USER" -w "$DB_PASSWORD" --http-port="$HTTP_PORT" --stop-after-init

    if [ $? -ne 0 ]; then
        echo "❌ Error al instalar el módulo: $MODULE. Saliendo..."
        exit 1
    else
        echo "✅ Módulo '$MODULE' instalado correctamente."
        docker restart "$ODOO_APP_CONTAINER"
    fi
done

echo "✅ Todos los módulos han sido procesados."
