#!/usr/bin/env python3
"""
Script de sincronización de CATEGORÍAS DE PRODUCTOS
Odoo 16 (VPS) -> Odoo 18 (Local)

Sincroniza las 3 categorías:
- Categorías normales de productos (product.category)
- Categorías de POS (pos.category)
- Categorías de eCommerce/Sitio Web (product.public.category)

Respeta la jerarquía padre-hijo

Uso:
    python3 sync_categories.py
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
        logging.FileHandler('sync_categories.log'),
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


class CategorySync:
    """Sincroniza categorías entre dos instancias de Odoo"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        # Mapeo de IDs (source_id -> target_id) para cada tipo
        self.product_category_map = {}
        self.pos_category_map = {}
        self.public_category_map = {}
        
        self.stats = {
            'product_categories': {'total': 0, 'created': 0, 'updated': 0, 'errors': 0},
            'pos_categories': {'total': 0, 'created': 0, 'updated': 0, 'errors': 0},
            'public_categories': {'total': 0, 'created': 0, 'updated': 0, 'errors': 0}
        }
    
    def get_external_id(self, model: str, source_id: int) -> str:
        """Genera un external_id único para mapear registros"""
        model_clean = model.replace('.', '_')
        return f"sync_{model_clean}_{source_id}"
    
    def find_existing_record(self, model: str, external_id: str) -> int:
        """Busca si el registro ya existe en Odoo 18"""
        try:
            existing = self.target.search(
                'ir.model.data',
                [
                    ('name', '=', external_id),
                    ('model', '=', model),
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
            logger.error(f"Error buscando registro existente: {e}")
            return None
    
    def create_external_id(self, model: str, external_id: str, record_id: int):
        """Crea un external_id en Odoo 18"""
        try:
            self.target.create('ir.model.data', {
                'name': external_id,
                'model': model,
                'module': 'sync_script',
                'res_id': record_id
            })
        except Exception as e:
            logger.error(f"Error creando external_id: {e}")
    
    def order_categories_by_hierarchy(self, categories: List[Dict]) -> List[Dict]:
        """Ordena categorías para sincronizar primero padres, luego hijos"""
        ordered = []
        processed_ids = set()
        
        def add_category_and_children(cat_id):
            """Recursivamente agrega categoría y sus hijos"""
            if cat_id in processed_ids:
                return
            
            # Buscar la categoría
            category = next((c for c in categories if c['id'] == cat_id), None)
            if not category:
                return
            
            # Si tiene padre, asegurar que el padre esté procesado primero
            parent_id = category.get('parent_id')
            if parent_id and isinstance(parent_id, (list, tuple)):
                parent_id = parent_id[0]
                if parent_id not in processed_ids:
                    add_category_and_children(parent_id)
            
            # Agregar esta categoría
            ordered.append(category)
            processed_ids.add(cat_id)
        
        # Procesar todas las categorías
        for category in categories:
            add_category_and_children(category['id'])
        
        return ordered
    
    # ========================================
    # CATEGORÍAS DE PRODUCTOS (product.category)
    # ========================================
    
    def sync_product_categories(self):
        """Sincroniza categorías de productos"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZANDO CATEGORÍAS DE PRODUCTOS")
        logger.info("=" * 60)
        
        try:
            # Obtener todas las categorías
            fields = ['id', 'name', 'parent_id', 'complete_name']
            categories = self.source.search_read('product.category', [], fields)
            
            logger.info(f"✓ Encontradas {len(categories)} categorías de productos")
            self.stats['product_categories']['total'] = len(categories)
            
            if not categories:
                return
            
            # Ordenar por jerarquía
            ordered_categories = self.order_categories_by_hierarchy(categories)
            
            # Sincronizar en orden
            for i, category in enumerate(ordered_categories, 1):
                logger.info(f"[{i}/{len(ordered_categories)}] Procesando: {category.get('complete_name', category['name'])}")
                self.sync_product_category(category)
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando categorías de productos: {e}")
    
    def sync_product_category(self, category: Dict):
        """Sincroniza una categoría de producto individual"""
        source_id = category['id']
        category_name = category['name']
        external_id = self.get_external_id('product.category', source_id)
        
        try:
            # Preparar valores
            vals = {
                'name': category_name,
            }
            
            # Manejar categoría padre
            parent_id = category.get('parent_id')
            if parent_id and isinstance(parent_id, (list, tuple)):
                parent_source_id = parent_id[0]
                # Buscar el ID del padre en Odoo 18
                parent_target_id = self.product_category_map.get(parent_source_id)
                if parent_target_id:
                    vals['parent_id'] = parent_target_id
            
            # Buscar si existe
            existing_id = self.find_existing_record('product.category', external_id)
            
            if existing_id:
                # Actualizar
                self.target.write('product.category', [existing_id], vals)
                self.stats['product_categories']['updated'] += 1
                self.product_category_map[source_id] = existing_id
            else:
                # Crear
                new_id = self.target.create('product.category', vals)
                self.create_external_id('product.category', external_id, new_id)
                self.stats['product_categories']['created'] += 1
                self.product_category_map[source_id] = new_id
                
        except Exception as e:
            logger.error(f"❌ Error con categoría {category_name}: {e}")
            self.stats['product_categories']['errors'] += 1
    
    # ========================================
    # CATEGORÍAS DE POS (pos.category)
    # ========================================
    
    def sync_pos_categories(self):
        """Sincroniza categorías de POS"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZANDO CATEGORÍAS DE POS")
        logger.info("=" * 60)
        
        try:
            # Verificar si el modelo existe
            try:
                fields = ['id', 'name', 'parent_id']
                categories = self.source.search_read('pos.category', [], fields)
            except Exception as e:
                logger.warning("⚠ El modelo pos.category no existe o no está accesible. Saltando...")
                return
            
            logger.info(f"✓ Encontradas {len(categories)} categorías de POS")
            self.stats['pos_categories']['total'] = len(categories)
            
            if not categories:
                return
            
            # Ordenar por jerarquía
            ordered_categories = self.order_categories_by_hierarchy(categories)
            
            # Sincronizar en orden
            for i, category in enumerate(ordered_categories, 1):
                logger.info(f"[{i}/{len(ordered_categories)}] Procesando: {category['name']}")
                self.sync_pos_category(category)
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando categorías de POS: {e}")
    
    def sync_pos_category(self, category: Dict):
        """Sincroniza una categoría de POS individual"""
        source_id = category['id']
        category_name = category['name']
        external_id = self.get_external_id('pos.category', source_id)
        
        try:
            # Preparar valores
            vals = {
                'name': category_name,
            }
            
            # Manejar categoría padre
            parent_id = category.get('parent_id')
            if parent_id and isinstance(parent_id, (list, tuple)):
                parent_source_id = parent_id[0]
                parent_target_id = self.pos_category_map.get(parent_source_id)
                if parent_target_id:
                    vals['parent_id'] = parent_target_id
            
            # Buscar si existe
            existing_id = self.find_existing_record('pos.category', external_id)
            
            if existing_id:
                # Actualizar
                self.target.write('pos.category', [existing_id], vals)
                self.stats['pos_categories']['updated'] += 1
                self.pos_category_map[source_id] = existing_id
            else:
                # Crear
                new_id = self.target.create('pos.category', vals)
                self.create_external_id('pos.category', external_id, new_id)
                self.stats['pos_categories']['created'] += 1
                self.pos_category_map[source_id] = new_id
                
        except Exception as e:
            logger.error(f"❌ Error con categoría POS {category_name}: {e}")
            self.stats['pos_categories']['errors'] += 1
    
    # ========================================
    # CATEGORÍAS PÚBLICAS/WEB (product.public.category)
    # ========================================
    
    def sync_public_categories(self):
        """Sincroniza categorías públicas/eCommerce"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZANDO CATEGORÍAS DE SITIO WEB/eCOMMERCE")
        logger.info("=" * 60)
        
        try:
            # Verificar si el modelo existe
            try:
                fields = ['id', 'name', 'parent_id', 'sequence']
                categories = self.source.search_read('product.public.category', [], fields)
            except Exception as e:
                logger.warning("⚠ El modelo product.public.category no existe o no está accesible. Saltando...")
                return
            
            logger.info(f"✓ Encontradas {len(categories)} categorías públicas")
            self.stats['public_categories']['total'] = len(categories)
            
            if not categories:
                return
            
            # Ordenar por jerarquía
            ordered_categories = self.order_categories_by_hierarchy(categories)
            
            # Sincronizar en orden
            for i, category in enumerate(ordered_categories, 1):
                logger.info(f"[{i}/{len(ordered_categories)}] Procesando: {category['name']}")
                self.sync_public_category(category)
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando categorías públicas: {e}")
    
    def sync_public_category(self, category: Dict):
        """Sincroniza una categoría pública individual"""
        source_id = category['id']
        category_name = category['name']
        external_id = self.get_external_id('product.public.category', source_id)
        
        try:
            # Preparar valores
            vals = {
                'name': category_name,
            }
            
            # Secuencia si existe
            if category.get('sequence'):
                vals['sequence'] = category['sequence']
            
            # Manejar categoría padre
            parent_id = category.get('parent_id')
            if parent_id and isinstance(parent_id, (list, tuple)):
                parent_source_id = parent_id[0]
                parent_target_id = self.public_category_map.get(parent_source_id)
                if parent_target_id:
                    vals['parent_id'] = parent_target_id
            
            # Buscar si existe
            existing_id = self.find_existing_record('product.public.category', external_id)
            
            if existing_id:
                # Actualizar
                self.target.write('product.public.category', [existing_id], vals)
                self.stats['public_categories']['updated'] += 1
                self.public_category_map[source_id] = existing_id
            else:
                # Crear
                new_id = self.target.create('product.public.category', vals)
                self.create_external_id('product.public.category', external_id, new_id)
                self.stats['public_categories']['created'] += 1
                self.public_category_map[source_id] = new_id
                
        except Exception as e:
            logger.error(f"❌ Error con categoría pública {category_name}: {e}")
            self.stats['public_categories']['errors'] += 1
    
    def run(self):
        """Ejecuta la sincronización completa de todas las categorías"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 10 + "SINCRONIZACIÓN DE CATEGORÍAS" + " " * 20 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Sincronizar cada tipo de categoría
            self.sync_product_categories()
            self.sync_pos_categories()
            self.sync_public_categories()
            
            # Resumen
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            
            logger.info("\n📦 CATEGORÍAS DE PRODUCTOS:")
            logger.info(f"   Total:        {self.stats['product_categories']['total']}")
            logger.info(f"   ✓ Creadas:    {self.stats['product_categories']['created']}")
            logger.info(f"   ✓ Actualizadas: {self.stats['product_categories']['updated']}")
            logger.info(f"   ❌ Errores:    {self.stats['product_categories']['errors']}")
            
            logger.info("\n🏪 CATEGORÍAS DE POS:")
            logger.info(f"   Total:        {self.stats['pos_categories']['total']}")
            logger.info(f"   ✓ Creadas:    {self.stats['pos_categories']['created']}")
            logger.info(f"   ✓ Actualizadas: {self.stats['pos_categories']['updated']}")
            logger.info(f"   ❌ Errores:    {self.stats['pos_categories']['errors']}")
            
            logger.info("\n🌐 CATEGORÍAS DE SITIO WEB:")
            logger.info(f"   Total:        {self.stats['public_categories']['total']}")
            logger.info(f"   ✓ Creadas:    {self.stats['public_categories']['created']}")
            logger.info(f"   ✓ Actualizadas: {self.stats['public_categories']['updated']}")
            logger.info(f"   ❌ Errores:    {self.stats['public_categories']['errors']}")
            
            logger.info(f"\n⏱ Tiempo total: {elapsed}")
            logger.info("=" * 60)
            
            total_errors = (
                self.stats['product_categories']['errors'] +
                self.stats['pos_categories']['errors'] +
                self.stats['public_categories']['errors']
            )
            
            if total_errors == 0:
                logger.info("✓ ¡Sincronización completada exitosamente!")
            else:
                logger.warning(f"⚠ Completado con {total_errors} errores")
            
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}")
            raise


if __name__ == "__main__":
    try:
        sync = CategorySync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)