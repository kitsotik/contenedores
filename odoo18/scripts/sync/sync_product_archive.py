#!/usr/bin/env python3
import xmlrpc.client
import logging
import sys
import os
import re
from datetime import datetime

# Configuración de entorno
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import ODOO_16, ODOO_18
except ImportError:
    print("❌ Error: No se encontró config.py")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.FileHandler('sync_limpieza_nombres.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class OdooConnection:
    def __init__(self, config, name):
        self.config = config
        self.name = name
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

def limpiar_nombre(nombre):
    """
    Limpia el nombre profundamente para comparación:
    - Todo a minúsculas
    - Quita comillas (", '), guiones, barras
    - Convierte múltiples espacios en uno solo
    """
    if not nombre: return ""
    # 1. Minúsculas
    n = nombre.lower()
    # 2. Quitar caracteres que suelen variar (comillas, símbolos)
    n = re.sub(r'[\"\'\-\/\(\)]', ' ', n)
    # 3. Quitar espacios múltiples y espacios en los extremos
    n = " ".join(n.split())
    return n

def get_product_map(conn):
    logger.info(f"Consultando productos en {conn.name}...")
    products = conn.execute(
        'product.product', 'search_read',
        [], 
        ['name', 'active', 'default_code'],
        context={'active_test': False}
    )
    
    product_map = {}
    for p in products:
        # LLAVE DE COMPARACIÓN LIMPIA
        key = limpiar_nombre(p.get('name'))
        if key:
            # Guardamos la info. Si el nombre limpio se repite, avisamos en debug
            product_map[key] = {
                'id': p['id'],
                'active': p['active'],
                'full_name': p['name'],
                'ref': p.get('default_code') or 'Sin Ref'
            }
    return product_map

def run_sync():
    logger.info(f"--- Sincronización Reforzada: {datetime.now().strftime('%H:%M:%S')} ---")
    
    o16 = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
    o18 = OdooConnection(ODOO_18, "Odoo 18 (Local)")

    mapa_16 = get_product_map(o16)
    mapa_18 = get_product_map(o18)

    logger.info(f"\nComparando {len(mapa_18)} productos de Odoo 18...")
    logger.info("-" * 60)

    stats = {'archivados': 0, 'no_encontrados': 0, 'correctos': 0}

    for key_18, data_18 in mapa_18.items():
        # Verificamos si el nombre limpio existe en O16
        if key_18 in mapa_16:
            data_16 = mapa_16[key_18]
            
            # Si en O16 está archivado (False) y en O18 está activo (True)
            if not data_16['active'] and data_18['active']:
                try:
                    logger.info(f"📦 ARCHIVANDO: '{data_18['full_name']}'")
                    logger.info(f"   (Motivo: Coincidencia limpia con O16 archivado)")
                    o18.execute('product.product', 'write', [data_18['id']], {'active': False})
                    stats['archivados'] += 1
                except Exception as e:
                    logger.error(f"❌ Error al archivar {data_18['full_name']}: {e}")
            else:
                stats['correctos'] += 1
        else:
            # Aquí verás si el SSD de 480Gb sigue saliendo como no encontrado
            logger.warning(f"⚠️  NO ENCONTRADO EN O16: '{data_18['full_name']}'")
            stats['no_encontrados'] += 1

    logger.info("-" * 60)
    logger.info(f"RESUMEN: Archivados: {stats['archivados']} | No encontrados: {stats['no_encontrados']} | Sin cambios: {stats['correctos']}")

if __name__ == "__main__":
    run_sync()