#!/usr/bin/env python3
"""
Script de sincronización de PRODUCTOS
Odoo 16 (VPS) -> Odoo 18 (Local)

Sincroniza:
- Datos del producto
- Imágenes (image_1920, image_1024, image_512, etc.)
- Categorías (vinculando con las ya sincronizadas)
- Variantes de producto

Uso:
    python3 sync_products.py
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List
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
            logger.info(f"Conectando a {self.name} en {self.config['url']}...")
            common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
            self.uid = common.authenticate(
                self.config['db'], 
                self.config['username'], 
                self.config['password'], 
                {}
            )
            
            if not self.uid:
                raise Exception(f"Autenticación fallida en {self.name}")
                
            self.models = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")
            
            # Obtener versión para verificar conexión
            version = common.version()
            logger.info(f"✓ Conectado a {self.name} (Versión: {version['server_version']})")
            
        except Exception as e:
            logger.error(f"❌ Error al conectar a {self.name}: {e}")
            raise

    def execute(self, model: str, method: str, *args, **kwargs):
        """Ejecuta un método en el modelo especificado"""
        try:
            return self.models.execute_kw(
                self.config['db'], 
                self.uid, 
                self.config['password'],
                model, 
                method, 
                args, 
                kwargs
            )
        except Exception as e:
            logger.error(f"Error ejecutando {method} en {model}: {e}")
            raise


class ProductSync:
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (Fuente)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Destino)")
        
        # Mapeos de IDs (Source ID -> Target ID)
        self.category_map = {}
        self.pos_category_map = {}
        self.public_category_map = {}
        self.tax_map = {}
        
        self.stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'images_synced': 0
        }
        
        # Mapeo de nombres de impuestos (Odoo 16 -> Odoo 18)
        self.tax_name_mapping = {
            'IVA 21%': 'VAT 21%',
            'IVA 10.5%': 'VAT 10.5%',
            'IVA 10,5%': 'VAT 10.5%',
            'IVA 0%': 'VAT 0%',
            'Exento': 'Exempt',
        }
        
        # Cargar mapeos iniciales
        self.load_initial_mappings()

    def load_initial_mappings(self):
        """Carga mapeos de categorías e impuestos"""
        logger.info("Cargando mapeos de datos maestros...")
        
        # 1. Cargar mapeos de Categorías de Producto
        self.load_category_mappings('product.category', self.category_map, 'sync_product_category_')
        
        # 2. Cargar mapeos de Categorías POS
        self.load_category_mappings('pos.category', self.pos_category_map, 'sync_pos_category_')
        
        # 3. Cargar mapeos de Categorías Públicas (E-commerce)
        self.load_category_mappings('product.public.category', self.public_category_map, 'sync_product_public_category_')
        
        # 4. Mapear impuestos por nombre
        self.map_taxes()

    def load_category_mappings(self, model, mapping_dict, prefix):
        """Busca External IDs en Odoo 18 para categorías ya sincronizadas"""
        try:
            # Buscar todos los ir.model.data que coincidan con el prefijo
            external_ids = self.target.execute(
                'ir.model.data', 'search_read',
                [('model', '=', model), ('module', '=', 'sync_script')],
                ['name', 'res_id']
            )
            
            for ext in external_ids:
                try:
                    # Extraer el ID original del nombre del external ID
                    source_id = int(ext['name'].replace(prefix, ''))
                    mapping_dict[source_id] = ext['res_id']
                except ValueError:
                    continue
            
            logger.info(f"✓ Cargados {len(mapping_dict)} mapeos para {model}")
        except Exception as e:
            logger.warning(f"⚠ No se pudieron cargar mapeos para {model}: {e}")

    def map_taxes(self):
        """Mapea impuestos de la fuente al destino por nombre"""
        logger.info("Mapeando impuestos por nombre...")
        
        # Obtener impuestos de Odoo 18
        target_taxes = self.target.execute(
            'account.tax', 'search_read',
            [('active', 'in', [True, False])],
            ['id', 'name', 'type_tax_use']
        )
        
        # Obtener impuestos de Odoo 16
        source_taxes = self.source.execute(
            'account.tax', 'search_read',
            [('active', 'in', [True, False])],
            ['id', 'name', 'type_tax_use']
        )
        
        for st in source_taxes:
            s_name = st['name']
            s_type = st['type_tax_use']
            
            # Buscar coincidencia exacta o por mapeo
            target_name = self.tax_name_mapping.get(s_name, s_name)
            
            match = next(
                (tt for tt in target_taxes 
                 if tt['name'] == target_name and tt['type_tax_use'] == s_type),
                None
            )
            
            if match:
                self.tax_map[st['id']] = match['id']
            else:
                # Intentar buscar por nombre si no hay coincidencia exacta con el tipo
                match_name = next((tt for tt in target_taxes if tt['name'] == target_name), None)
                if match_name:
                    self.tax_map[st['id']] = match_name['id']

        logger.info(f"✓ Mapeados {len(self.tax_map)} impuestos")

    def get_products_from_source(self) -> List[Dict]:
        """Obtiene productos de Odoo 16"""
        domain = [('active', '=', True)]
        
        if SYNC_OPTIONS.get('only_active', True):
            domain = [('active', '=', True)]
        else:
            domain = ['|', ('active', '=', True), ('active', '=', False)]
            
        # Filtro incremental opcional
        if SYNC_OPTIONS.get('incremental_sync', False):
            last_sync = self.get_last_sync_date()
            if last_sync:
                domain.append(('write_date', '>', last_sync))

        logger.info(f"Buscando productos en Odoo 16 con dominio: {domain}")
        
        limit = SYNC_OPTIONS.get('product_limit', 0)
        
        # Campos a extraer (Agregado 'internal_code')
        fields = [
            'id', 'name', 'default_code', 'internal_code', 'barcode', 'type', 'categ_id', 
            'list_price', 'standard_price', 'uom_id', 'uom_po_id',
            'description_sale', 'weight', 'volume', 'sale_ok', 'purchase_ok',
            'pos_categ_id', 'public_categ_ids', 'taxes_id', 'supplier_taxes_id',
            'available_in_pos', 'active'
        ]
        
        product_ids = self.source.execute('product.product', 'search', domain, limit=limit)
        
        if not product_ids:
            return []
            
        logger.info(f"Leyendo datos de {len(product_ids)} productos...")
        
        # Leer en lotes de 100 para no saturar la conexión
        products = []
        for i in range(0, len(product_ids), 100):
            batch_ids = product_ids[i:i+100]
            batch_data = self.source.execute('product.product', 'read', batch_ids, fields)
            products.extend(batch_data)
            logger.info(f"  - Progreso: {len(products)}/{len(product_ids)}")
            
        return products

    def prepare_values(self, product: Dict) -> Dict:
        """Prepara el diccionario de valores para Odoo 18"""
        
        # Mapeo de tipos de producto (Odoo 16 -> Odoo 18)
        # Odoo 18 usa 'consu' para productos almacenables con el flag is_storable=True
        p_type = product.get('type')
        is_storable = False
        
        if p_type == 'product':
            p_type = 'consu'
            is_storable = True
        elif p_type == 'consu':
            p_type = 'consu'
            is_storable = False
            
        vals = {
            'name': product['name'],
            'type': p_type,
            'default_code': product.get('default_code'),
            'internal_code': product.get('internal_code'), # <-- Agregado aquí
            'barcode': product.get('barcode'),
            'list_price': product.get('list_price', 0.0),
            'standard_price': product.get('standard_price', 0.0),
            'description_sale': product.get('description_sale'),
            'weight': product.get('weight', 0.0),
            'volume': product.get('volume', 0.0),
            'sale_ok': product.get('sale_ok', True),
            'purchase_ok': product.get('purchase_ok', True),
            'available_in_pos': product.get('available_in_pos', False),
            'active': product.get('active', True),
        }
        
        # En Odoo 18, el campo is_storable define si es almacenable
        if p_type == 'consu':
            vals['is_storable'] = is_storable

        # Mapear Categoría
        if product.get('categ_id'):
            s_categ_id = product['categ_id'][0]
            if s_categ_id in self.category_map:
                vals['categ_id'] = self.category_map[s_categ_id]

        # Mapear Categoría POS (En Odoo 18 es Many2many, en 16 es Many2one)
        if product.get('pos_categ_id'):
            s_pos_id = product['pos_categ_id'][0]
            if s_pos_id in self.pos_category_map:
                vals['pos_categ_ids'] = [(6, 0, [self.pos_category_map[s_pos_id]])]

        # Mapear Categorías Públicas (Many2many)
        if product.get('public_categ_ids'):
            target_pub_ids = []
            for s_pub_id in product['public_categ_ids']:
                if s_pub_id in self.public_category_map:
                    target_pub_ids.append(self.public_category_map[s_pub_id])
            if target_pub_ids:
                vals['public_categ_ids'] = [(6, 0, target_pub_ids)]

        # Mapear Impuestos de Ventas
        if product.get('taxes_id'):
            target_tax_ids = []
            for s_tax_id in product['taxes_id']:
                if s_tax_id in self.tax_map:
                    target_tax_ids.append(self.tax_map[s_tax_id])
            if target_tax_ids:
                vals['taxes_id'] = [(6, 0, target_tax_ids)]

        # Mapear Impuestos de Compras
        if product.get('supplier_taxes_id'):
            target_sup_tax_ids = []
            for s_tax_id in product['supplier_taxes_id']:
                if s_tax_id in self.tax_map:
                    target_sup_tax_ids.append(self.tax_map[s_tax_id])
            if target_sup_tax_ids:
                vals['supplier_taxes_id'] = [(6, 0, target_sup_tax_ids)]

        # Unidad de medida (asumimos que los IDs coinciden o ya existen)
        # Nota: Idealmente esto también debería estar mapeado por External ID o Nombre
        if product.get('uom_id'):
            vals['uom_id'] = product['uom_id'][0]
        if product.get('uom_po_id'):
            vals['uom_po_id'] = product['uom_po_id'][0]

        return vals

    def sync_product(self, product: Dict):
        """Crea o actualiza un producto en el destino"""
        external_id_name = f"sync_product_product_{product['id']}"
        
        try:
            # 1. Preparar valores base
            vals = self.prepare_values(product)
            
            # 2. Verificar si existe por External ID
            existing_record = self.target.execute(
                'ir.model.data', 'search_read',
                [('name', '=', external_id_name), ('model', '=', 'product.product')],
                ['res_id']
            )
            
            product_id = None
            if existing_record:
                product_id = existing_record[0]['res_id']
                # Actualizar
                self.target.execute('product.product', 'write', [product_id], vals)
                self.stats['updated'] += 1
            else:
                # Crear nuevo
                product_id = self.target.execute('product.product', 'create', vals)
                
                # Crear External ID
                self.target.execute('ir.model.data', 'create', {
                    'name': external_id_name,
                    'module': 'sync_script',
                    'model': 'product.product',
                    'res_id': product_id,
                    'noupdate': False
                })
                self.stats['created'] += 1

            # 3. Sincronizar imagen si está habilitado
            if SYNC_OPTIONS.get('sync_images', True) and product_id:
                self.sync_product_image(product['id'], product_id)

        except Exception as e:
            logger.error(f"❌ Error sincronizando producto ID {product['id']} ({product['name']}): {e}")
            self.stats['errors'] += 1

    def sync_product_image(self, source_id, target_id):
        """Sincroniza la imagen principal del producto"""
        try:
            # Leer imagen de la fuente
            source_data = self.source.execute(
                'product.product', 'read', 
                [source_id], 
                ['image_1920']
            )
            
            if source_data and source_data[0].get('image_1920'):
                self.target.execute(
                    'product.product', 'write', 
                    [target_id], 
                    {'image_1920': source_data[0]['image_1920']}
                )
                self.stats['images_synced'] += 1
        except Exception as e:
            logger.warning(f"  ⚠ No se pudo sincronizar imagen para producto {source_id}: {e}")

    def get_last_sync_date(self):
        if os.path.exists('last_product_sync.txt'):
            with open('last_product_sync.txt', 'r') as f:
                return f.read().strip()
        return None

    def save_sync_date(self):
        with open('last_product_sync.txt', 'w') as f:
            f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def run(self):
        """Ejecuta el proceso completo"""
        start_time = datetime.now()
        logger.info(f"Iniciando sincronización de productos a las {start_time}")
        
        try:
            # Obtener productos
            products = self.get_products_from_source()
            self.stats['total'] = len(products)
            
            # Procesar cada producto
            for i, product in enumerate(products, 1):
                pct = (i / len(products)) * 100
                logger.info(f"[{i}/{len(products)} - {pct:.1f}%] Sincronizando: {product['name']} (ID: {product['id']})")
                self.sync_product(product)
            
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            logger.info(f"Total procesados: {self.stats['total']}")
            logger.info(f"✓ Creados:       {self.stats['created']}")
            logger.info(f"✓ Actualizados:  {self.stats['updated']}")
            logger.info(f"🖼️  Imágenes:      {self.stats['images_synced']}")
            logger.info(f"❌ Errores:       {self.stats['errors']}")
            logger.info(f"⏱ Tiempo:         {elapsed}")
            logger.info("=" * 60)
            
            if self.stats['errors'] == 0:
                logger.info("✓ ¡Sincronización completada exitosamente!")
                # Guardar fecha de sincronización solo si fue exitosa
                if SYNC_OPTIONS.get('incremental_sync', False):
                    self.save_sync_date()
            else:
                logger.warning(f"⚠ Completado con {self.stats['errors']} errores")
            
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}")
            raise


if __name__ == "__main__":
    try:
        sync = ProductSync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\nSincronización cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)