#!/usr/bin/env python3
"""
Script de sincronización de PRODUCTOS optimizado
Odoo 16 (VPS) -> Odoo 18 (Local)

Sincroniza:
- Datos del producto (incluyendo internal_code)
- Imágenes (image_1920)
- Categorías y Mapas de Impuestos
- Unidades de Medida (UoM) precargadas
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Set
import sys
import os

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar configuración
try:
    from config import ODOO_16, ODOO_18, SYNC_OPTIONS
except ImportError as e:
    print("❌ Error: No se encontró el archivo config.py")
    sys.exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_products.log'),
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
            logger.info(f"Conectando a {self.name}...")
            common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
            self.uid = common.authenticate(
                self.config['db'], self.config['username'], self.config['password'], {}
            )
            if not self.uid:
                raise Exception(f"Autenticación fallida en {self.name}")
            self.models = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")
            version = common.version()
            logger.info(f"✓ {self.name} listo (v: {version['server_version']})")
        except Exception as e:
            logger.error(f"❌ Error conectando a {self.name}: {e}")
            raise

    def execute(self, model: str, method: str, *args, **kwargs):
        return self.models.execute_kw(
            self.config['db'], self.uid, self.config['password'],
            model, method, args, kwargs
        )
    
    def search_read(self, model: str, domain: List, fields: List) -> List[Dict]:
        return self.execute(model, 'search_read', domain, {'fields': fields})
    
    def search(self, model: str, domain: List, limit: int = None) -> List[int]:
        kwargs = {'limit': limit} if limit else {}
        return self.execute(model, 'search', domain, kwargs)

    def create(self, model: str, values: Dict) -> int:
        return self.execute(model, 'create', values)

    def write(self, model: str, record_ids: List[int], values: Dict) -> bool:
        return self.execute(model, 'write', record_ids, values)


class ProductSync:
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16")
        self.target = OdooConnection(ODOO_18, "Odoo 18")
        
        self.category_map = {}
        self.pos_category_map = {}
        self.public_category_map = {}
        self.tax_map = {}
        self.valid_uom_ids = set() # Optimización: Cache de UoMs
        
        self.stats = {
            'total': 0, 'created': 0, 'updated': 0, 'errors': 0, 'images_synced': 0
        }
        
        # MAPEO DE IMPUESTOS
        self.tax_name_mapping = {
            'IVA 21%': 'VAT 21%',
            'IVA 10.5%': 'VAT 10.5%',
            'IVA 10,5%': 'VAT 10.5%',
        }
        
        self.load_initial_data()

    def load_initial_data(self):
        """Carga datos maestros para optimizar el proceso"""
        self.load_category_mappings()
        self.load_tax_mappings()
        # Precargar UoMs de Odoo 18 para evitar búsquedas repetitivas
        uoms = self.target.search('uom.uom', [])
        self.valid_uom_ids = set(uoms)
        logger.info(f"✓ {len(self.valid_uom_ids)} Unidades de Medida precargadas")

    def convert_product_type(self, odoo16_type: str) -> tuple:
        """Mapeo de tipos Odoo 16 -> 18"""
        mapping = {
            'product': ('consu', True),
            'consu': ('consu', False),
            'service': ('service', False)
        }
        return mapping.get(odoo16_type, ('consu', False))

    def load_tax_mappings(self):
        logger.info("Mapeando impuestos...")
        for sp, en in self.tax_name_mapping.items():
            source_taxes = self.source.search_read('account.tax', [('name', '=', sp)], ['id', 'type_tax_use'])
            for st in source_taxes:
                target_tax = self.target.search('account.tax', [('name', '=', en), ('type_tax_use', '=', st['type_tax_use'])], limit=1)
                if target_tax:
                    self.tax_map[st['id']] = target_tax[0]
        logger.info(f"✓ {len(self.tax_map)} impuestos vinculados")

    def load_category_mappings(self):
        """Carga mapeos desde external IDs (ir.model.data)"""
        models = {
            'product.category': (self.category_map, 'sync_product_category_'),
            'pos.category': (self.pos_category_map, 'sync_pos_category_'),
            'product.public.category': (self.public_category_map, 'sync_product_public_category_')
        }
        for model, (mapping_dict, prefix) in models.items():
            try:
                records = self.target.search_read('ir.model.data', [('model', '=', model), ('module', '=', 'sync_script')], ['name', 'res_id'])
                for r in records:
                    try:
                        source_id = int(r['name'].replace(prefix, ''))
                        mapping_dict[source_id] = r['res_id']
                    except ValueError: continue
            except: logger.warning(f"⚠ No se pudieron cargar mapeos para {model}")

    def get_products_from_source(self) -> List[Dict]:
        domain = [('active', '=', True)] if SYNC_OPTIONS.get('only_active', True) else []
        
        # Sincronización incremental
        if SYNC_OPTIONS.get('incremental_sync', False):
            if os.path.exists('last_product_sync.txt'):
                with open('last_product_sync.txt', 'r') as f:
                    domain.append(('write_date', '>', f.read().strip()))

        product_ids = self.source.search('product.product', domain, limit=SYNC_OPTIONS.get('product_limit', 0))
        
        # Campos a leer (Agregado: internal_code)
        fields = [
            'id', 'name', 'default_code', 'internal_code', 'barcode', 'type', 'categ_id',
            'list_price', 'standard_price', 'uom_id', 'uom_po_id',
            'description_sale', 'weight', 'volume', 'sale_ok', 'purchase_ok',
            'pos_categ_id', 'public_categ_ids', 'taxes_id', 'supplier_taxes_id',
            'available_in_pos'
        ]
        
        products = []
        for i, pid in enumerate(product_ids, 1):
            if i % 100 == 0: logger.info(f"⏳ Descargando metadatos: {i}/{len(product_ids)}")
            data = self.source.search_read('product.product', [('id', '=', pid)], fields)
            if data: products.append(data[0])

        # Descarga de imágenes por separado (Optimización de memoria)
        if SYNC_OPTIONS.get('sync_images', True):
            logger.info("🖼️ Descargando imágenes...")
            for i, p in enumerate(products, 1):
                if i % 100 == 0: logger.info(f"⏳ Procesando imagen {i}/{len(products)}")
                img_data = self.source.search_read('product.product', [('id', '=', p['id'])], ['image_1920'])
                if img_data and img_data[0].get('image_1920'):
                    p['image_1920'] = img_data[0]['image_1920']
        
        return products

    def prepare_values(self, product: Dict) -> Dict:
        p_type, is_storable = self.convert_product_type(product.get('type', 'consu'))
        
        vals = {
            'name': product['name'],
            'type': p_type,
            'active': product.get('active', True),
            'sale_ok': product.get('sale_ok', True),
            'purchase_ok': product.get('purchase_ok', True),
            'available_in_pos': product.get('available_in_pos', False),
            'default_code': product.get('default_code'),
            'internal_code': product.get('internal_code'), # <--- NUEVO CAMPO
            'barcode': product.get('barcode'),
            'list_price': product.get('list_price', 0.0),
            'standard_price': product.get('standard_price', 0.0),
            'description_sale': product.get('description_sale'),
            'weight': product.get('weight', 0.0),
            'volume': product.get('volume', 0.0),
        }

        if p_type == 'consu': vals['is_storable'] = is_storable
        if product.get('image_1920'): vals['image_1920'] = product['image_1920']

        # Categoría
        if product.get('categ_id'):
            vals['categ_id'] = self.category_map.get(product['categ_id'][0])

        # Impuestos
        for field in ['taxes_id', 'supplier_taxes_id']:
            if product.get(field):
                mapped_taxes = [self.tax_map[tid] for tid in product[field] if tid in self.tax_map]
                if mapped_taxes: vals[field] = [(6, 0, mapped_taxes)]

        # POS Categories (v16 many2one -> v18 many2many)
        if product.get('pos_categ_id'):
            pos_id = product['pos_categ_id'][0]
            if pos_id in self.pos_category_map:
                vals['pos_categ_ids'] = [(6, 0, [self.pos_category_map[pos_id]])]

        # UoM (Usando Cache)
        for uom_field in ['uom_id', 'uom_po_id']:
            if product.get(uom_field):
                u_id = product[uom_field][0]
                if u_id in self.valid_uom_ids:
                    vals[uom_field] = u_id

        return vals

    def sync_product(self, product: Dict):
        ext_id = f"sync_product_product_{product['id']}"
        try:
            vals = self.prepare_values(product)
            
            # Buscar si ya existe por external_id
            existing = self.target.search('ir.model.data', [('name', '=', ext_id), ('model', '=', 'product.product')], limit=1)
            
            if existing:
                res_id = self.target.search_read('ir.model.data', [('id', '=', existing[0])], ['res_id'])[0]['res_id']
                self.target.write('product.product', [res_id], vals)
                self.stats['updated'] += 1
            else:
                new_id = self.target.create('product.product', vals)
                self.target.create('ir.model.data', {
                    'name': ext_id, 'model': 'product.product', 'module': 'sync_script', 'res_id': new_id
                })
                self.stats['created'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en {product['name']}: {e}")
            self.stats['errors'] += 1

    def run(self):
        start_time = datetime.now()
        products = self.get_products_from_source()
        self.stats['total'] = len(products)

        for i, p in enumerate(products, 1):
            if i % 20 == 0: logger.info(f"Procesando {i}/{len(products)}...")
            self.sync_product(p)

        if SYNC_OPTIONS.get('incremental_sync') and self.stats['errors'] == 0:
            with open('last_product_sync.txt', 'w') as f:
                f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        logger.info(f"""
        === Resumen ===
        Total:   {self.stats['total']}
        Creados: {self.stats['created']}
        Editados:{self.stats['updated']}
        Errores: {self.stats['errors']}
        Tiempo:  {datetime.now() - start_time}
        """)

if __name__ == "__main__":
    sync = ProductSync()
    sync.run()