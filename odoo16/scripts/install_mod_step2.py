import xmlrpc.client

# Configuración de conexión
url = 'http://localhost:8069'  # URL del servidor Odoo
db = 'o16db'
username = 'admin'
password = 'bgt56yhn*971'

# Conexión común
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

# Conexión de objetos
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Lista de módulos a instalar
modules_to_install = [
    'om_account_accountant',
    'l10n_ar',
    'l10n_ar_afipws',
    'l10n_ar_afipws_caea',
    'l10n_ar_afipws_fe',
    'l10n_ar_bank',
    'l10n_ar_pos_afipws_fe',
    'l10n_ar_purchase',
    'l10n_ar_purchase_stock',
    'l10n_ar_reports',
    'l10n_ar_sale',
    'l10n_ar_sale_order_type',
    'l10n_ar_stock',
    'l10n_ar_stock_delivery',
    'l10n_ar_ux',
    'l10n_ar_website_sale',
    'web_responsive',
    'product_planned_price',
    'product_replenishment_cost',
    'product_internal_code',
    'product_prices_update',
    'account_mass_reconcile',
    'account_move_line_reconcile_manual',
    'account_move_reconcile_forbid_cancel',
    'account_reconcile_oca',
    'pos_default_partner',
    'pos_order_reorder',
    'pos_stock_available_online',
    'pos_order_to_sale_order',
    'pos_lot_selection',
    'pos_lot_barcode',
    'product_planned_price',
    'product_replenishment_cost',
    'product_internal_code',
    'product_prices_update',
    #'meli_oerp',
    #'auto_backup',
    # Agrega tantos módulos como necesites
]

for module in modules_to_install:
    # Verificar si el módulo ya está instalado
    installed_module_ids = models.execute_kw(db, uid, password, 'ir.module.module', 'search', [[('name', '=', module), ('state', '=', 'installed')]])
    if installed_module_ids:
        print(f"El módulo {module} ya está instalado.")
    else:
        # Busca el módulo en la base de datos
        module_id = models.execute_kw(db, uid, password, 'ir.module.module', 'search', [[('name', '=', module)]])
        
        if module_id:
            try:
                # Intenta instalar el módulo
                models.execute_kw(db, uid, password, 'ir.module.module', 'button_immediate_install', [module_id])
                print(f'Módulo {module} instalado correctamente.')
            except Exception as e:
                print(f'Error al instalar el módulo {module}: {e}')
        else:
            print(f'Módulo {module} no encontrado.')

print('Proceso de instalación de módulos completado.')
