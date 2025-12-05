#!/usr/bin/env python3
"""
sync_products.py
Sincronización de PRODUCTOS
Odoo 16 (VPS - ORIGEN) -> Odoo 18 (LOCAL - DESTINO)

Colocar este archivo junto a config.py (con ODOO_16, ODOO_18, SYNC_OPTIONS).

Características:
- Lee productos del origen (Odoo 16) y crea/actualiza en destino (Odoo 18).
- Sincroniza imagen principal (image_1920).
- Mapear categorías, POS categories, public categories, monedas e impuestos.
- Manejo robusto de many2one que puede venir como [id, name] o id simple.
- Detección segura de selection fields usando ast.literal_eval.
- Logs a archivo sync_products.log y STDOUT.
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Any
import sys
import os
import ast

# Asegurar que el directorio actual esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar config (debe existir en mismo directorio)
try:
    from config import ODOO_16, ODOO_18, SYNC_OPTIONS
except Exception as e:
    print("❌ Error: No se encontró config.py o tiene errores.")
    print(f"Detalle: {e}")
    sys.exit(1)

# Config logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_products.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# -------------------------
# Utilidades internas
# -------------------------
def normalize_m2o(value: Any) -> Any:
    """
    Normaliza un many2one/many2many entry.
    Acepta:
      - [id, 'Name']
      - id (int)
      - '123' (string con digitos)
      - None/False -> retorna None
    Retorna: int id o None, o lista de ids si viene una lista de many2many.
    """
    if value is None or value is False:
        return None
    # many2one como [id, name]
    if isinstance(value, (list, tuple)):
        # si es many2one: [id, name]
        if len(value) >= 1 and isinstance(value[0], int):
            return value[0]
        # si viene lista de ints (many2many)
        if all(isinstance(x, int) for x in value):
            return value
        # si viene lista de tuplas many2many-like, intentar extraer ids
        ids = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 1 and isinstance(item[0], int):
                ids.append(item[0])
            elif isinstance(item, int):
                ids.append(item)
        return ids if ids else None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def safe_parse_selection(selection_raw: Any):
    """
    Convierte la representación textual de selection a lista de tuplas
    usando ast.literal_eval o intentando interpretar si ya viene en formato usable.
    """
    if not selection_raw:
        return None
    # Si ya es una lista/tuple de tuplas
    if isinstance(selection_raw, (list, tuple)):
        return selection_raw
    # Si es string, usar ast.literal_eval con try/except
    if isinstance(selection_raw, str):
        try:
            parsed = ast.literal_eval(selection_raw)
            if isinstance(parsed, (list, tuple)):
                return parsed
        except Exception:
            # algunos Odoo devuelven string con comillas diferentes; fallback: intentar reemplazos simples
            try:
                cleaned = selection_raw.strip()
                parsed = ast.literal_eval(cleaned)
                if isinstance(parsed, (list, tuple)):
                    return parsed
            except Exception:
                logger.warning("No se pudo parsear selection string de ir.model.fields.")
                return None
    return None


# -------------------------
# Conexión Odoo
# -------------------------
class OdooConnection:
    def __init__(self, config: Dict, name: str):
        self.config = config
        self.name = name
        self.uid = None
        self.models = None
        self.connect()

    def connect(self):
        try:
            logger.info(f"Conectando a {self.name} ({self.config.get('url')})...")
            common = xmlrpc.client.ServerProxy(f"{self.config['url'].rstrip('/')}/xmlrpc/2/common")
            self.uid = common.authenticate(self.config['db'], self.config['username'], self.config['password'], {})
            if not self.uid:
                raise Exception("Autenticación fallida")
            self.models = xmlrpc.client.ServerProxy(f"{self.config['url'].rstrip('/')}/xmlrpc/2/object")
            version = common.version()
            logger.info(f"✓ Conectado a {self.name} - Versión: {version.get('server_version')}")
        except Exception as e:
            logger.error(f"❌ Error conectando a {self.name}: {e}")
            raise

    def execute_kw(self, model: str, method: str, args: list = None, kwargs: dict = None):
        """
        Wrapper directo a execute_kw para mayor control.
        args debe ser lista (p. ej. [domain]) ; kwargs diccionario de opciones (p. ej. {'fields': [...], 'limit': 1})
        """
        args = args or []
        kwargs = kwargs or {}
        return self.models.execute_kw(self.config['db'], self.uid, self.config['password'], model, method, args, kwargs)

    def search_read(self, model: str, domain: list, fields: list = None, limit: int = None) -> list:
        """search_read con manejo de limit y fields en kwargs (compatible con Odoo)."""
        try:
            options = {}
            if fields:
                options['fields'] = fields
            if limit:
                options['limit'] = limit
            return self.execute_kw(model, 'search_read', [domain], options)
        except Exception as e:
            logger.error(f"Error search_read en {model} - domain: {domain} - fields: {fields} - limit: {limit} -> {e}")
            raise

    def search(self, model: str, domain: list, limit: int = None) -> list:
        """search que devuelve lista de IDs; usa kwargs para limit"""
        try:
            options = {}
            if limit:
                options['limit'] = limit
            return self.execute_kw(model, 'search', [domain], options)
        except Exception as e:
            logger.error(f"Error search en {model} - domain: {domain} - limit: {limit} -> {e}")
            raise

    def create(self, model: str, values: dict) -> int:
        return self.execute_kw(model, 'create', [values])

    def write(self, model: str, record_ids: list, values: dict) -> bool:
        return self.execute_kw(model, 'write', [record_ids, values])


# -------------------------
# Sincronizador
# -------------------------
class ProductSync:
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")

        self.category_map = {}
        self.pos_category_map = {}
        self.public_category_map = {}

        self.valid_product_types = self.detect_valid_product_types()

        self.stats = {'total': 0, 'created': 0, 'updated': 0, 'errors': 0, 'images_synced': 0}

        self.load_category_mappings()

    def detect_valid_product_types(self) -> dict:
        """
        Detecta valores válidos para el selection del campo 'type' (product.template).
        Consulta ir.model.fields -> selection.
        """
        logger.info("Detectando tipos de producto válidos en Odoo 18...")
        try:
            # buscar registro de field (sin usar 'limit' como campo, sino como parámetro)
            field_info = self.target.search_read(
                'ir.model.fields',
                [('model', '=', 'product.template'), ('name', '=', 'type')],
                ['selection'],
                limit=1
            )
            if field_info and field_info[0].get('selection'):
                parsed = safe_parse_selection(field_info[0]['selection'])
                if parsed:
                    valid_types = {item[0]: item[1] for item in parsed if isinstance(item, (list, tuple)) and len(item) >= 2}
                    logger.info(f"✓ Tipos válidos detectados: {list(valid_types.keys())}")
                    return valid_types
        except Exception as e:
            logger.warning(f"No se pudieron detectar tipos válidos: {e}")

        # Fallback
        logger.info("Usando tipos por defecto de Odoo 18")
        return {'consu': 'Consumible', 'service': 'Servicio', 'product': 'Almacenable'}

    def convert_product_type(self, odoo16_type: str) -> tuple:
        if odoo16_type == 'product':
            return ('consu', True)
        elif odoo16_type == 'consu':
            return ('consu', False)
        elif odoo16_type == 'service':
            return ('service', False)
        else:
            logger.warning(f"Tipo desconocido '{odoo16_type}', usando 'consu'")
            return ('consu', False)

    def load_category_mappings(self):
        logger.info("Cargando mapeos de categorías (ir.model.data sync_script)...")
        try:
            product_cats = self.target.search_read(
                'ir.model.data',
                [('model', '=', 'product.category'), ('module', '=', 'sync_script'), ('name', 'like', 'sync_product_category_%')],
                ['name', 'res_id']
            )
            for cat in product_cats:
                try:
                    src = int(cat['name'].replace('sync_product_category_', ''))
                    self.category_map[src] = cat['res_id']
                except Exception:
                    continue
            logger.info(f"✓ Cargadas {len(self.category_map)} categorías de productos")
        except Exception as e:
            logger.warning(f"⚠ Error cargando mapeo de product.category: {e}")

        # POS
        try:
            pos_cats = self.target.search_read(
                'ir.model.data',
                [('model', '=', 'pos.category'), ('module', '=', 'sync_script'), ('name', 'like', 'sync_pos_category_%')],
                ['name', 'res_id']
            )
            for cat in pos_cats:
                try:
                    src = int(cat['name'].replace('sync_pos_category_', ''))
                    self.pos_category_map[src] = cat['res_id']
                except Exception:
                    continue
            logger.info(f"✓ Cargadas {len(self.pos_category_map)} categorías POS")
        except Exception:
            logger.info("⚠ No se encontraron categorías POS")

        # Public categories
        try:
            public_cats = self.target.search_read(
                'ir.model.data',
                [('model', '=', 'product.public.category'), ('module', '=', 'sync_script'), ('name', 'like', 'sync_product_public_category_%')],
                ['name', 'res_id']
            )
            for cat in public_cats:
                try:
                    src = int(cat['name'].replace('sync_product_public_category_', ''))
                    self.public_category_map[src] = cat['res_id']
                except Exception:
                    continue
            logger.info(f"✓ Cargadas {len(self.public_category_map)} categorías públicas")
        except Exception:
            logger.info("⚠ No se encontraron categorías públicas")

    def get_external_id(self, source_id: int) -> str:
        return f"sync_product_product_{source_id}"

    def get_last_sync_date(self) -> str:
        try:
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
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('last_product_sync.txt', 'w') as f:
                f.write(current_time)
            logger.info(f"✓ Fecha de sincronización guardada: {current_time}")
        except Exception as e:
            logger.warning(f"No se pudo guardar fecha de sincronización: {e}")

    def get_products_from_source(self) -> List[Dict]:
        logger.info("=" * 60)
        logger.info("OBTENIENDO PRODUCTOS DESDE ODOO 16")
        logger.info("=" * 60)

        domain = []
        if SYNC_OPTIONS.get('only_active', True):
            domain.append(('active', '=', True))

        if SYNC_OPTIONS.get('incremental_sync', False):
            last_sync = self.get_last_sync_date()
            if last_sync:
                domain.append(('write_date', '>', last_sync))
                logger.info(f"📅 Sincronización incremental: desde {last_sync}")

        if SYNC_OPTIONS.get('custom_filter'):
            domain.extend(SYNC_OPTIONS['custom_filter'])

        try:
            logger.info("📊 Buscando IDs de productos...")
            product_ids = self.source.search('product.product', domain)
            logger.info(f"✓ Encontrados {len(product_ids)} productos")
            if not product_ids:
                logger.info("✓ No hay productos para sincronizar")
                return []
            limit = SYNC_OPTIONS.get('product_limit', 0)
            if limit > 0 and len(product_ids) > limit:
                logger.info(f"⚠ Aplicando límite: solo {limit} productos")
                product_ids = product_ids[:limit]
        except Exception as e:
            logger.error(f"❌ Error buscando productos: {e}")
            raise

        # Campos base
        fields = [
            'id', 'name', 'default_code', 'barcode', 'type', 'categ_id',
            'list_price', 'standard_price', 'uom_id', 'uom_po_id',
            'description', 'description_sale', 'description_purchase',
            'weight', 'volume', 'sale_ok', 'purchase_ok', 'active',
            'pos_categ_id', 'public_categ_ids', 'taxes_id', 'supplier_taxes_id',
            'write_date'
        ]
        custom_fields = SYNC_OPTIONS.get('custom_product_fields', [])
        if custom_fields:
            fields.extend(custom_fields)
            logger.info(f"✓ Campos personalizados solicitados: {', '.join(custom_fields)}")

        products = []
        logger.info("📦 Descargando datos de productos (sin imágenes)...")
        for i, pid in enumerate(product_ids, 1):
            try:
                if i % 50 == 0 or i == 1:
                    logger.info(f"⏳ Descargando producto {i}/{len(product_ids)} (ID {pid})...")
                data = self.source.search_read('product.product', [('id', '=', pid)], fields)
                if data:
                    products.append(data[0])
            except Exception as e:
                err = str(e)
                if 'Invalid field' in err or 'invalid field' in err.lower():
                    logger.warning(f"⚠ Producto {pid}: posible campo personalizado inválido, reintentando sin personalizados")
                    minimal = [f for f in fields if f not in custom_fields]
                    try:
                        data = self.source.search_read('product.product', [('id', '=', pid)], minimal)
                        if data:
                            products.append(data[0])
                            logger.info(f"✓ Producto {pid} descargado sin personalizados")
                    except Exception as e2:
                        logger.error(f"❌ No se pudo descargar producto {pid}: {e2}")
                else:
                    logger.error(f"❌ Error descargando producto {pid}: {e}")

        logger.info(f"✓ Descargados {len(products)} productos")

        # Descargar imágenes aparte (más tolerante)
        if SYNC_OPTIONS.get('sync_images', True):
            logger.info("🖼️ Descargando imágenes de productos...")
            for i, prod in enumerate(products, 1):
                try:
                    if i % 50 == 0 or i == 1:
                        logger.info(f"⏳ Descargando imagen {i}/{len(products)}...")
                    img = self.source.search_read('product.product', [('id', '=', prod['id'])], ['image_1920'])
                    if img and img[0].get('image_1920'):
                        prod['image_1920'] = img[0]['image_1920']
                except Exception as e:
                    logger.warning(f"⚠ No se pudo descargar imagen producto {prod.get('id')}: {e}")
            logger.info("✓ Descarga de imágenes completada")

        return products

    def sync_category(self, category_data) -> Any:
        if not category_data:
            return None
        source_id = normalize_m2o(category_data)
        if not source_id:
            return None
        return self.category_map.get(source_id)

    def sync_pos_categories(self, pos_category_ids) -> List[int]:
        if not pos_category_ids:
            return []
        target_ids = []
        # pos_category_ids puede ser id, [id], [(id,name), ...]
        if isinstance(pos_category_ids, (list, tuple)) and all(isinstance(x, int) for x in pos_category_ids):
            sids = pos_category_ids
        else:
            sids = []
            # intentar extraer
            if isinstance(pos_category_ids, (list, tuple)):
                for p in pos_category_ids:
                    nid = normalize_m2o(p)
                    if nid:
                        sids.append(nid)
            else:
                nid = normalize_m2o(pos_category_ids)
                if nid:
                    sids.append(nid)
        for sid in sids:
            tid = self.pos_category_map.get(sid)
            if tid:
                target_ids.append(tid)
        return target_ids

    def sync_public_categories(self, public_category_ids) -> List[int]:
        if not public_category_ids:
            return []
        ids = []
        if isinstance(public_category_ids, (list, tuple)) and all(isinstance(x, int) for x in public_category_ids):
            ids = public_category_ids
        else:
            if isinstance(public_category_ids, (list, tuple)):
                for p in public_category_ids:
                    nid = normalize_m2o(p)
                    if nid:
                        ids.append(nid)
            else:
                nid = normalize_m2o(public_category_ids)
                if nid:
                    ids.append(nid)
        target_ids = []
        for sid in ids:
            tid = self.public_category_map.get(sid)
            if tid:
                target_ids.append(tid)
        return target_ids

    def sync_currency(self, currency_data) -> Any:
        """
        Robust currency mapping:
        - acepta id (int) o [id, name]
        - lee el código 'name' en ORIGEN y busca por 'name' en DESTINO
        - devuelve el id de moneda en destino o None
        """
        if not currency_data:
            return None
        try:
            source_currency_id = normalize_m2o(currency_data)
            if not source_currency_id:
                return None

            # Leer moneda en ORIGEN
            currency_info = self.source.search_read('res.currency', [('id', '=', source_currency_id)], ['name'], limit=1)
            if not currency_info:
                logger.warning(f"Moneda origen id={source_currency_id} no encontrada")
                return None
            currency_code = currency_info[0].get('name')
            if not currency_code:
                logger.warning(f"Moneda origen id={source_currency_id} sin código (name)")
                return None

            # Buscar en DESTINO por código
            target = self.target.search('res.currency', [('name', '=', currency_code)], limit=1)
            if target:
                logger.debug(f"✓ Moneda mapeada: {currency_code} -> {target[0]}")
                return target[0]
            else:
                logger.warning(f"Moneda '{currency_code}' no encontrada en destino")
                return None
        except Exception as e:
            logger.warning(f"⚠ Error mapeando moneda: {e}")
            return None

    def sync_taxes(self, tax_ids) -> List[int]:
        if not tax_ids:
            return []
        ids = []
        # many2many/list of [id,name] or [(id,name),...]
        if isinstance(tax_ids, (list, tuple)):
            for t in tax_ids:
                nid = normalize_m2o(t)
                if nid:
                    ids.append(nid)
        elif isinstance(tax_ids, int):
            ids = [tax_ids]

        target_ids = []
        for sid in ids:
            existing = self.target.search('account.tax', [('id', '=', sid)])
            if existing:
                target_ids.append(sid)
            else:
                # posible mejora: intentar mapear por 'name' o 'amount' si tenés reglas
                pass
        return target_ids

    def prepare_values(self, product: Dict) -> Dict:
        product_type, is_storable = self.convert_product_type(product.get('type', 'consu'))
        vals = {
            'name': product.get('name'),
            'type': product_type,
            'active': product.get('active', True),
            'sale_ok': product.get('sale_ok', True),
            'purchase_ok': product.get('purchase_ok', True),
        }
        if product_type == 'consu':
            vals['is_storable'] = is_storable

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

        custom_fields = SYNC_OPTIONS.get('custom_product_fields', [])
        simple_custom_fields = ['replenishment_base_cost', 'list_price_type', 'sale_margin']
        for field in simple_custom_fields:
            if field in custom_fields and field in product and product.get(field) is not False:
                optional_fields[field] = product[field]

        for field, value in optional_fields.items():
            if value is not False and value is not None and value != '':
                vals[field] = value

        # Imagen principal
        if product.get('image_1920'):
            vals['image_1920'] = product['image_1920']
            self.stats['images_synced'] += 1

        # Categoría principal
        if product.get('categ_id'):
            categ_id = self.sync_category(product['categ_id'])
            if categ_id:
                vals['categ_id'] = categ_id
            else:
                default_cat = self.target.search('product.category', [('name', '=', 'All')], limit=1)
                if default_cat:
                    vals['categ_id'] = default_cat[0]

        # Moneda del costo base (campo personalizado)
        if 'replenishment_base_cost_on_currency' in custom_fields and product.get('replenishment_base_cost_on_currency'):
            cur_id = self.sync_currency(product.get('replenishment_base_cost_on_currency'))
            if cur_id:
                # campo en Odoo18 se llama igual según confirmación tuya
                vals['replenishment_base_cost_on_currency'] = cur_id

        # POS categories (manejar many2one -> many2many)
        if product.get('pos_categ_id'):
            pos_val = product['pos_categ_id']
            if isinstance(pos_val, (list, tuple)):
                pos_val = pos_val[0] if pos_val else None
            pos_cats = self.sync_pos_categories([pos_val] if pos_val else [])
            if pos_cats:
                vals['pos_categ_ids'] = [(6, 0, pos_cats)]
        elif product.get('pos_categ_ids'):
            pos_cats = self.sync_pos_categories(product['pos_categ_ids'])
            if pos_cats:
                vals['pos_categ_ids'] = [(6, 0, pos_cats)]

        # Public categories many2many
        if product.get('public_categ_ids'):
            public_cats = self.sync_public_categories(product['public_categ_ids'])
            if public_cats:
                vals['public_categ_ids'] = [(6, 0, public_cats)]

        # Taxes
        if product.get('taxes_id'):
            taxes = self.sync_taxes(product['taxes_id'])
            if taxes:
                vals['taxes_id'] = [(6, 0, taxes)]
        if product.get('supplier_taxes_id'):
            s_taxes = self.sync_taxes(product['supplier_taxes_id'])
            if s_taxes:
                vals['supplier_taxes_id'] = [(6, 0, s_taxes)]

        # UOM mapping (intentamos por id)
        if product.get('uom_id'):
            uom = normalize_m2o(product['uom_id'])
            if uom and self.target.search('uom.uom', [('id', '=', uom)], limit=1):
                vals['uom_id'] = uom
        if product.get('uom_po_id'):
            uom_po = normalize_m2o(product['uom_po_id'])
            if uom_po and self.target.search('uom.uom', [('id', '=', uom_po)], limit=1):
                vals['uom_po_id'] = uom_po

        return vals

    def find_existing_product(self, external_id: str) -> Any:
        try:
            existing = self.target.search('ir.model.data', [
                ('name', '=', external_id),
                ('model', '=', 'product.product'),
                ('module', '=', 'sync_script')
            ])
            if existing:
                data = self.target.search_read('ir.model.data', [('id', '=', existing[0])], ['res_id'], limit=1)
                if data:
                    return data[0].get('res_id')
            return None
        except Exception as e:
            logger.error(f"Error buscando producto existente: {e}")
            return None

    def create_external_id(self, external_id: str, record_id: int):
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
        source_id = product.get('id')
        product_name = product.get('name')
        product_ref = product.get('default_code', 'Sin ref')
        external_id = self.get_external_id(source_id)
        try:
            vals = self.prepare_values(product)
            existing = self.find_existing_product(external_id)
            if existing:
                self.target.write('product.product', [existing], vals)
                logger.info(f"✓ Actualizado: [{product_ref}] {product_name} (ID destino: {existing})")
                self.stats['updated'] += 1
            else:
                new_id = self.target.create('product.product', vals)
                self.create_external_id(external_id, new_id)
                logger.info(f"✓ Creado: [{product_ref}] {product_name} (ID destino: {new_id})")
                self.stats['created'] += 1
        except Exception as e:
            logger.error(f"❌ Error sincronizando [{product_ref}] {product_name}: {e}")
            self.stats['errors'] += 1

    def run(self):
        start_time = datetime.now()
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 12 + "SINCRONIZACIÓN DE PRODUCTOS" + " " * 19 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")

        try:
            products = self.get_products_from_source()
            self.stats['total'] = len(products)
            if not products:
                logger.warning("⚠ No hay productos para sincronizar")
                return

            logger.info("Comenzando sincronización de productos...")
            for i, prod in enumerate(products, 1):
                if i % 10 == 0 or i == 1:
                    logger.info(f"[{i}/{len(products)}] Procesando: [{prod.get('default_code','Sin ref')}] {prod.get('name')}")
                self.sync_product(prod)

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

            if self.stats['errors'] == 0 and SYNC_OPTIONS.get('incremental_sync', False):
                self.save_sync_date()
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}")
            raise


# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    try:
        sync = ProductSync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
