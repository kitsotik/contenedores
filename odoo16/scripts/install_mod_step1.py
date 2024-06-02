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
    'account',
    'sale_management',
    'crm',
    'stock',
    'purchase',
    'point_of_sale',
    'contacts',
    'website',
    'website_sale',
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
