import xmlrpc.client
from config import ODOO_16, ODOO_18

# ==========================================================
# CONEXIÓN
# ==========================================================
def odoo_connect(conf):
    common = xmlrpc.client.ServerProxy(f"{conf['url']}/xmlrpc/2/common")
    uid = common.authenticate(conf['db'], conf['username'], conf['password'], {})
    models = xmlrpc.client.ServerProxy(f"{conf['url']}/xmlrpc/2/object")
    return uid, models


# ==========================================================
# SELECCIONA CORRECTAMENTE LA MONEDA
# ==========================================================
def detect_currency(models, conf, uid, seller_ids):
    if not seller_ids:
        return "SIN MONEDA"

    sellers = models.execute_kw(
        conf['db'], uid, conf['password'],
        'product.supplierinfo', 'read',
        [seller_ids],
        {'fields': ['currency_id', 'price', 'sequence']}
    )

    # 1️⃣ Intentar encontrar proveedor con USD
    for s in sellers:
        if s['currency_id'] and s['currency_id'][1] == 'USD':
            return "USD"

    # 2️⃣ Si no hay USD, tomar el que tenga sequence más bajo
    sellers_sorted = sorted(sellers, key=lambda x: x.get('sequence', 999))
    if sellers_sorted[0]['currency_id']:
        return sellers_sorted[0]['currency_id'][1]

    return "SIN MONEDA"


# ==========================================================
# LECTURA DE PRODUCTOS
# ==========================================================
def read_products(conf, uid, models):
    ids = models.execute_kw(
        conf['db'], uid, conf['password'],
        'product.product', 'search',
        [[]],
        {'limit': 10}
    )

    records = models.execute_kw(
        conf['db'], uid, conf['password'],
        'product.product', 'read',
        [ids],
        {'fields': ['name', 'seller_ids']}
    )

    results = []
    for rec in records:
        currency = detect_currency(models, conf, uid, rec['seller_ids'])
        results.append({
            'name': rec['name'],
            'currency': currency
        })
    return results


# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":
    uid16, m16 = odoo_connect(ODOO_16)
    uid18, m18 = odoo_connect(ODOO_18)

    origen = read_products(ODOO_16, uid16, m16)

    destino = []
    for prod in origen:
        rec = m18.execute_kw(
            ODOO_18['db'], uid18, ODOO_18['password'],
            'product.product', 'search_read',
            [[['name', '=', prod['name']]]],
            {'fields': ['seller_ids']}
        )
        if rec:
            currency = detect_currency(m18, ODOO_18, uid18, rec[0]['seller_ids'])
        else:
            currency = "NO EXISTE EN DESTINO"

        destino.append({'name': prod['name'], 'currency': currency})

    print("\n================= RESULTADOS =================\n")
    for o, d in zip(origen, destino):
        flag = "✔ OK" if o['currency'] == d['currency'] else "❌ DIFERENTE"
        print(f"{flag} | {o['name']}")
        print(f"   Origen : {o['currency']}")
        print(f"   Destino: {d['currency']}\n")
