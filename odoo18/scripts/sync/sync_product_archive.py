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

# Logging configurado
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
        self.uid = None
        self.models = None
        self.connect()

    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
            self.uid = common.authenticate(self.config['db'], self.config['username'], self.config['password'], {})
            self.models = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")
        except Exception as e:
            logger.error(f"Error de conexión en {self.name}: {e}")
            sys.exit(1)

    def execute(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.config['db'], self.uid, self.config['password'], model, method, args, kwargs)

def get_product_map(conn):
    """Obtiene todos los productos (activos y archivados) mapeados por referencia"""
    logger.info(f"Consultando productos en {conn.name}...")
    # USAMOS active_test: False para ver los archivados de Odoo
    products = conn.execute(
        'product.product', 'search_read',
        [], # Buscamos todos los registros
        ['default_code', 'active', 'name'],
        context={'active_test': False}
    )
    
    product_map = {}
    for p in products:
        ref = str(p.get('default_code') or '').strip()
        if ref:
            product_map[ref] = p
    return product_map

def run_sync():
    logger.info(f"--- Inicio de Sincronización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    o16 = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
    o18 = OdooConnection(ODOO_18, "Odoo 18 (Local)")

    # 1. Traer mapas de productos
    mapa_16 = get_product_map(o16)
    mapa_18 = get_product_map(o18)

    logger.info(f"\nAnalizando {len(mapa_18)} productos con referencia en Odoo 18...")
    logger.info("-" * 60)

    stats = {
        'archivados': 0, 
        'no_encontrados_en_16': 0, 
        'ya_estaban_bien': 0,
        'errores': 0
    }

    # 2. Comparar Odoo 18 contra Odoo 16
    for ref, prod_18 in mapa_18.items():
        
        if ref in mapa_16:
            prod_16 = mapa_16[ref]
            
            # REGLA DE ORO: Si en 16 está archivado (False) y en 18 está activo (True) -> ARCHIVAR 18
            if not prod_16['active'] and prod_18['active']:
                try:
                    logger.info(f"📦 ARCHIVANDO: [{ref}] {prod_18['name']} (Está archivado en O16)")
                    o18.execute('product.product', 'write', [prod_18['id']], {'active': False})
                    stats['archivados'] += 1
                except Exception as e:
                    logger.error(f"❌ Error al archivar {ref}: {e}")
                    stats['errores'] += 1
            else:
                stats['ya_estaban_bien'] += 1
        else:
            # Producto en 18 que no existe en 16
            logger.warning(f"⚠️  ANÁLISIS: Encontré esto en odoo 18 [{ref}] y no lo encuentro activo en odoo 16")
            stats['no_encontrados_en_16'] += 1

    # 3. Resumen final (Corregido para evitar KeyError)
    logger.info("-" * 60)
    logger.info(f"Finalizado.")
    logger.info(f"- Productos archivados en O18: {stats['archivados']}")
    logger.info(f"- Productos en O18 que no existen en O16: {stats['no_encontrados_en_16']}")
    logger.info(f"- Productos que ya estaban correctos: {stats['ya_estaban_bien']}")
    if stats['errores'] > 0:
        logger.error(f"- Errores encontrados: {stats['errores']}")
    logger.info("-" * 60)

if __name__ == "__main__":
    run_sync()