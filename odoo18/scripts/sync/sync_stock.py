#!/usr/bin/env python3
"""
Script de sincronización de STOCK/INVENTARIO
Odoo 16 (VPS) -> Odoo 18 (Local)

Lee las cantidades en mano (qty_available) de Odoo 16 y ajusta
el stock en Odoo 18 usando movimientos de inventario.

Uso:
    python3 sync_stock.py
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
        logging.FileHandler('sync_stock.log'),
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


class StockSync:
    """Sincroniza stock/inventario entre dos instancias de Odoo"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        
        # Ubicaciones importantes en Odoo 18
        self.target_location_stock = None  # Ubicación física principal
        self.target_location_inventory = None  # Ubicación virtual de inventario
        
        self.stats = {
            'total': 0,
            'adjusted': 0,
            'skipped': 0,
            'errors': 0,
            'total_qty_adjusted': 0.0
        }
        
        # Cargar ubicaciones del destino
        self.load_target_locations()
    
    def load_target_locations(self):
        """Carga las ubicaciones de stock necesarias en Odoo 18"""
        logger.info("Cargando ubicaciones de stock en Odoo 18...")
        
        try:
            # Ubicación física principal (WH/Stock)
            stock_location = self.target.search(
                'stock.location',
                [('usage', '=', 'internal'), ('name', '=', 'Stock')]
            )
            
            if stock_location:
                self.target_location_stock = stock_location[0]
                logger.info(f"✓ Ubicación de stock encontrada (ID: {self.target_location_stock})")
            else:
                # Si no encuentra "Stock", buscar la primera ubicación interna
                stock_location = self.target.search(
                    'stock.location',
                    [('usage', '=', 'internal')]
                )
                if stock_location:
                    self.target_location_stock = stock_location[0]
                    logger.info(f"✓ Ubicación interna encontrada (ID: {self.target_location_stock})")
                else:
                    raise Exception("No se encontró ninguna ubicación de stock interna")
            
            # Ubicación virtual de ajuste de inventario
            inventory_location = self.target.search(
                'stock.location',
                [('usage', '=', 'inventory')]
            )
            
            if inventory_location:
                self.target_location_inventory = inventory_location[0]
                logger.info(f"✓ Ubicación de inventario encontrada (ID: {self.target_location_inventory})")
            else:
                raise Exception("No se encontró ubicación virtual de inventario")
                
        except Exception as e:
            logger.error(f"❌ Error cargando ubicaciones: {e}")
            raise
    
    def get_product_mapping(self) -> Dict[int, int]:
        """Obtiene el mapeo de productos entre Odoo 16 y Odoo 18"""
        logger.info("Cargando mapeo de productos...")
        
        product_map = {}
        
        try:
            # Buscar todos los productos sincronizados
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
                # Extraer el ID de origen del nombre
                source_id = int(ext_id['name'].replace('sync_product_product_', ''))
                product_map[source_id] = ext_id['res_id']
            
            logger.info(f"✓ Cargados {len(product_map)} productos mapeados")
            
            if len(product_map) == 0:
                logger.warning("⚠ No se encontraron productos sincronizados")
                logger.warning("⚠ Ejecuta primero: python3 sync_products.py")
            
            return product_map
            
        except Exception as e:
            logger.error(f"❌ Error cargando mapeo de productos: {e}")
            raise
    
    def get_stock_from_source(self, product_ids: List[int]) -> Dict[int, float]:
        """Obtiene las cantidades en stock desde Odoo 16"""
        logger.info("Obteniendo cantidades de stock desde Odoo 16...")
        
        stock_data = {}
        
        try:
            # Leer cantidades de a lotes de 100
            batch_size = 100
            total_batches = (len(product_ids) + batch_size - 1) // batch_size
            
            for i in range(0, len(product_ids), batch_size):
                batch = product_ids[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"⏳ Leyendo lote {batch_num}/{total_batches} ({len(batch)} productos)...")
                
                products = self.source.search_read(
                    'product.product',
                    [('id', 'in', batch)],
                    ['id', 'name', 'default_code', 'qty_available', 'type']
                )
                
                for product in products:
                    # Solo sincronizar productos almacenables (type='product' en v16)
                    if product.get('type') == 'product':
                        stock_data[product['id']] = {
                            'qty': product.get('qty_available', 0.0),
                            'name': product.get('name'),
                            'code': product.get('default_code', 'Sin ref')
                        }
            
            logger.info(f"✓ Obtenidas cantidades de {len(stock_data)} productos almacenables")
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo stock: {e}")
            raise
    
    def get_current_stock_target(self, product_id: int) -> float:
        """Obtiene la cantidad actual en Odoo 18"""
        try:
            # Buscar el quant del producto en la ubicación principal
            quants = self.target.search_read(
                'stock.quant',
                [
                    ('product_id', '=', product_id),
                    ('location_id', '=', self.target_location_stock)
                ],
                ['quantity', 'reserved_quantity']
            )
            
            if quants:
                # Cantidad disponible = cantidad total - cantidad reservada
                total_qty = sum(q.get('quantity', 0) for q in quants)
                return total_qty
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"⚠ Error obteniendo stock actual: {e}")
            return 0.0
    
    def create_inventory_adjustment(self, product_id: int, product_name: str, 
                                   current_qty: float, target_qty: float) -> bool:
        """
        Crea un ajuste de inventario para un producto
        
        Actualiza directamente el campo 'quantity' en stock.quant
        que es el campo real del inventario
        """
        try:
            difference = target_qty - current_qty
            
            if abs(difference) < 0.01:  # Ignorar diferencias menores a 0.01
                logger.debug(f"Sin cambios para {product_name}: {current_qty}")
                return False
            
            # Buscar el quant existente
            existing_quants = self.target.search(
                'stock.quant',
                [
                    ('product_id', '=', product_id),
                    ('location_id', '=', self.target_location_stock)
                ]
            )
            
            if existing_quants:
                # Actualizar directamente el campo 'quantity' (no inventory_quantity)
                # Esto actualiza el stock real sin necesidad de aplicar ajustes
                try:
                    # Primero intentar con inventory_quantity + apply
                    self.target.write(
                        'stock.quant',
                        existing_quants,
                        {
                            'inventory_quantity': target_qty,
                            'inventory_quantity_set': True,
                            'inventory_diff_quantity': difference
                        }
                    )
                    
                    # Forzar el ajuste usando SQL directamente vía ORM
                    # Actualizar quantity directamente
                    self.target.write(
                        'stock.quant',
                        existing_quants,
                        {'quantity': target_qty}
                    )
                    
                except Exception as e:
                    logger.warning(f"Método estándar falló, usando actualización directa: {e}")
                    # Si todo falla, actualizar quantity directamente
                    self.target.write(
                        'stock.quant',
                        existing_quants,
                        {'quantity': target_qty}
                    )
            else:
                # Si no existe el quant, crearlo directamente con quantity
                quant_vals = {
                    'product_id': product_id,
                    'location_id': self.target_location_stock,
                    'quantity': target_qty,
                }
                
                self.target.create('stock.quant', quant_vals)
            
            action = "+" if difference > 0 else ""
            logger.info(f"✓ Ajustado: {product_name} ({current_qty:.2f} → {target_qty:.2f}) [{action}{difference:.2f}]")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ajustando {product_name}: {e}")
            return False
    
    def sync_stock(self):
        """Sincroniza el stock de todos los productos"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZANDO STOCK")
        logger.info("=" * 60)
        
        # Obtener mapeo de productos
        product_map = self.get_product_mapping()
        
        if not product_map:
            logger.error("❌ No hay productos para sincronizar")
            return
        
        # Obtener stock del origen
        source_product_ids = list(product_map.keys())
        stock_source = self.get_stock_from_source(source_product_ids)
        
        self.stats['total'] = len(stock_source)
        
        if not stock_source:
            logger.info("✓ No hay productos almacenables para sincronizar")
            return
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("AJUSTANDO INVENTARIO")
        logger.info("=" * 60)
        
        # Sincronizar cada producto
        for i, (source_id, stock_info) in enumerate(stock_source.items(), 1):
            target_id = product_map.get(source_id)
            
            if not target_id:
                logger.warning(f"⚠ Producto no mapeado: {stock_info['name']}")
                self.stats['skipped'] += 1
                continue
            
            try:
                product_name = f"[{stock_info['code']}] {stock_info['name']}"
                source_qty = stock_info['qty']
                
                # Mostrar progreso cada 50 productos
                if i % 50 == 0 or i == 1:
                    logger.info(f"[{i}/{len(stock_source)}] Procesando: {product_name}")
                
                # Obtener cantidad actual en destino
                current_qty = self.get_current_stock_target(target_id)
                
                # Crear ajuste si es necesario
                if self.create_inventory_adjustment(target_id, product_name, current_qty, source_qty):
                    self.stats['adjusted'] += 1
                    self.stats['total_qty_adjusted'] += abs(source_qty - current_qty)
                else:
                    self.stats['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Error con producto {stock_info['name']}: {e}")
                self.stats['errors'] += 1
    
    def run(self):
        """Ejecuta la sincronización completa"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 10 + "SINCRONIZACIÓN DE STOCK/INVENTARIO" + " " * 14 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Sincronizar stock
            self.sync_stock()
            
            # Resumen
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            logger.info(f"Total productos:     {self.stats['total']}")
            logger.info(f"✓ Ajustados:         {self.stats['adjusted']}")
            logger.info(f"⊙ Sin cambios:       {self.stats['skipped']}")
            logger.info(f"❌ Errores:           {self.stats['errors']}")
            logger.info(f"📦 Unidades ajustadas: {self.stats['total_qty_adjusted']:.2f}")
            logger.info(f"⏱ Tiempo:             {elapsed}")
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
        sync = StockSync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)