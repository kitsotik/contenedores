#!/usr/bin/env python3
import xmlrpc.client
import logging
import sys
import os
from datetime import datetime

# Mantener lógica de importación de config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import ODOO_16, ODOO_18
except ImportError:
    print("❌ Error: No se encontró config.py")
    sys.exit(1)

# Logging configurado para lo que pediste
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.FileHandler('archivo_productos.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class OdooConnection:
    def __init__(self, config, name):
        self.config = config
        self.name = name
        self.connect()

    def connect(self):
        common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
        self.uid = common.authenticate(self.config['db'], self.config['username'], self.config['password'], {})
        self.models = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")

    def execute(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.config['db'], self.uid, self.config['password'], model, method, args, kwargs)

def get_product_map(conn):
    """Obtiene todos los productos (activos y archivados) mapeados por referencia"""
    logger.info(f"Consultando productos en {conn.name}...")
    # ESENCIAL: active_test=False para poder ver los archivados
    products = conn.execute(
        'product.product', 'search_read',
        [], # Todos los productos
        ['default_code', 'active', 'name'],
        context={'active_test': False}
    )
    
    # Creamos un diccionario { 'REF123': {'id': 1, 'active': True, 'name': 'Producto'} }
    product_map = {}
    for p in products:
        ref = str(p.get('default_code') or '').strip()
        if ref:
            product_map[ref] = p
    return product_map

def run_sync():
    o16 = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
    o18 = OdooConnection(ODOO_18, "Odoo 18 (Local)")

    # 1. Traer datos de ambos mundos
    mapa_16 = get_product_map(o16)
    mapa_18 = get_product_map(o18)

    logger.info(f"\nAnalizando {len(mapa_18)} productos de Odoo 18...")
    logger.info("-" * 50)

    stats = {'archivados': 0, 'no_encontrados': 0, 'ya_estaban_bien': 0}

    # 2. Iterar sobre lo que hay en Odoo 18
    for ref, prod_18 in mapa_18.items():
        
        # Si el producto existe en Odoo 16
        if ref in mapa_16:
            prod_16 = mapa_16[ref]
            
            # CASO: En O16 está ARCHIVADO (active=False) pero en O18 está ACTIVO (active=True)
            if not prod_16['active'] and prod_18['active']:
                logger.info(f"📦 ARCHIVANDO: [{ref}] {prod_18['name']} (Detectado archivado en O16)")
                o18.execute('product.product', 'write', [prod_18['id']], {'active': False})
                stats['archivados'] += 1
            else:
                stats['ya_estaban_bien'] += 1
        
        else:
            # REQUERIMIENTO: Log de lo que hay en 18 pero no está activo en 16
            logger.warning(f"⚠️  ANÁLISIS: Encontré esto en odoo 18 [{ref}] y no lo encuentro activo en odoo 16")
            stats['no_encontrados'] += 1

    # 3. Resumen
    logger.info("-" * 50)
    logger.info(f"Finalizado. Se archivaron {stats['archivados']} productos en Odoo 18.")
    logger.info(f"Productos en O18 sin referencia activa en O16: {stats['not_found']}")

if __name__ == "__main__":
    run_sync()