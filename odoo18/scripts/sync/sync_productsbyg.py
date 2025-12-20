#!/usr/bin/env python3
"""
Script de sincronización de PRODUCTOS
Odoo 16 (VPS) -> Odoo 18 (Local)

OPTIMIZADO SIN REESCRIBIR:
- Lectura por bloques (chunks)
- Imagen en la misma lectura
- Cache external_id
- Cache categoría "All"
- FIX search / search_read (XML-RPC correcto)
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ODOO_16, ODOO_18, SYNC_OPTIONS

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_products.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# ODOO CONNECTION
# ---------------------------------------------------------
class OdooConnection:
    def __init__(self, config: Dict, name: str):
        self.config = config
        self.name = name
        self.uid = None
        self.models = None
        self.connect()

    def connect(self):
        common = xmlrpc.client.ServerProxy(
            f"{self.config['url']}/xmlrpc/2/common"
        )
        self.uid = common.authenticate(
            self.config['db'],
            self.config['username'],
            self.config['password'],
            {}
        )
        if not self.uid:
            raise Exception(f"Error autenticando en {self.name}")

        self.models = xmlrpc.client.ServerProxy(
            f"{self.config['url']}/xmlrpc/2/object"
        )

        version = common.version()
        logger.info(f"✓ {self.name} conectado (v{version['server_version']})")

    # --- FIXED ---
    def search(self, model, domain, limit=None):
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        return self.models.execute_kw(
            self.config['db'],
            self.uid,
            self.config['password'],
            model,
            'search',
            [domain],
            kwargs
        )

    # --- FIXED ---
    def search_read(self, model, domain, fields):
        return self.models.execute_kw(
            self.config['db'],
            self.uid,
            self.config['password'],
            model,
            'search_read',
            [domain],
            {'fields': fields}
        )

    def create(self, model, values):
        return self.models.execute_kw(
            self.config['db'],
            self.uid,
            self.config['password'],
            model,
            'create',
            [values]
        )

    def write(self, model, ids, values):
        return self.models.execute_kw(
            self.config['db'],
            self.uid,
            self.config['password'],
            model,
            'write',
            [ids, values]
        )

# ---------------------------------------------------------
# PRODUCT SYNC
# ---------------------------------------------------------
class ProductSync:
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16")
        self.target = OdooConnection(ODOO_18, "Odoo 18")

        self.stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'images_synced': 0
        }

        # -------------------------------------------------
        # CACHE CATEGORÍA "ALL"
        # -------------------------------------------------
        self.default_category_id = None
        cat = self.target.search(
            'product.category',
            [('name', '=', 'All')],
            limit=1
        )
        if cat:
            self.default_category_id = cat[0]

        # -------------------------------------------------
        # CACHE EXTERNAL IDS
        # -------------------------------------------------
        self.external_id_map = {}
        records = self.target.search_read(
            'ir.model.data',
            [
                ('model', '=', 'product.product'),
                ('module', '=', 'sync_script'),
                ('name', 'like', 'sync_product_product_%')
            ],
            ['name', 'res_id']
        )
        for r in records:
            self.external_id_map[r['name']] = r['res_id']

        logger.info(
            f"Cache cargado: {len(self.external_id_map)} productos existentes"
        )

    # -----------------------------------------------------
    def get_external_id(self, source_id: int) -> str:
        return f"sync_product_product_{source_id}"

    # -----------------------------------------------------
    def get_products_from_source(self) -> List[Dict]:
        logger.info("📊 Buscando productos en Odoo 16...")

        domain = []
        if SYNC_OPTIONS.get('only_active', True):
            domain.append(('active', '=', True))

        product_ids = self.source.search('product.product', domain)
        total = len(product_ids)

        logger.info(f"✓ {total} productos encontrados")

        if not product_ids:
            return []

        fields = [
            'id', 'name', 'default_code', 'barcode', 'type', 'categ_id',
            'list_price', 'standard_price', 'uom_id', 'uom_po_id',
            'description', 'description_sale', 'description_purchase',
            'weight', 'volume', 'sale_ok', 'purchase_ok', 'active',
            'pos_categ_id', 'public_categ_ids', 'taxes_id',
            'supplier_taxes_id', 'available_in_pos',
            'image_1920'
        ]

        CHUNK = 100
        products = []

        for offset in range(0, total, CHUNK):
            chunk_ids = product_ids[offset: offset + CHUNK]

            logger.info(
                f"⏳ Descargando productos "
                f"{offset + 1}–{min(offset + CHUNK, total)} / {total}"
            )

            chunk = self.source.search_read(
                'product.product',
                [('id', 'in', chunk_ids)],
                fields
            )

            products.extend(chunk)

        return products

    # -----------------------------------------------------
    def prepare_values(self, product: Dict) -> Dict:
        vals = {
            'name': product['name'],
            'type': 'consu',
            'active': product.get('active', True),
            'sale_ok': product.get('sale_ok', True),
            'purchase_ok': product.get('purchase_ok', True),
        }

        simple_fields = [
            'default_code', 'barcode',
            'list_price', 'standard_price',
            'description', 'description_sale',
            'description_purchase',
            'weight', 'volume'
        ]

        for f in simple_fields:
            if product.get(f) not in (None, False, ''):
                vals[f] = product[f]

        if product.get('image_1920'):
            vals['image_1920'] = product['image_1920']
            self.stats['images_synced'] += 1

        if product.get('categ_id') and self.default_category_id:
            vals['categ_id'] = self.default_category_id

        return vals

    # -----------------------------------------------------
    def sync_product(self, product: Dict):
        external_id = self.get_external_id(product['id'])

        try:
            vals = self.prepare_values(product)
            existing_id = self.external_id_map.get(external_id)

            if existing_id:
                self.target.write(
                    'product.product',
                    [existing_id],
                    vals
                )
                self.stats['updated'] += 1
            else:
                new_id = self.target.create(
                    'product.product',
                    vals
                )
                self.target.create(
                    'ir.model.data',
                    {
                        'name': external_id,
                        'model': 'product.product',
                        'module': 'sync_script',
                        'res_id': new_id
                    }
                )
                self.external_id_map[external_id] = new_id
                self.stats['created'] += 1

        except Exception as e:
            logger.error(f"❌ {product['name']}: {e}")
            self.stats['errors'] += 1

    # -----------------------------------------------------
    def run(self):
        start = datetime.now()

        products = self.get_products_from_source()
        self.stats['total'] = len(products)

        logger.info("🚀 Sincronizando productos...")

        for i, product in enumerate(products, 1):
            if i % 25 == 0 or i == 1:
                logger.info(
                    f"[{i}/{len(products)}] "
                    f"{product.get('default_code', 'Sin ref')} - {product['name']}"
                )
            self.sync_product(product)

        elapsed = datetime.now() - start

        logger.info("=" * 60)
        logger.info("RESUMEN")
        logger.info(f"Total: {self.stats['total']}")
        logger.info(f"Creados: {self.stats['created']}")
        logger.info(f"Actualizados: {self.stats['updated']}")
        logger.info(f"Imágenes: {self.stats['images_synced']}")
        logger.info(f"Errores: {self.stats['errors']}")
        logger.info(f"Tiempo: {elapsed}")
        logger.info("=" * 60)

# ---------------------------------------------------------
if __name__ == "__main__":
    ProductSync().run()
