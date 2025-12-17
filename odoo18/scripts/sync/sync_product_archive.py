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
    handlers=[logging.FileHandler('sync_tecnico.log'), logging.StreamHandler()]
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

def get_product_maps(conn):
    """Crea dos mapas: uno por barcode y otro por referencia"""
    logger.info(f"Consultando productos en {conn.name}...")
    products = conn.execute(
        'product.product', 'search_read',
        [], 
        ['default_code', 'barcode', 'active', 'name'],
        context={'active_test': False}
    )
    
    by_barcode = {}
    by_ref = {}
    
    for p in products:
        barcode = str(p.get('barcode') or '').strip()
        ref = str(p.get('default_code') or '').strip()
        
        data = {'id': p['id'], 'active': p['active'], 'name': p['name']}
        
        if barcode:
            by_barcode[barcode] = data
        if ref:
            by_ref[ref] = data
            
    return by_barcode, by_ref

def run_sync():
    logger.info(f"--- Sincronización Técnica (Barcode/Ref): {datetime.now().strftime('%H:%M:%S')} ---")
    
    o16 = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
    o18 = OdooConnection(ODOO_18, "Odoo 18 (Local)")

    # 1. Obtener mapas de Odoo 16 (Fuente)
    o16_barcodes, o16_refs = get_product_maps(o16)
    
    # 2. Obtener productos de Odoo 18 (Destino)
    logger.info(f"Consultando productos en Odoo 18...")
    products_18 = o18.execute(
        'product.product', 'search_read',
        [], 
        ['default_code', 'barcode', 'active', 'name'],
        context={'active_test': False}
    )

    stats = {'archivados': 0, 'no_encontrados': 0, 'omitidos': 0}

    # 3. Procesar Odoo 18
    for p18 in products_18:
        barcode = str(p18.get('barcode') or '').strip()
        ref = str(p18.get('default_code') or '').strip()
        p18_id = p18['id']
        p18_name = p18['name']
        
        target_o16 = None
        
        # Intentar encontrar por Barcode primero
        if barcode and barcode in o16_barcodes:
            target_o16 = o16_barcodes[barcode]
        # Si no, intentar por Referencia Interna
        elif ref and ref in o16_refs:
            target_o16 = o16_refs[ref]
            
        if target_o16:
            # Si en O16 está archivado (False) y en O18 está activo (True) -> Archivar
            if not target_o16['active'] and p18['active']:
                logger.info(f"📦 ARCHIVANDO: [{ref or 'S/R'}] {p18_name}")
                o18.execute('product.product', 'write', [p18_id], {'active': False})
                stats['archivados'] += 1
        else:
            if not barcode and not ref:
                stats['omitidos'] += 1
            else:
                # Log de análisis solicitado
                logger.warning(f"⚠️  ANÁLISIS: Encontré en O18 [{ref or barcode}] {p18_name} y no existe activo en O16")
                stats['no_encontrados'] += 1

    logger.info("-" * 60)
    logger.info(f"RESULTADOS FINAL:")
    logger.info(f"- Archivados en O18: {stats['archivados']}")
    logger.info(f"- No encontrados en O16: {stats['no_encontrados']}")
    logger.info(f"- Sin códigos (Omitidos): {stats['omitidos']}")
    logger.info("-" * 60)

if __name__ == "__main__":
    run_sync()