#!/usr/bin/env python3
import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import sys
import os

# ... (Mantenemos la lógica de importación de config y OdooConnection igual) ...

class ProductArchiveSync:
    def __init__(self):
        # Asegúrate que ODOO_16 y ODOO_18 estén definidos en tu config.py
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        self.stats = {
            'matched': 0,
            'archived_in_o18': 0,
            'activated_in_o18': 0,
            'not_in_o16': 0,
            'errors': 0
        }

    def get_products_dict(self, connection: OdooConnection) -> Dict[str, dict]:
        """
        Obtiene productos indexados por referencia normalizada.
        """
        logger.info(f"Consultando productos en {connection.name}...")
        # Buscamos en product.product para manejar variantes
        products = connection.search_read(
            'product.product',
            [], 
            ['id', 'name', 'default_code', 'active'],
            context={'active_test': False}
        )
        
        result = {}
        for p in products:
            # Normalizamos la referencia: quitar espacios y pasar a mayúsculas
            ref = str(p.get('default_code') or '').strip().upper()
            if ref:
                result[ref] = {
                    'id': p['id'],
                    'name': p['name'],
                    'active': p['active']
                }
        return result

    def run(self):
        start_time = datetime.now()
        logger.info("Iniciando comparación cruzada Odoo 16 <-> Odoo 18")

        # 1. Cargar datos de ambos
        dict_o16 = self.get_products_dict(self.source)
        dict_o18 = self.get_products_dict(self.target)

        logger.info(f"Odoo 16: {len(dict_o16)} productos con referencia.")
        logger.info(f"Odoo 18: {len(dict_o18)} productos con referencia.")

        # 2. Sincronizar Odoo 18 basado en Odoo 16
        for ref, data_o18 in dict_o18.items():
            o18_id = data_o18['id']
            o18_active = data_o18['active']
            o18_name = data_o18['name']

            if ref in dict_o16:
                o16_active = dict_o16[ref]['active']
                self.stats['matched'] += 1

                # CASO: Encontrado en ambos, pero diferente estado
                if o18_active != o16_active:
                    try:
                        self.target.write('product.product', [o18_id], {'active': o16_active})
                        accion = "ARCHIVANDO" if not o16_active else "ACTIVANDO"
                        logger.info(f"➔ {accion}: [{ref}] {o18_name} (O16 estaba {'Activo' if o16_active else 'Archivado'})")
                        
                        if o16_active: self.stats['activated_in_o18'] += 1
                        else: self.stats['archived_in_o18'] += 1
                    except Exception as e:
                        logger.error(f"❌ Error actualizando {ref}: {e}")
                        self.stats['errors'] += 1
            else:
                # REQUERIMIENTO ESPECIAL: "Encontré esto en Odoo 18 y no lo encuentro activo en Odoo 16"
                # Esto significa que el producto es nuevo en O18 o no tiene la misma referencia en O16
                logger.warning(f"🔍 ANALISIS: Encontré [{ref}] {o18_name} en Odoo 18, pero NO existe (o no tiene referencia) en Odoo 16")
                self.stats['not_in_o16'] += 1

        # 3. Resumen Final
        logger.info("="*50)
        logger.info(f"FINALIZADO EN: {datetime.now() - start_time}")
        logger.info(f"Productos procesados en O18: {len(dict_o18)}")
        logger.info(f"Coincidencias encontradas: {self.stats['matched']}")
        logger.info(f"Archivados en O18: {self.stats['archived_in_o18']}")
        logger.info(f"Activados en O18: {self.stats['activated_in_o18']}")
        logger.info(f"Productos en O18 que no existen en O16: {self.stats['not_in_o16']}")
        logger.info("="*50)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    sync = ProductArchiveSync()
    sync.run()