#!/bin/bash

if [ -z "$1" ]; then
    echo "Uso: $0 <nombre_de_base_de_datos>"
    exit 1
fi

# Variables de configuración
ODOO_APP_CONTAINER="odoo-app"
ODOO_DB="$1"  # Nombre de la base de datos pasado como argumento
DB_HOST="odoo-db"
DB_USER="odoo_db"
DB_PASSWORD="bgt56yhn*971"
HTTP_PORT=18069

docker exec -it "$ODOO_APP_CONTAINER" odoo --update=all --stop-after-init -d "$ODOO_DB" \
        --db_host="$DB_HOST" -r "$DB_USER" -w "$DB_PASSWORD" --http-port="$HTTP_PORT" --stop-after-init

# Lista de módulos separados por espacio
MODULES="account sale_management stock crm purchase point_of_sale mrp website website_sale"

# Iterar sobre los módulos
for MODULE in $MODULES; do
    echo "Instalando módulo: $MODULE"
    docker exec -it "$ODOO_APP_CONTAINER" odoo -i "$MODULE" -d "$ODOO_DB" \
        --db_host="$DB_HOST" -r "$DB_USER" -w "$DB_PASSWORD" --http-port="$HTTP_PORT" --stop-after-init
    
    if [ $? -ne 0 ]; then
        echo "Error al instalar el módulo: $MODULE. Saliendo..."
        exit 1
    else
        echo "Módulo $MODULE instalado correctamente."
        docker restart odoo-app
    fi
done

echo "Todos los módulos han sido instalados."
