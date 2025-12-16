#!/usr/bin/env python3
"""
Script de sincronización de ESTADO DE PRODUCTOS (Activo/Archivado)
Odoo 16 (VPS) -> Odoo 18 (Local)

Sincroniza el campo 'active' de productos:
- Si está archivado en Odoo 16 → Archiva en Odoo 18
- Si está activo en Odoo 16 → Activa en Odoo 18

Uso:
    python3 sync_product_archive.py
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
            logger.error(f"Error en search_read - Model: {model}")
            raise
    
    def search(self, model: str, domain: List) -> List[int]:
        """Busca IDs de registros"""
        return self.execute(model, 'search', domain)
    
    def write(self, model: str, record_ids: List[int], values: Dict) -> bool:
        """Actualiza registros"""
        return self.execute(model, 'write', record_ids, values)


class ProductArchiveSync:
    """Sincroniza estado activo/archivado de productos"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        self.stats = {
            'total': 0,
            'archived': 0,
            'activated': 0,
            'unchanged': 0,
            'not_found': 0,
            'errors': 0
        }
    
    def get_product_mapping(self) -> Dict[int, int]:
        """Obtiene el mapeo de productos sincronizados"""
        logger.info("Cargando mapeo de productos...")
        
        product_map = {}
        
        try:
            external_ids = self.target.search_read(
                'ir.model.data',
                [
                    ('model', '=', 'product.product'),
                    ('module', '=', 'sync_script'),
                    ('name', 'like', 'sync_product_product_%')
                ],
                ['name', 'res_id']
            )
            
            for ext_id in external_ids:
                source_id = int(ext_id['name'].replace('sync_product_product_', ''))
                product_map[source_id] = ext_id['res_id']
            
            logger.info(f"✓ Cargados {len(product_map)} productos mapeados")
            return product_map
            
        except Exception as e:
            logger.error(f"❌ Error cargando mapeo: {e}")
            raise
    
    def get_all_products_status(self) -> Dict[int, tuple]:
        """
        Obtiene el estado (activo/archivado) de TODOS los productos en Odoo 16
        Incluyendo los archivados
        """
        logger.info("=" * 60)
        logger.info("OBTENIENDO ESTADO DE TODOS LOS PRODUCTOS")
        logger.info("=" * 60)
        
        try:
            # Buscar TODOS los productos (activos Y archivados)
            # Para incluir archivados, usamos context con active_test=False
            logger.info("Leyendo productos activos desde Odoo 16...")
            active_products = self.source.search_read(
                'product.product',
                [('active', '=', True)],
                ['id', 'name', 'default_code', 'active']
            )
            
            logger.info("Leyendo productos archivados desde Odoo 16...")
            # Para leer archivados, necesitamos cambiar el contexto
            archived_products = self.source.models.execute_kw(
                self.source.config['db'],
                self.source.uid,
                self.source.config['password'],
                'product.product',
                'search_read',
                [[('active', '=', False)]],
                {
                    'fields': ['id', 'name', 'default_code', 'active'],
                    'context': {'active_test': False}
                }
            )
            
            # Combinar todos los productos
            all_products = active_products + archived_products
            
            logger.info(f"✓ Total productos en Odoo 16: {len(all_products)}")
            logger.info(f"  - Activos: {len(active_products)}")
            logger.info(f"  - Archivados: {len(archived_products)}")
            
            # Crear diccionario {id: (name, ref, active)}
            products_status = {}
            for product in all_products:
                products_status[product['id']] = (
                    product.get('name', 'Sin nombre'),
                    product.get('default_code', 'Sin ref'),
                    product['active']
                )
            
            return products_status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos: {e}")
            raise
    
    def sync_product_status(self, source_id: int, target_id: int, 
                           product_name: str, product_ref: str, 
                           should_be_active: bool):
        """Sincroniza el estado de un producto individual"""
        try:
            # Obtener estado actual en Odoo 18
            target_product = self.target.search_read(
                'product.product',
                [('id', '=', target_id)],
                ['active']
            )
            
            if not target_product:
                logger.warning(f"⚠ Producto no encontrado en Odoo 18: [{product_ref}] {product_name}")
                self.stats['not_found'] += 1
                return
            
            current_active = target_product[0]['active']
            
            # Si el estado es diferente, actualizarlo
            if current_active != should_be_active:
                self.target.write(
                    'product.product',
                    [target_id],
                    {'active': should_be_active}
                )
                
                action = "ACTIVADO" if should_be_active else "ARCHIVADO"
                status = "✓" if should_be_active else "📦"
                logger.info(f"{status} {action}: [{product_ref}] {product_name} (ID: {target_id})")
                
                if should_be_active:
                    self.stats['activated'] += 1
                else:
                    self.stats['archived'] += 1
            else:
                # Estado ya es correcto
                self.stats['unchanged'] += 1
                logger.debug(f"⊙ Sin cambios: [{product_ref}] {product_name}")
                
        except Exception as e:
            logger.error(f"❌ Error con [{product_ref}] {product_name}: {e}")
            self.stats['errors'] += 1
    
    def run(self):
        """Ejecuta la sincronización completa"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 8 + "SINCRONIZACIÓN DE ESTADO DE PRODUCTOS" + " " * 13 + "║")
        logger.info("║" + " " * 12 + "(Activo/Archivado)" + " " * 28 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Obtener mapeo de productos
            product_map = self.get_product_mapping()
            
            if not product_map:
                logger.error("❌ No hay productos sincronizados")
                return
            
            # Obtener estado de todos los productos en Odoo 16
            products_status = self.get_all_products_status()
            
            self.stats['total'] = len(product_map)
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("SINCRONIZANDO ESTADO DE PRODUCTOS")
            logger.info("=" * 60)
            
            # Sincronizar cada producto
            processed = 0
            for source_id, target_id in product_map.items():
                if source_id in products_status:
                    product_name, product_ref, should_be_active = products_status[source_id]
                    
                    # Mostrar progreso cada 100 productos
                    processed += 1
                    if processed % 100 == 0:
                        logger.info(f"⏳ Procesados {processed}/{len(product_map)} productos...")
                    
                    self.sync_product_status(
                        source_id, 
                        target_id, 
                        product_name, 
                        product_ref, 
                        should_be_active
                    )
                else:
                    logger.warning(f"⚠ Producto {source_id} no encontrado en origen")
                    self.stats['not_found'] += 1
            
            # Resumen
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            logger.info(f"Total productos:    {self.stats['total']}")
            logger.info(f"✓ Activados:        {self.stats['activated']}")
            logger.info(f"📦 Archivados:       {self.stats['archived']}")
            logger.info(f"⊙ Sin cambios:      {self.stats['unchanged']}")
            logger.info(f"⚠ No encontrados:   {self.stats['not_found']}")
            logger.info(f"❌ Errores:          {self.stats['errors']}")
            logger.info(f"⏱ Tiempo:            {elapsed}")
            logger.info("=" * 60)
            
            if self.stats['errors'] == 0:
                logger.info("✓ ¡Sincronización completada exitosamente!")
            else:
                logger.warning(f"⚠ Completado con {self.stats['errors']} errores")
            
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}")
            raise


if __name__ == "__main__":
    try:
        sync = ProductArchiveSync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)