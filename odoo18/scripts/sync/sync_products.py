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
    print(f"Directorio actual: {os.getcwd()}")
    print(f"Script ubicado en: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"Error técnico: {e}")
    print("\nVerifica que config.py existe en el mismo directorio que este script")
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

# TABLA DE MAPEO DE NOMBRES DE IMPUESTOS CONOCIDOS
# (Origen en español -> Destino en inglés)
TAX_NAME_MAP = {
    'IVA': 'VAT', 
    'I.V.A.': 'VAT',
    'Impuesto al Valor Agregado': 'VAT',
}


class OdooConnection:
    """Maneja la conexión a una instancia de Odoo"""
    
    def __init__(self, config: Dict, name: str):
        self.config = config
        self.name = name
        self.uid = None
        self.models = None
        self.connect()
    
    def connect(self):
        """Establece la conexión con Odoo"""
        try:
            logger.info(f"Conectando a {self.name} ({self.config['url']})...")
            
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
                raise Exception(f"Autenticación fallida en {self.name}")
            
            self.models = xmlrpc.client.ServerProxy(
                f"{self.config['url']}/xmlrpc/2/object"
            )
            
            # Verificar versión
            version = common.version()
            logger.info(f"✓ Conectado a {self.name} - Versión: {version['server_version']}")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a {self.name}: {e}")
            raise
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Ejecuta un método en Odoo"""
        return self.models.execute_kw(
            self.config['db'],
            self.uid,
            self.config['password'],
            model,
            method,
            args,
            kwargs
        )
    
    def search_read(self, model: str, domain: List, fields: List) -> List[Dict]:
        """Busca y lee registros"""
        try:
            return self.models.execute_kw(
                self.config['db'],
                self.uid,
                self.config['password'],
                model,
                'search_read',
                [domain],
                {'fields': fields}
            )
        except Exception as e:
            logger.error(f"Error en search_read - Model: {model}, Fields: {fields}")
            logger.error(f"Domain: {domain}")
            raise
    
    def search(self, model: str, domain: List, limit: int = None) -> List[int]:
        """Busca IDs de registros"""
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        return self.execute(model, 'search', domain, kwargs)
    
    def create(self, model: str, values: Dict) -> int:
        """Crea un registro"""
        return self.execute(model, 'create', values)
    
    def write(self, model: str, record_ids: List[int], values: Dict) -> bool:
        """Actualiza registros"""
        return self.execute(model, 'write', record_ids, values)


class ProductSync:
    """Sincroniza productos entre dos instancias de Odoo"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        # Mapeos de categorías (necesarios para vincular productos)
        self.category_map = {}
        self.pos_category_map = {}
        self.public_category_map = {}
        
        # Mapeo de tipos de producto (detectar valores válidos en Odoo 18)
        self.valid_product_types = self.detect_valid_product_types()
        
        self.stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'images_synced': 0
        }
        
        # Cargar mapeos de categorías
        self.load_category_mappings()
    
    def detect_valid_product_types(self) -> dict:
        """Detecta qué valores de 'type' son válidos en Odoo 18"""
        logger.info("Configurando tipos de producto para Odoo 18...")
        
        valid_types = {
            'consu': 'Consumible/Almacenable',
            'service': 'Servicio',
            'combo': 'Combo'
        }
        
        logger.info(f"✓ Tipos configurados: {list(valid_types.keys())}")
        return valid_types
    
    def convert_product_type(self, odoo16_type: str) -> tuple:
        """
        Convierte el tipo de producto de Odoo 16 a Odoo 18
        """
        if odoo16_type == 'product':
            # Almacenable en Odoo 16 = consu + is_storable en Odoo 18
            return ('consu', True)
        elif odoo16_type == 'consu':
            # Consumible
            return ('consu', False)
        elif odoo16_type == 'service':
            # Servicio (no tiene is_storable)
            return ('service', False)
        else:
            # Fallback: consumible
            logger.warning(f"Tipo desconocido '{odoo16_type}', usando 'consu'")
            return ('consu', False)
    
    def load_category_mappings(self):
        """Carga los mapeos de categorías sincronizadas previamente"""
        logger.info("Cargando mapeos de categorías...")
        
        try:
            # Cargar categorías de productos
            product_cats = self.target.search_read(
                'ir.model.data',
                [
                    ('model', '=', 'product.category'),
                    ('module', '=', 'sync_script'),
                    ('name', 'like', 'sync_product_category_%')
                ],
                ['name', 'res_id']
            )
            
            for cat in product_cats:
                source_id = int(cat['name'].replace('sync_product_category_', ''))
                self.category_map[source_id] = cat['res_id']
            
            logger.info(f"✓ Cargadas {len(self.category_map)} categorías de productos")
            
            # Cargar categorías POS
            try:
                pos_cats = self.target.search_read(
                    'ir.model.data',
                    [
                        ('model', '=', 'pos.category'),
                        ('module', '=', 'sync_script'),
                        ('name', 'like', 'sync_pos_category_%')
                    ],
                    ['name', 'res_id']
                )
                
                for cat in pos_cats:
                    source_id = int(cat['name'].replace('sync_pos_category_', ''))
                    self.pos_category_map[source_id] = cat['res_id']
                
                logger.info(f"✓ Cargadas {len(self.pos_category_map)} categorías de POS")
            except:
                logger.info("⚠ No se encontraron categorías de POS")
            
            # Cargar categorías públicas
            try:
                public_cats = self.target.search_read(
                    'ir.model.data',
                    [
                        ('model', '=', 'product.public.category'),
                        ('module', '=', 'sync_script'),
                        ('name', 'like', 'sync_product_public_category_%')
                    ],
                    ['name', 'res_id']
                )
                
                for cat in public_cats:
                    source_id = int(cat['name'].replace('sync_product_public_category_', ''))
                    self.public_category_map[source_id] = cat['res_id']
                
                logger.info(f"✓ Cargadas {len(self.public_category_map)} categorías públicas")
            except:
                logger.info("⚠ No se encontraron categorías públicas")
                
        except Exception as e:
            logger.warning(f"⚠ Error cargando mapeos de categorías: {e}")
            logger.warning("Los productos se crearán sin categorías")
    
    def get_external_id(self, source_id: int) -> str:
        """Genera un external_id único para mapear registros"""
        return f"sync_product_product_{source_id}"
    

    def get_last_sync_date(self) -> str:
        """Obtiene la fecha de la última sincronización"""
        try:
            # Buscar el archivo de última sincronización
            import os
            sync_file = 'last_product_sync.txt'
            
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    last_sync = f.read().strip()
                    logger.info(f"✓ Última sincronización: {last_sync}")
                    return last_sync
        except Exception as e:
            logger.warning(f"No se pudo leer última sincronización: {e}")
        
        return None
    
    def save_sync_date(self):
        """Guarda la fecha de sincronización actual"""
        try:
            from datetime import datetime
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open('last_product_sync.txt', 'w') as f:
                f.write(current_time)
            
            logger.info(f"✓ Fecha de sincronización guardada: {current_time}")
        except Exception as e:
            logger.warning(f"No se pudo guardar fecha de sincronización: {e}")
    
    def get_products_from_source(self) -> List[Dict]:
        """Obtiene productos desde Odoo 16 de uno en uno"""
        logger.info("=" * 60)
        logger.info("OBTENIENDO PRODUCTOS DESDE ODOO 16")
        logger.info("=" * 60)
        
        # Construir dominio de búsqueda
        domain = []
        
        # Agregar filtro de activos si está configurado
        if SYNC_OPTIONS.get('only_active', True):
            domain.append(('active', '=', True))
        
        # Sincronización incremental
        if SYNC_OPTIONS.get('incremental_sync', False):
            last_sync = self.get_last_sync_date()
            if last_sync:
                domain.append(('write_date', '>', last_sync))
                logger.info(f"📅 Sincronización incremental: solo productos modificados desde {last_sync}")
        
        # Agregar filtros personalizados
        if SYNC_OPTIONS.get('custom_filter'):
            domain.extend(SYNC_OPTIONS['custom_filter'])
        
        # Primero, obtener solo los IDs (rápido)
        try:
            logger.info("📊 Buscando IDs de productos...")
            product_ids = self.source.search('product.product', domain)
            logger.info(f"✓ Encontrados {len(product_ids)} productos")
            
            if len(product_ids) == 0:
                logger.info("✓ No hay productos nuevos o modificados para sincronizar")
                return []
            
            # Aplicar límite si está configurado
            limit = SYNC_OPTIONS.get('product_limit', 0)
            if limit > 0 and len(product_ids) > limit:
                logger.info(f"⚠ Aplicando límite: solo se procesarán {limit} productos")
                product_ids = product_ids[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error buscando productos: {e}")
            raise
        
        # Campos base a leer
        fields = [
            'id', 'name', 'default_code', 'barcode', 'type', 'categ_id',
            'list_price', 'standard_price', 'uom_id', 'uom_po_id',
            'description', 'description_sale', 'description_purchase',
            'weight', 'volume', 'sale_ok', 'purchase_ok', 'active',
            'pos_categ_id', 'public_categ_ids', 'taxes_id', 'supplier_taxes_id',
            'available_in_pos',  # Campo para POS
            'write_date'  # Para sincronización incremental
        ]
        
        # Agregar campos personalizados desde config
        custom_fields = SYNC_OPTIONS.get('custom_product_fields', [])
        if custom_fields:
            fields.extend(custom_fields)
            logger.info(f"✓ Campos personalizados: {', '.join(custom_fields)}")
        
        # Descargar productos de uno en uno
        products = []
        logger.info("")
        logger.info("📦 Descargando datos de productos (sin imágenes)...")
        
        for i, product_id in enumerate(product_ids, 1):
            try:
                # Mostrar progreso cada 50 productos
                if i % 50 == 0 or i == 1:
                    logger.info(f"⏳ Descargando producto {i}/{len(product_ids)}...")
                
                # Leer este producto específico
                product_data = self.source.search_read(
                    'product.product',
                    [('id', '=', product_id)],
                    fields
                )
                
                if product_data:
                    products.append(product_data[0])
                    
            except Exception as e:
                error_str = str(e)
                # Si falla por un campo específico, reintentar sin campos personalizados
                if 'Invalid field' in error_str:
                    logger.warning(f"⚠ Producto {product_id}: campo personalizado inválido")
                    # Campos mínimos (sin personalizados)
                    minimal_fields = [f for f in fields if f not in custom_fields]
                    try:
                        product_data = self.source.search_read(
                            'product.product',
                            [('id', '=', product_id)],
                            minimal_fields
                        )
                        if product_data:
                            products.append(product_data[0])
                            logger.info(f"✓ Producto {product_id} descargado sin campos personalizados")
                    except Exception as e2:
                        logger.error(f"❌ No se pudo descargar producto {product_id}: {e2}")
                else:
                    logger.error(f"❌ Error descargando producto {product_id}: {e}")
        
        logger.info(f"✓ Descargados {len(products)} productos exitosamente")
        
        # Ahora descargar imágenes en una segunda pasada
        if SYNC_OPTIONS.get('sync_images', True):
            logger.info("")
            logger.info("🖼️  Descargando imágenes de productos...")
            
            for i, product in enumerate(products, 1):
                try:
                    if i % 50 == 0 or i == 1:
                        logger.info(f"⏳ Descargando imagen {i}/{len(products)}...")
                    
                    # Leer solo la imagen
                    image_data = self.source.search_read(
                        'product.product',
                        [('id', '=', product['id'])],
                        ['image_1920']
                    )
                    
                    if image_data and image_data[0].get('image_1920'):
                        product['image_1920'] = image_data[0]['image_1920']
                        
                except Exception as e:
                    logger.warning(f"⚠ No se pudo descargar imagen del producto {product.get('name', product['id'])}: {e}")
            
            logger.info(f"✓ Proceso de descarga de imágenes completado")
        
        return products
    
    def sync_category(self, category_data) -> int:
        """Busca la categoría mapeada en Odoo 18"""
        if not category_data or not isinstance(category_data, (list, tuple)):
            return None
        
        source_id = category_data[0]
        return self.category_map.get(source_id)
    
    def sync_pos_categories(self, pos_category_ids) -> List[int]:
        """Busca las categorías POS mapeadas en Odoo 18"""
        if not pos_category_ids:
            return []
        
        target_ids = []
        for source_id in pos_category_ids:
            target_id = self.pos_category_map.get(source_id)
            if target_id:
                target_ids.append(target_id)
        
        return target_ids
    
    def sync_public_categories(self, public_category_ids) -> List[int]:
        """Busca las categorías públicas mapeadas en Odoo 18"""
        if not public_category_ids:
            return []
        
        target_ids = []
        for source_id in public_category_ids:
            target_id = self.public_category_map.get(source_id)
            if target_id:
                target_ids.append(target_id)
        
        return target_ids
    
    def sync_currency(self, currency_data) -> int:
        """Sincroniza/busca moneda en Odoo 18 por código (USD, EUR, ARS, etc.)"""
        if not currency_data or not isinstance(currency_data, (list, tuple)):
            return None
        
        source_currency_id = currency_data[0]
        
        try:
            # Leer la moneda del origen para obtener su código
            currency_info = self.source.search_read(
                'res.currency',
                [('id', '=', source_currency_id)],
                ['name']  # 'name' es el código de la moneda (USD, EUR, ARS, etc.)
            )
            
            if not currency_info:
                logger.warning(f"⚠ No se encontró moneda con ID {source_currency_id} en origen")
                return None
            
            currency_code = currency_info[0]['name']
            
            # Buscar en Odoo 18 por código usando search (no search_read)
            target_currency_ids = self.target.search(
                'res.currency',
                [('name', '=', currency_code)]
            )
            
            if target_currency_ids and len(target_currency_ids) > 0:
                target_currency_id = target_currency_ids[0] if isinstance(target_currency_ids, list) else target_currency_ids
                logger.debug(f"✓ Moneda mapeada: {currency_code} (Origen: {source_currency_id} → Destino: {target_currency_id})")
                return target_currency_id
            else:
                logger.warning(f"⚠ Moneda '{currency_code}' no encontrada en Odoo 18")
                return None
                
        except Exception as e:
            logger.warning(f"⚠ Error mapeando moneda: {e}")
            return None
    
    def sync_taxes(self, tax_data) -> List[int]:
        """
        Busca impuestos en Odoo 18 por nombre, con lógica flexible para mapear IVA->VAT.
        Asegura que el input sea una lista limpia de IDs de impuestos de origen.
        """
        if not tax_data:
            return []
        
        source_tax_ids = []
        
        # --- LÓGICA DE LIMPIEZA DE DATOS DE ENTRADA (Maneja M2O, M2M, M2M lista de tuplas) ---
        if isinstance(tax_data, (list, tuple)):
            if len(tax_data) == 2 and isinstance(tax_data[0], int) and isinstance(tax_data[1], str):
                 # Caso M2O: [ID, Nombre]
                 source_tax_ids = [tax_data[0]]
            elif len(tax_data) > 0 and isinstance(tax_data[0], int):
                 # Caso M2M: [ID, ID, ...]
                 source_tax_ids = list(tax_data)
            elif len(tax_data) > 0 and isinstance(tax_data[0], (list, tuple)):
                 # Caso M2M: [[ID, Nombre], ...] - Limpiar a solo [ID, ...]
                 source_tax_ids = [t[0] for t in tax_data if isinstance(t, (list, tuple)) and len(t) >= 1 and isinstance(t[0], int)]

        if not source_tax_ids:
            return []
        # --- FIN DE LÓGICA DE LIMPIEZA ---
        
        target_ids = []
        for source_id in source_tax_ids:
            try:
                # 1. Leer el nombre del impuesto desde Odoo 16
                tax_info = self.source.search_read(
                    'account.tax',
                    [('id', '=', source_id)],
                    ['name']
                )
                
                if not tax_info:
                    logger.warning(f"⚠ Impuesto ID {source_id} no encontrado en origen")
                    continue
                
                tax_name = tax_info[0]['name'].strip()
                mapped_tax_name = tax_name # Valor por defecto
                
                # --- 2. INTENTO DE BÚSQUEDA ROBUSTA (Aplica IVA -> VAT) ---
                target_tax_ids = []
                
                # A. Buscar por nombre exacto (Caso: nombres iguales)
                target_tax_ids = self.target.search('account.tax', [('name', '=', tax_name)])
                
                if not target_tax_ids:
                    # B. Intentar mapeo y búsqueda flexible (Caso: IVA -> VAT)
                    for source_term, target_term in TAX_NAME_MAP.items():
                        # Usar CONTAINMENT (in) para manejar "IVA 21%" vs "IVA"
                        if source_term.lower() in tax_name.lower(): 
                            
                            # Reemplazar el término de origen (ej. 'iva') por el de destino (ej. 'vat')
                            # en el nombre completo (ej. 'iva 21.00%')
                            mapped_tax_name = tax_name.lower().replace(
                                source_term.lower(), 
                                target_term.lower(), 
                                1 # Solo el primer reemplazo
                            )
                            # Poner en mayúscula la primera letra de cada palabra (Title Case)
                            mapped_tax_name = mapped_tax_name.title().strip()
                            
                            logger.debug(f"  → Nombre mapeado: '{tax_name}' a '{mapped_tax_name}'")
                            
                            # Buscar con el nombre mapeado usando 'ilike' (flexible)
                            target_tax_ids = self.target.search(
                                'account.tax',
                                [('name', 'ilike', mapped_tax_name)] 
                            )
                            
                            if target_tax_ids:
                                break # Encontrado, salir del loop de mapeo
                            
                    
                # 3. Finalizar y añadir ID
                if target_tax_ids:
                    # Tomar el primero si hay varios
                    target_id = target_tax_ids[0] if isinstance(target_tax_ids, list) else target_tax_ids
                    if target_id not in target_ids: # Evitar duplicados
                         target_ids.append(target_id)
                    logger.debug(f"✓ Impuesto '{tax_name}' mapeado a ID: {target_id}")
                else:
                    logger.warning(f"⚠ Impuesto '{tax_name}' (Mapeo: '{mapped_tax_name}') NO ENCONTRADO en Odoo 18.")
                        
            except Exception as e:
                logger.warning(f"⚠ Error buscando impuesto {source_id}: {e}")
        
        return target_ids
    
    def prepare_values(self, product: Dict) -> Dict:
        """Prepara los valores para crear/actualizar en Odoo 18"""
        
        # Convertir tipo de producto (retorna tuple: type, is_storable)
        product_type, is_storable = self.convert_product_type(product.get('type', 'consu'))
        
        vals = {
            'name': product['name'],
            'type': product_type,
            'active': product.get('active', True),
            'sale_ok': product.get('sale_ok', True),
            'purchase_ok': product.get('purchase_ok', True),
            'available_in_pos': product.get('available_in_pos', False),
        }
        
        # Agregar is_storable si corresponde (solo para type='consu')
        if product_type == 'consu':
            vals['is_storable'] = is_storable
        
        # Campos opcionales simples
        optional_fields = {
            'default_code': product.get('default_code'),
            'barcode': product.get('barcode'),
            'list_price': product.get('list_price', 0.0),
            'standard_price': product.get('standard_price', 0.0),
            'description': product.get('description'),
            'description_sale': product.get('description_sale'),
            'description_purchase': product.get('description_purchase'),
            'weight': product.get('weight', 0.0),
            'volume': product.get('volume', 0.0),
        }
        
        # Agregar campos personalizados simples (no relacionales)
        custom_fields = SYNC_OPTIONS.get('custom_product_fields', [])
        simple_custom_fields = [
            'replenishment_base_cost',
            'list_price_type',
            'sale_margin'
        ]
        
        for field in simple_custom_fields:
            if field in custom_fields and field in product and product.get(field) is not False:
                optional_fields[field] = product[field]
        
        # Solo agregar campos que no sean False/None/''
        for field, value in optional_fields.items():
            if value is not False and value is not None and value != '':
                vals[field] = value
        
        # Imagen principal (base64)
        if product.get('image_1920'):
            vals['image_1920'] = product['image_1920']
            self.stats['images_synced'] += 1
        
        # === CAMPOS RELACIONALES ===
        
        # Categoría principal
        if product.get('categ_id'):
            categ_id = self.sync_category(product['categ_id'])
            if categ_id:
                vals['categ_id'] = categ_id
            else:
                # Usar categoría por defecto "All" si no encuentra
                default_cat = self.target.search('product.category', [('name', '=', 'All')], limit=1)
                if default_cat:
                    vals['categ_id'] = default_cat[0]
        
        # Moneda de costo base (campo personalizado relacional)
        currency_field = None
        if 'replenishment_base_cost_currency_id' in custom_fields and product.get('replenishment_base_cost_currency_id'):
            currency_field = 'replenishment_base_cost_currency_id'
        elif 'replenishment_base_cost_on_currency' in custom_fields and product.get('replenishment_base_cost_on_currency'):
            currency_field = 'replenishment_base_cost_on_currency'
        
        if currency_field:
            currency_id = self.sync_currency(product[currency_field])
            if currency_id:
                vals['replenishment_base_cost_currency_id'] = currency_id
                logger.debug(f"Moneda sincronizada para {product['name']}: {currency_id}")
        
        # Categorías POS
        if product.get('pos_categ_id'):
            pos_cat_id = product['pos_categ_id']
            if isinstance(pos_cat_id, (list, tuple)):
                pos_cat_id = pos_cat_id[0]
            
            pos_cats = self.sync_pos_categories([pos_cat_id])
            if pos_cats:
                vals['pos_categ_ids'] = [(6, 0, pos_cats)]
        
        elif product.get('pos_categ_ids'):
            pos_cats = self.sync_pos_categories(product['pos_categ_ids'])
            if pos_cats:
                vals['pos_categ_ids'] = [(6, 0, pos_cats)]
        
        # Categorías públicas (many2many)
        if product.get('public_categ_ids'):
            public_cats = self.sync_public_categories(product['public_categ_ids'])
            if public_cats:
                vals['public_categ_ids'] = [(6, 0, public_cats)]
        
        # === MANEJO DE IMPUESTOS (Venta y Compra) ===
        
        # Impuestos de venta (taxes_id)
        if 'taxes_id' in product and product.get('taxes_id'):
            tax_data = product['taxes_id']
            if tax_data and isinstance(tax_data, (list, tuple)) and len(tax_data) > 0:
                taxes = self.sync_taxes(tax_data)
                if taxes:
                    vals['taxes_id'] = [(6, 0, taxes)]
                    logger.debug(f"  Impuestos venta mapeados: {tax_data} → {taxes}")
        
        # Impuestos de compra (supplier_taxes_id) - Usa la misma función robusta
        if 'supplier_taxes_id' in product and product.get('supplier_taxes_id'):
            tax_data = product['supplier_taxes_id']
            if tax_data and isinstance(tax_data, (list, tuple)) and len(tax_data) > 0:
                supplier_taxes = self.sync_taxes(tax_data)
                if supplier_taxes:
                    vals['supplier_taxes_id'] = [(6, 0, supplier_taxes)]
                    logger.debug(f"  Impuestos compra mapeados: {tax_data} → {supplier_taxes}")
        
        # UOM (Unidad de medida) - intentar mapear por ID, si falla usar por defecto
        if product.get('uom_id') and isinstance(product['uom_id'], (list, tuple)):
            uom_id = product['uom_id'][0]
            # Verificar si existe en Odoo 18
            if self.target.search('uom.uom', [('id', '=', uom_id)]):
                vals['uom_id'] = uom_id
        
        if product.get('uom_po_id') and isinstance(product['uom_po_id'], (list, tuple)):
            uom_po_id = product['uom_po_id'][0]
            if self.target.search('uom.uom', [('id', '=', uom_po_id)]):
                vals['uom_po_id'] = uom_po_id
        
        return vals
    
    def find_existing_product(self, external_id: str) -> int:
        """Busca si el producto ya existe en Odoo 18"""
        try:
            existing = self.target.search(
                'ir.model.data',
                [
                    ('name', '=', external_id),
                    ('model', '=', 'product.product'),
                    ('module', '=', 'sync_script')
                ]
            )
            
            if existing:
                data = self.target.search_read(
                    'ir.model.data',
                    [('id', '=', existing[0])],
                    ['res_id']
                )
                return data[0]['res_id'] if data else None
            
            return None
        except Exception as e:
            logger.error(f"Error buscando producto existente: {e}")
            return None
    
    def create_external_id(self, external_id: str, record_id: int):
        """Crea un external_id en Odoo 18"""
        try:
            self.target.create('ir.model.data', {
                'name': external_id,
                'model': 'product.product',
                'module': 'sync_script',
                'res_id': record_id
            })
        except Exception as e:
            logger.error(f"Error creando external_id: {e}")
    
    def sync_product(self, product: Dict):
        """Sincroniza un producto individual"""
        source_id = product['id']
        product_name = product['name']
        product_ref = product.get('default_code', 'Sin ref')
        external_id = self.get_external_id(source_id)
        
        try:
            # Preparar valores
            vals = self.prepare_values(product)
            
            # Log de impuestos para debug
            if 'taxes_id' in vals:
                logger.info(f"  → Impuestos venta: {vals['taxes_id']}")
            if 'supplier_taxes_id' in vals:
                logger.info(f"  → Impuestos compra: {vals['supplier_taxes_id']}")
            
            # Buscar si existe
            existing_id = self.find_existing_product(external_id)
            
            if existing_id:
                # Actualizar producto existente
                self.target.write('product.product', [existing_id], vals)
                logger.info(f"✓ Actualizado: [{product_ref}] {product_name} (ID: {existing_id})")
                self.stats['updated'] += 1
            else:
                # Crear nuevo producto
                new_id = self.target.create('product.product', vals)
                
                # Crear external_id para futuras sincronizaciones
                self.create_external_id(external_id, new_id)
                
                logger.info(f"✓ Creado: [{product_ref}] {product_name} (ID: {new_id})")
                self.stats['created'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error con [{product_ref}] {product_name}: {e}")
            self.stats['errors'] += 1
    
    def run(self):
        """Ejecuta la sincronización completa"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 12 + "SINCRONIZACIÓN DE PRODUCTOS" + " " * 19 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 26 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Obtener productos
            products = self.get_products_from_source()
            self.stats['total'] = len(products)
            
            if not products:
                logger.warning("⚠ No se encontraron productos para sincronizar")
                return
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("SINCRONIZANDO PRODUCTOS")
            logger.info("=" * 60)
            
            # Sincronizar cada producto
            for i, product in enumerate(products, 1):
                product_ref = product.get('default_code', 'Sin ref')
                
                # Mostrar progreso cada 10 productos
                if i % 10 == 0 or i == 1:
                    logger.info(f"[{i}/{len(products)}] Procesando: [{product_ref}] {product['name']}")
                
                self.sync_product(product)
            
            # Resumen
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
        logger.info("\n⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)