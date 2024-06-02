import xmlrpc.client

# Configuración de conexión
url = 'http://149.50.138.116:8069'  # URL del servidor Odoo
db = 'o16db'
username = 'admin'
password = 'bgt56yhn*971'

# Conexión a la API común
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

# Conexión al objeto de la API
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Listar todas las monedas y sus campos
currencies = models.execute_kw(db, uid, password,
    'res.currency', 'search_read',
    [[], ['id', 'name', 'symbol', 'active']])

# Imprimir las monedas
for currency in currencies:
    print(currency)

# Buscar el ID de la moneda por su nombre
currency_name = 'USD'
currency_ids = models.execute_kw(db, uid, password,
    'res.currency', 'search',
    [[['name', '=', currency_name], ['active', 'in', [True, False]]]])

# Si se encuentra la moneda, activar
if currency_ids:
    currency_id = currency_ids[0]
    models.execute_kw(db, uid, password,
        'res.currency', 'write',
        [[currency_id], {'active': True}])
    print(f"La moneda {currency_name} ha sido activada.")
else:
    print(f"No se encontró la moneda con el nombre {currency_name}.")



