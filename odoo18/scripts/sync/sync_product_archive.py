#!/usr/bin/env python3
"""
Script de sincronización de ESTADO DE PRODUCTOS (Activo/Archivado)
Odoo 16 (VPS) -> Odoo 18 (Local)

Sincroniza el campo 'active' de productos:
- Si está archivado en Odoo 16 → Archiva en Odoo 18
- Si está activo en Odoo 16 → Activa en Odoo 18

BUSCA PRODUCTOS POR REFERENCIA INTERNA (default_code)

Uso:
    python3 sync_product_archive.py
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
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
    
    def search_read(self, model: str, domain: List, fields: List, context: Dict = None) -> List[Dict]:
        """Busca y lee registros"""
        try:
            kwargs = {'fields': fields}
            if context:
                kwargs['context'] = context
            
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
            logger.error(f"Error en search_read - Model: {model}")
            raise
    
    def search(self, model: str, domain: List, context: Dict = None) -> List[int]:
        """Busca IDs de registros"""
        kwargs = {}
        if context:
            kwargs['context'] = context
        return self.execute(model, 'search', domain, **kwargs)
    
    def write(self, model: str, record_ids: List[int], values: Dict, context: Dict = None) -> bool:
        """Actualiza registros"""
        kwargs = {}
        if context:
            kwargs['context'] = context
        
        return self.models.execute_kw(
            self.config['db'],
            self.uid,
            self.config['password'],
            model,
            'write',
            [record_ids, values],
            kwargs
        )


class ProductArchiveSync:
    """Sincroniza estado activo/archivado de productos"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        self.stats = {
            'total_o16': 0,
            'total_o18': 0,
            'matched': 0,
            'archived': 0,
            'activated': 0,
            'unchanged': 0,
            'not_found': 0,
            'errors': 0
        }
    
    def get_all_products_o16(self) -> Dict[str, Tuple[int, str, bool]]:
        """
        Obtiene TODOS los productos de Odoo 16 (activos y archivados)
        Retorna: {default_code: (id, name, active)}
        """
        logger.info("=" * 60)
        logger.info("OBTENIENDO PRODUCTOS DE ODOO 16")
        logger.info("=" * 60)
        
        try:
            # Leer TODOS los productos con active_test=False
            all_products = self.source.search_read(
                'product.product',
                [],
                ['id', 'name', 'default_code', 'active'],
                context={'active_test': False}
            )
            
            # Crear diccionario por default_code
            products_by_ref = {}
            products_without_ref = []
            
            for product in all_products:
                ref = product.get('default_code') or ''
                ref = ref.strip() if isinstance(ref, str) else ''
                
                if ref:  # Solo productos con referencia
                    products_by_ref[ref] = (
                        product['id'],
                        product.get('name', 'Sin nombre'),
                        product['active']
                    )
                else:
                    products_without_ref.append(product)
            
            active_count = sum(1 for p in all_products if p['active'])
            archived_count = len(all_products) - active_count
            
            logger.info(f"✓ Total productos en Odoo 16: {len(all_products)}")
            logger.info(f"  - Activos: {active_count}")
            logger.info(f"  - Archivados: {archived_count}")
            logger.info(f"  - Con referencia: {len(products_by_ref)}")
            logger.info(f"  - Sin referencia: {len(products_without_ref)}")
            
            if products_without_ref:
                logger.warning(f"⚠ {len(products_without_ref)} productos sin referencia no se sincronizarán")
            
            self.stats['total_o16'] = len(products_by_ref)
            return products_by_ref
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos de Odoo 16: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def get_all_products_o18(self) -> Dict[str, Tuple[int, str, bool]]:
        """
        Obtiene TODOS los productos de Odoo 18 (activos y archivados)
        Retorna: {default_code: (id, name, active)}
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("OBTENIENDO PRODUCTOS DE ODOO 18")
        logger.info("=" * 60)
        
        try:
            # Leer TODOS los productos con active_test=False
            all_products = self.target.search_read(
                'product.product',
                [],
                ['id', 'name', 'default_code', 'active'],
                context={'active_test': False}
            )
            
            # Crear diccionario por default_code
            products_by_ref = {}
            products_without_ref = []
            
            for product in all_products:
                ref = product.get('default_code') or ''
                ref = ref.strip() if isinstance(ref, str) else ''
                
                if ref:  # Solo productos con referencia
                    products_by_ref[ref] = (
                        product['id'],
                        product.get('name', 'Sin nombre'),
                        product['active']
                    )
                else:
                    products_without_ref.append(product)
            
            active_count = sum(1 for p in all_products if p['active'])
            archived_count = len(all_products) - active_count
            
            logger.info(f"✓ Total productos en Odoo 18: {len(all_products)}")
            logger.info(f"  - Activos: {active_count}")
            logger.info(f"  - Archivados: {archived_count}")
            logger.info(f"  - Con referencia: {len(products_by_ref)}")
            logger.info(f"  - Sin referencia: {len(products_without_ref)}")
            
            self.stats['total_o18'] = len(products_by_ref)
            return products_by_ref
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos de Odoo 18: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def sync_product_status(self, ref: str, o18_id: int, o18_name: str, 
                           o18_active: bool, should_be_active: bool):
        """Sincroniza el estado de un producto individual"""
        try:
            # Si el estado es diferente, actualizarlo
            if o18_active != should_be_active:
                # Actualizar con context para poder modificar archivados
                result = self.target.write(
                    'product.product',
                    [o18_id],
                    {'active': should_be_active},
                    context={'active_test': False}
                )
                
                action = "ACTIVADO" if should_be_active else "ARCHIVADO"
                status = "✓" if should_be_active else "📦"
                logger.info(f"{status} {action}: [{ref}] {o18_name} (ID: {o18_id})")
                
                if should_be_active:
                    self.stats['activated'] += 1
                else:
                    self.stats['archived'] += 1
            else:
                # Estado ya es correcto
                self.stats['unchanged'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error con [{ref}] {o18_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.stats['errors'] += 1
    
    def run(self):
        """Ejecuta la sincronización completa"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 8 + "SINCRONIZACIÓN DE ESTADO DE PRODUCTOS" + " " * 13 + "║")
        logger.info("║" + " " * 12 + "(Activo/Archivado)" + " " * 28 + "║")
        logger.info("║" + " " * 10 + "Búsqueda por REFERENCIA INTERNA" + " " * 17 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Obtener todos los productos de ambas instancias
            products_o16 = self.get_all_products_o16()
            products_o18 = self.get_all_products_o18()
            
            if not products_o16:
                logger.error("❌ No hay productos en Odoo 16")
                return
            
            if not products_o18:
                logger.error("❌ No hay productos en Odoo 18")
                return
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("SINCRONIZANDO ESTADO DE PRODUCTOS")
            logger.info("=" * 60)
            logger.info("Estrategia: Buscar por referencia interna (default_code)")
            logger.info("            Sincronizar estado Odoo 16 → Odoo 18")
            logger.info("")
            
            # Contadores para estadísticas
            active_in_o16 = sum(1 for (_, _, active) in products_o16.values() if active)
            archived_in_o16 = len(products_o16) - active_in_o16
            
            logger.info(f"📊 Productos en Odoo 16 (con referencia):")
            logger.info(f"   - Activos: {active_in_o16}")
            logger.info(f"   - Archivados: {archived_in_o16}")
            logger.info("")
            
            # Procesar cada producto de Odoo 18
            processed = 0
            for ref, (o18_id, o18_name, o18_active) in products_o18.items():
                processed += 1
                if processed % 100 == 0:
                    logger.info(f"⏳ Procesados {processed}/{len(products_o18)} productos...")
                
                # Buscar el producto en Odoo 16 por referencia
                if ref in products_o16:
                    o16_id, o16_name, o16_active = products_o16[ref]
                    self.stats['matched'] += 1
                    
                    # Sincronizar estado
                    self.sync_product_status(
                        ref, o18_id, o18_name, o18_active, o16_active
                    )
                else:
                    # Producto existe en O18 pero NO en O16 → Informar
                    logger.warning(f"⚠ Producto [{ref}] existe en Odoo 18 pero NO en Odoo 16")
                    self.stats['not_found'] += 1
            
            # Buscar productos que están en O16 pero NO en O18
            logger.info("")
            logger.info("Buscando productos de Odoo 16 que NO están en Odoo 18...")
            missing_in_o18 = []
            for ref in products_o16:
                if ref not in products_o18:
                    o16_id, o16_name, o16_active = products_o16[ref]
                    missing_in_o18.append((ref, o16_name, o16_active))
            
            if missing_in_o18:
                logger.warning(f"⚠ {len(missing_in_o18)} productos de Odoo 16 NO están en Odoo 18")
                if len(missing_in_o18) <= 10:
                    for ref, name, active in missing_in_o18:
                        state = "Activo" if active else "Archivado"
                        logger.warning(f"   - [{ref}] {name} ({state})")
                else:
                    logger.warning(f"   (Mostrando primeros 10)")
                    for ref, name, active in missing_in_o18[:10]:
                        state = "Activo" if active else "Archivado"
                        logger.warning(f"   - [{ref}] {name} ({state})")
            
            # Resumen
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            logger.info(f"Productos en Odoo 16 (con ref):  {self.stats['total_o16']}")
            logger.info(f"  - Activos:                     {active_in_o16}")
            logger.info(f"  - Archivados:                  {archived_in_o16}")
            logger.info(f"")
            logger.info(f"Productos en Odoo 18 (con ref):  {self.stats['total_o18']}")
            logger.info(f"")
            logger.info(f"🔗 Productos coincidentes:       {self.stats['matched']}")
            logger.info(f"✓ Activados en O18:              {self.stats['activated']}")
            logger.info(f"📦 Archivados en O18:             {self.stats['archived']}")
            logger.info(f"⊙ Sin cambios:                   {self.stats['unchanged']}")
            logger.info(f"⚠ Solo en O18:                   {self.stats['not_found']}")
            logger.info(f"⚠ Solo en O16:                   {len(missing_in_o18)}")
            logger.info(f"❌ Errores:                       {self.stats['errors']}")
            logger.info(f"⏱ Tiempo:                         {elapsed}")
            logger.info("=" * 60)
            
            if self.stats['errors'] == 0:
                logger.info("✓ ¡Sincronización completada exitosamente!")
                if self.stats['archived'] > 0:
                    logger.info(f"📦 Se archivaron {self.stats['archived']} productos en Odoo 18")
                if self.stats['activated'] > 0:
                    logger.info(f"✓ Se activaron {self.stats['activated']} productos en Odoo 18")
                if self.stats['unchanged'] > 0:
                    logger.info(f"⊙ {self.stats['unchanged']} productos ya estaban correctos")
            else:
                logger.warning(f"⚠ Completado con {self.stats['errors']} errores")
            
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}")
            import traceback
            logger.error(traceback.format_exc())
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