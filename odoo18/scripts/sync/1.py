import xmlrpc.client
from config import ODOO_16

uid = None
models = None

# Conexión
common = xmlrpc.client.ServerProxy(f"{ODOO_16['url']}/xmlrpc/2/common")
uid = common.authenticate(ODOO_16['db'], ODOO_16['username'], ODOO_16['password'], {})
models = xmlrpc.client.ServerProxy(f"{ODOO_16['url']}/xmlrpc/2/object")

# Leer UN producto para identificar el tipo de campo
prod = models.execute_kw(
    ODOO_16['db'], uid, ODOO_16['password'],
    'product.product', 'search_read',
    [[]],
    {'fields': ['name', 'replenishment_base_cost_on_currency'], 'limit': 1}
)

print(prod)
