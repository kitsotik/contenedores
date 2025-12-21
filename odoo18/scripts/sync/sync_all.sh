#!/bin/bash
cd ~/contenedores/odoo18/scripts/sync

echo "=== Iniciando sincronización $(date) ===" >> sync_all.log

python3 sync_suppliers.py >> sync_all.log 2>&1
python3 sync_customers.py >> sync_all.log 2>&1
python3 sync_categories.py >> sync_all.log 2>&1
python3 sync_products.py >> sync_all.log 2>&1
python3 sync_archived_products_only.py >> sync_all.log 2>&1
python3 sync_stock.py >> sync_all.log 2>&1
python3 sync_pricelists.py >> sync_all.log 2>&1

echo "=== Sincronización completada $(date) ===" >> sync_all.log

