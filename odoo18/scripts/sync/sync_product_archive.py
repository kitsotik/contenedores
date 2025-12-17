#!/usr/bin/env python3
import xmlrpc.client
import logging
import sys
import os
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
    handlers=[logging.FileHandler('sync_por_nombre.log'), logging.StreamHandler()]
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

def get_product_map_by_name(conn):
    """Obtiene productos mapeados por NOMBRE normalizado"""
    logger.info(f"Consultando productos en {conn.name}...")
    products = conn.execute(
        'product.product', 'search_read',
        [], 
        ['name', 'active'],
        context={'active_test': False}
    )
    
    product_map = {}
    for p in products:
        # Normalizamos el nombre: minúsculas y sin espacios a los lados
        name_key = str(p.get('name') or '').strip().lower()
        if name_key:
            # Si hay nombres duplicados, se quedará con el último encontrado
            product_map[name_key] = {
                'id': p['id'],
                'active': p['active'],
                'full_name': p['name'] # Guardamos el nombre original para el log
            }
    return product_map

def run_sync():
    logger.info(f"--- Sincronización por Nombre: {datetime.now().strftime('%H:%M:%S')} ---")
    
    o16 = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
    o18 = OdooConnection(ODOO_18, "Odoo 18 (Local)")

    # 1. Cargar mapas por nombre
    mapa_16 = get_product_map_by_name(o16)
    mapa_18 = get_product_map_by_name(o18)

    logger.info(f"\nAnalizando {len(mapa_18)} productos encontrados en Odoo 18...")
    logger.info("-" * 60)

    stats = {'archivados': 0, 'no_encontrados_en_16': 0, 'ya_estaban_bien': 0, 'errores': 0}

    # 2. Comparar
    for name_key, prod_18 in mapa_18.items():
        
        if name_key in mapa_16:
            prod_16 = mapa_16[name_key]
            
            # Si en O16 está archivado y en O18 está activo -> Archivar en O18
            if not prod_16['active'] and prod_18['active']:
                try:
                    logger.info(f"📦 ARCHIVANDO: '{prod_18['full_name']}' (Archivado en O16)")
                    o18.execute('product.product', 'write', [prod_18['id']], {'active': False})
                    stats['archivados'] += 1
                except Exception as e:
                    logger.error(f"❌ Error al archivar '{prod_18['full_name']}': {e}")
                    stats['errores'] += 1
            else:
                stats['ya_estaban_bien'] += 1
        else:
            # El log que pediste
            logger.warning(f"⚠️  ANÁLISIS: Encontré '{prod_18['full_name']}' en Odoo 18 y no existe con ese nombre en Odoo 16")
            stats['no_encontrados_en_16'] += 1

    # 3. Resumen
    logger.info("-" * 60)
    logger.info(f"RESULTADOS:")
    logger.info(f"- Productos archivados en O18: {stats['archivados']}")
    logger.info(f"- No encontrados en O16:       {stats['no_encontrados_en_16']}")
    logger.info(f"- Sin cambios necesarios:      {stats['ya_estaban_bien']}")
    logger.info("-" * 60)

if __name__ == "__main__":
    run_sync()