#!/usr/bin/env python3
import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys
import os

# Configuración de directorio para importar config.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import ODOO_16, ODOO_18
except ImportError:
    print("❌ Error: No se encontró config.py")
    sys.exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_product_archive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OdooConnection:
    """Maneja la conexión a una instancia de Odoo"""
    def __init__(self, config: Dict, name: str):
        self.config = config
        self.name = name
        self.uid = None
        self.models = None
        self.connect()
    
    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
            self.uid = common.authenticate(
                self.config['db'], self.config['username'], self.config['password'], {}
            )
            if not self.uid:
                raise Exception(f"Autenticación fallida en {self.name}")
            self.models = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")
        except Exception as e:
            logger.error(f"❌ Error conectando a {self.name}: {e}")
            raise

    def search_read(self, model: str, domain: List, fields: List, context: Dict = None) -> List[Dict]:
        kwargs = {'fields': fields}
        if context: kwargs['context'] = context
        return self.models.execute_kw(
            self.config['db'], self.uid, self.config['password'],
            model, 'search_read', [domain], kwargs
        )

    def write(self, model: str, record_ids: List[int], values: Dict, context: Dict = None) -> bool:
        kwargs = {}
        if context: kwargs['context'] = context
        return self.models.execute_kw(
            self.config['db'], self.uid, self.config['password'],
            model, 'write', [record_ids, values], kwargs
        )

class ProductArchiveSync:
    """Sincroniza el estado activo/archivado basado en default_code"""
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        self.stats = {
            'matched': 0,
            'archived': 0,
            'activated': 0,
            'not_found_in_o16': 0,
            'errors': 0
        }

    def get_products_dict(self, connection: OdooConnection) -> Dict[str, dict]:
        """Obtiene productos y los indexa por referencia normalizada"""
        logger.info(f"--- Cargando productos de {connection.name} ---")
        try:
            # Traemos todos incluyendo archivados usando active_test: False
            products = connection.search_read(
                'product.product', 
                [], 
                ['id', 'name', 'default_code', 'active'],
                context={'active_test': False}
            )
            
            p_dict = {}
            for p in products:
                # Normalización: quitamos espacios y pasamos a mayúsculas
                ref = str(p.get('default_code') or '').strip().upper()
                if ref:
                    p_dict[ref] = {
                        'id': p['id'],
                        'name': p['name'],
                        'active': p['active']
                    }
            logger.info(f"✓ {len(p_dict)} productos con referencia encontrados.")
            return p_dict
        except Exception as e:
            logger.error(f"Error cargando productos: {e}")
            return {}

    def run(self):
        start_time = datetime.now()
        logger.info("Iniciando proceso de comparación...")

        o16_data = self.get_products_dict(self.source)
        o18_data = self.get_products_dict(self.target)

        if not o16_data or not o18_data:
            logger.error("No se pudo obtener datos de una de las instancias. Abortando.")
            return

        for ref, p18 in o18_data.items():
            # CASO: Existe en Odoo 18
            if ref in o16_data:
                p16 = o16_data[ref]
                self.stats['matched'] += 1

                # Comparar estados
                if p18['active'] != p16['active']:
                    try:
                        self.target.write('product.product', [p18['id']], {'active': p16['active']})
                        status_txt = "ACTIVANDO" if p16['active'] else "ARCHIVANDO"
                        logger.info(f"➔ {status_txt}: [{ref}] {p18['name']} (Igualando a O16)")
                        
                        if p16['active']: self.stats['activated'] += 1
                        else: self.stats['archived'] += 1
                    except Exception as e:
                        logger.error(f"❌ Error con {ref}: {e}")
                        self.stats['errors'] += 1
            else:
                # REQUERIMIENTO: Log de lo que está en O18 pero no en O16
                logger.warning(f"🔍 ANALISIS: Encontré esto en Odoo 18 [{ref}] y NO lo encuentro activo/existente en Odoo 16")
                self.stats['not_found_in_o16'] += 1

        # Resumen
        logger.info("="*60)
        logger.info(f"RESUMEN FINAL - Tiempo: {datetime.now() - start_time}")
        logger.info(f"• Coincidencias procesadas: {self.stats['matched']}")
        logger.info(f"• Archivados en O18:       {self.stats['archived']}")
        logger.info(f"• Activados en O18:        {self.stats['activated']}")
        logger.info(f"• No encontrados en O16:   {self.stats['not_found_in_o16']}")
        logger.info(f"• Errores técnicos:        {self.stats['errors']}")
        logger.info("="*60)

if __name__ == "__main__":
    try:
        sync = ProductArchiveSync()
        sync.run()
    except Exception as e:
        logger.error(f"Error fatal: {e}")