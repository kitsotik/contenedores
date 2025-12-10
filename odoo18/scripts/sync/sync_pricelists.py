#!/usr/bin/env python3
"""
Script de sincronización de LISTAS DE PRECIOS
Odoo 16 (VPS) -> Odoo 18 (Local)

Sincroniza:
- Listas de Precios (product.pricelist)
- Reglas de Precios (product.pricelist.item)

¡MODIFICADO para Odoo 16+: Se eliminó 'parent_id', 'discount_policy' y 'sequence'
de product.pricelist.item!

Uso:
    python3 sync_pricelists.py
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Set, Tuple
import sys
import os

# Asegurar que el directorio actual esté en el path para importar config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar configuración
try:
    from config import ODOO_16, ODOO_18, SYNC_OPTIONS
except ImportError as e:
    print("❌ Error: No se encontró el archivo config.py")
    print("\nVerifica que config.py existe en el mismo directorio que este script")
    sys.exit(1)

# Configuración de logging (como en tu script de categorías)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_pricelists.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =======================================================
# CLASE OdooConnection 
# =======================================================

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
    
    def search_read(self, model: str, domain: List, fields: List, offset: int = 0, limit: int = 0) -> List[Dict]:
        """Busca y lee registros"""
        kwargs = {'fields': fields}
        if offset > 0:
             kwargs['offset'] = offset
        if limit > 0:
             kwargs['limit'] = limit
        
        try:
            return self.models.execute_kw(
                self.config['db'],
                self.uid,
                self.config['password'],
                model,
                'search_read',
                [domain],
                kwargs
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

# =======================================================
# CLASE PriceListSync
# =======================================================

class PriceListSync:
    """Sincroniza Listas de Precios (product.pricelist y product.pricelist.item)"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        # Mapeo de IDs (source_id -> target_id)
        self.pricelist_map: Dict[int, int] = {}
        self.pricelist_item_map: Dict[int, int] = {}
        
        # Campos a sincronizar para product.pricelist
        # (Ya corregidos: sin 'parent_id' ni 'discount_policy')
        self.pricelist_fields = [
            'id', 'name', 'currency_id', 'active', 
            'sequence', 
        ]
        
        # Campos de reglas de precios (pricelist.item)
        # ¡CORRECCIÓN APLICADA! Se elimina 'sequence'
        self.pricelist_item_fields = [
            'id', 'name', 'applied_on', 'min_quantity', 'base', 'price_surcharge',
            'price_discount', 'price_round', 'price_min_margin', 'price_max_margin',
            'compute_price', 'date_start', 'date_end', 
            'product_tmpl_id', 
            'product_id',      
            'categ_id',        
            'pricelist_id',    
        ]
        
        self.stats = {
            'pricelists': {'total': 0, 'created': 0, 'updated': 0, 'errors': 0},
            'pricelist_items': {'total': 0, 'created': 0, 'updated': 0, 'errors': 0}
        }
        
        # Mapeos de IDs externos para dependencias
        self.product_tmpl_map = self._load_external_id_map('product.template')
        self.product_map = self._load_external_id_map('product.product')
        self.category_map = self._load_external_id_map('product.category')
        self.currency_map = self._load_external_id_map('res.currency')
        
    def _load_external_id_map(self, model: str) -> Dict[int, int]:
        """Carga el mapeo de IDs de Odoo 16 (Source) a Odoo 18 (Target)
           para modelos dependientes (ej: productos, categorías, monedas)."""
        
        model_clean = model.replace('.', '_')
        domain = [
            ('model', '=', model),
            ('module', '=', 'sync_script') # Módulo que usas en tu script de categorías
        ]
        fields = ['name', 'res_id']
        
        logger.info(f"Cargando mapeo de IDs para el modelo: {model}...")
        try:
            data = self.target.search_read('ir.model.data', domain, fields)
            
            id_map = {}
            for rec in data:
                try:
                    # Extraer source_id: sync_product_template_123 -> 123
                    name_parts = rec['name'].split('_')
                    if len(name_parts) >= 3 and name_parts[0] == 'sync' and name_parts[1] == model_clean:
                        source_id = int(name_parts[-1])
                        target_id = rec['res_id']
                        id_map[source_id] = target_id
                except ValueError:
                    logger.warning(f"No se pudo parsear el external ID: {rec['name']}")
                    continue
            
            logger.info(f"✓ Mapeo cargado para {model}: {len(id_map)} IDs encontrados.")
            return id_map
        except Exception as e:
            logger.error(f"❌ Error al cargar mapeo para {model}: {e}")
            return {}

    def get_external_id(self, model: str, source_id: int) -> str:
        """Genera un external_id único para mapear registros"""
        model_clean = model.replace('.', '_')
        return f"sync_{model_clean}_{source_id}"
    
    def find_existing_record(self, model: str, external_id: str) -> int:
        """Busca si el registro ya existe en Odoo 18 usando ir.model.data"""
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
                # Recuperar el res_id (ID del registro real)
                data = self.target.search_read(
                    'ir.model.data',
                    [('id', '=', existing[0])],
                    ['res_id']
                )
                return data[0]['res_id'] if data else None
            
            return None
        except Exception as e:
            logger.error(f"Error buscando registro existente (ir.model.data): {e}")
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

    # ========================================
    # LISTAS DE PRECIOS (product.pricelist)
    # ========================================
    
    def sync_pricelists(self):
        """Sincroniza las listas de precios principales"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZANDO LISTAS DE PRECIOS (product.pricelist)")
        logger.info("=" * 60)
        
        try:
            # Obtener todas las listas de precios
            pricelists = self.source.search_read('product.pricelist', [], self.pricelist_fields)
            
            logger.info(f"✓ Encontradas {len(pricelists)} listas de precios")
            self.stats['pricelists']['total'] = len(pricelists)
            
            if not pricelists:
                return
            
            # Sincronizar en orden
            for i, pricelist in enumerate(pricelists, 1):
                logger.info(f"[{i}/{len(pricelists)}] Procesando Lista: {pricelist['name']}")
                self.sync_pricelist(pricelist)
                
            logger.info("✓ Listas de precios sincronizadas. Continuando con Reglas...")
            
        except Exception as e:
            logger.error(f"❌ Error sincronizando listas de precios: {e}")

    def sync_pricelist(self, pricelist: Dict):
        """Sincroniza una lista de precios individual"""
        source_id = pricelist['id']
        pricelist_name = pricelist['name']
        external_id = self.get_external_id('product.pricelist', source_id)
        
        try:
            # Preparar valores (copiar solo los campos válidos en self.pricelist_fields)
            vals = {k: v for k, v in pricelist.items() if k in self.pricelist_fields and k != 'id'}
            
            # Manejar Moneda (currency_id)
            currency_id = pricelist.get('currency_id')
            if currency_id and isinstance(currency_id, (list, tuple)):
                source_currency_id = currency_id[0]
                target_currency_id = self.currency_map.get(source_currency_id)
                
                if target_currency_id:
                    vals['currency_id'] = target_currency_id
                else:
                    logger.warning(f"⚠ Moneda ID {source_currency_id} no mapeada. Usando Moneda por Defecto para {pricelist_name}.")
                    vals['currency_id'] = self.get_default_currency_id() 
            
            # Buscar si existe
            existing_id = self.find_existing_record('product.pricelist', external_id)
            
            if existing_id:
                # Actualizar 
                self.target.write('product.pricelist', [existing_id], vals)
                self.stats['pricelists']['updated'] += 1
                self.pricelist_map[source_id] = existing_id
            else:
                # Crear
                new_id = self.target.create('product.pricelist', vals)
                self.create_external_id('product.pricelist', external_id, new_id)
                self.stats['pricelists']['created'] += 1
                self.pricelist_map[source_id] = new_id
                
        except Exception as e:
            logger.error(f"❌ Error con Lista de Precios {pricelist_name}: {e}")
            self.stats['pricelists']['errors'] += 1

    def get_default_currency_id(self) -> int:
        """Obtiene el ID de la moneda por defecto del Target (Odoo 18)"""
        try:
            default_company_ids = self.target.search('res.company', [('id', '=', 1)])
            if not default_company_ids:
                default_company_ids = self.target.search('res.company', []) 

            if default_company_ids:
                company_data = self.target.search_read('res.company', [('id', '=', default_company_ids[0])], ['currency_id'])
                if company_data and company_data[0].get('currency_id'):
                    return company_data[0]['currency_id'][0] 
        except Exception as e:
             logger.error(f"Error al obtener moneda por defecto en Odoo 18: {e}")
        
        # ID de fallback. 1 suele ser EUR/USD o la primera moneda creada.
        return 1
        
    # ========================================
    # REGLAS DE PRECIOS (product.pricelist.item)
    # ========================================
    
    def sync_pricelist_items(self):
        """Sincroniza las reglas de precios asociadas a las listas"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZANDO REGLAS DE PRECIOS (product.pricelist.item)")
        logger.info("=" * 60)
        
        if not self.pricelist_map:
            logger.warning("⚠ No se han sincronizado listas de precios. Saltando reglas.")
            return

        # Solo buscar reglas para las listas de precios que se han sincronizado
        source_pricelist_ids = list(self.pricelist_map.keys())
        domain = [('pricelist_id', 'in', source_pricelist_ids)] 
        
        try:
            # Obtener todas las reglas
            items = self.source.search_read('product.pricelist.item', domain, self.pricelist_item_fields)
            
            logger.info(f"✓ Encontradas {len(items)} reglas de precios para sincronizar")
            self.stats['pricelist_items']['total'] = len(items)
            
            for i, item in enumerate(items, 1):
                logger.debug(f"[{i}/{len(items)}] Procesando Regla: {item.get('name', 'Regla sin nombre')}")
                self.sync_pricelist_item(item)
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando reglas de precios: {e}")

    def sync_pricelist_item(self, item: Dict):
        """Sincroniza una regla de precios individual"""
        source_id = item['id']
        external_id = self.get_external_id('product.pricelist.item', source_id)
        
        # Obtener el ID de la lista de precios (pricelist_id) del origen
        pricelist_source_id = item.get('pricelist_id')[0] 
        
        try:
            # 1. Preparar valores
            vals = {k: v for k, v in item.items() if k in self.pricelist_item_fields and k != 'id'}
            
            # 2. Mapear la Lista de Precios
            pricelist_target_id = self.pricelist_map.get(pricelist_source_id)
            if not pricelist_target_id:
                logger.error(f"❌ Error: Lista de Precios {pricelist_source_id} (Origen) no mapeada. Regla {source_id} no sincronizada.")
                self.stats['pricelist_items']['errors'] += 1
                return
            
            vals['pricelist_id'] = pricelist_target_id # Asignar el ID del destino
            
            # 3. Mapear Dependencias según 'applied_on'
            applied_on = vals.get('applied_on')
            
            if applied_on == '1_product': # Producto Variante (product.product)
                product_id = vals.pop('product_id', False)
                if product_id and isinstance(product_id, (list, tuple)):
                    vals['product_id'] = self.product_map.get(product_id[0])
            
            elif applied_on == '2_product_category': # Categoría de Producto (product.category)
                categ_id = vals.pop('categ_id', False)
                if categ_id and isinstance(categ_id, (list, tuple)):
                    vals['categ_id'] = self.category_map.get(categ_id[0])
                    
            elif applied_on == '3_product_template': # Producto Plantilla (product.template)
                product_tmpl_id = vals.pop('product_tmpl_id', False)
                if product_tmpl_id and isinstance(product_tmpl_id, (list, tuple)):
                    vals['product_tmpl_id'] = self.product_tmpl_map.get(product_tmpl_id[0])

            # 4. Manejar Campos de Fecha (Asegurar que son strings o None)
            for date_field in ['date_start', 'date_end']:
                if vals.get(date_field) and isinstance(vals[date_field], datetime):
                    vals[date_field] = vals[date_field].strftime('%Y-%m-%d')
                
            # 5. Buscar si existe
            existing_id = self.find_existing_record('product.pricelist.item', external_id)
            
            if existing_id:
                # Actualizar
                self.target.write('product.pricelist.item', [existing_id], vals)
                self.stats['pricelist_items']['updated'] += 1
                self.pricelist_item_map[source_id] = existing_id
            else:
                # Crear
                new_id = self.target.create('product.pricelist.item', vals)
                self.create_external_id('product.pricelist.item', external_id, new_id)
                self.stats['pricelist_items']['created'] += 1
                self.pricelist_item_map[source_id] = new_id
                
        except Exception as e:
            logger.error(f"❌ Error con Regla de Precio {source_id} (Lista {pricelist_source_id}): {e}")
            self.stats['pricelist_items']['errors'] += 1


    def run(self):
        """Ejecuta la sincronización completa de las listas y reglas de precios"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 10 + "SINCRONIZACIÓN DE LISTAS DE PRECIOS" + " " * 11 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Sincronizar Listas de Precios
            self.sync_pricelists()
            
            # Sincronizar Reglas de Precios
            self.sync_pricelist_items()
            
            # Resumen
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            
            logger.info("\n💲 LISTAS DE PRECIOS (product.pricelist):")
            logger.info(f"   Total:          {self.stats['pricelists']['total']}")
            logger.info(f"   ✓ Creadas:      {self.stats['pricelists']['created']}")
            logger.info(f"   ✓ Actualizadas: {self.stats['pricelists']['updated']}")
            logger.info(f"   ❌ Errores:      {self.stats['pricelists']['errors']}")
            
            logger.info("\n📜 REGLAS DE PRECIOS (product.pricelist.item):")
            logger.info(f"   Total:          {self.stats['pricelist_items']['total']}")
            logger.info(f"   ✓ Creadas:      {self.stats['pricelist_items']['created']}")
            logger.info(f"   ✓ Actualizadas: {self.stats['pricelist_items']['updated']}")
            logger.info(f"   ❌ Errores:      {self.stats['pricelist_items']['errors']}")
            
            logger.info(f"\n⏱ Tiempo total: {elapsed}")
            logger.info("=" * 60)
            
            total_errors = self.stats['pricelists']['errors'] + self.stats['pricelist_items']['errors']
            
            if total_errors == 0:
                logger.info("✓ ¡Sincronización de Listas de Precios completada exitosamente!")
            else:
                logger.warning(f"⚠ Completado con {total_errors} errores. Revise los errores críticos de dependencias.")
            
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}")
            raise


if __name__ == "__main__":
    try:
        sync = PriceListSync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)