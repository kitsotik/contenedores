#!/usr/bin/env python3
"""
Script de sincronización de CLIENTES
Odoo 16 (VPS) -> Odoo 18 (Local)

Uso:
    python3 sync_customers.py
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
        logging.FileHandler('sync_customers.log'),
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
            # La sintaxis correcta para search_read con XML-RPC
            return self.models.execute_kw(
                self.config['db'],
                self.uid,
                self.config['password'],
                model,
                'search_read',
                [domain],  # domain va en una lista
                {'fields': fields}  # fields va en un diccionario
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


class CustomerSync:
    """Sincroniza clientes entre dos instancias de Odoo"""
    
    def __init__(self):
        self.source = OdooConnection(ODOO_16, "Odoo 16 (VPS)")
        self.target = OdooConnection(ODOO_18, "Odoo 18 (Local)")
        self.stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def get_external_id(self, source_id: int) -> str:
        """Genera un external_id único para mapear registros"""
        return f"sync_customer_{source_id}"
    
    def get_customers_from_source(self) -> List[Dict]:
        """Obtiene clientes desde Odoo 16"""
        logger.info("=" * 60)
        logger.info("OBTENIENDO CLIENTES DESDE ODOO 16")
        logger.info("=" * 60)
        
        # Construir dominio de búsqueda
        domain = [
            ('customer_rank', '>', 0),  # Solo clientes
        ]
        
        # Agregar filtro de activos si está configurado
        if SYNC_OPTIONS.get('only_active', True):
            domain.append(('active', '=', True))
        
        # Agregar filtros personalizados
        if SYNC_OPTIONS.get('custom_filter'):
            domain.extend(SYNC_OPTIONS['custom_filter'])
        
        # Campos básicos de cliente
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'mobile',
            'vat',
            'ref',
            'street',
            'street2',
            'city',
            'zip',
            'website',
            'is_company',
            'active',
            'country_id',
            'state_id',
            'l10n_ar_afip_responsibility_type_id'  # Campo AFIP
        ]
        
        # Agregar campos extras si están configurados
        if SYNC_OPTIONS.get('extra_fields'):
            fields.extend(SYNC_OPTIONS['extra_fields'])
        
        try:
            customers = self.source.search_read('res.partner', domain, fields)
            logger.info(f"✓ Encontrados {len(customers)} clientes")
            return customers
        except Exception as e:
            logger.error(f"❌ Error obteniendo clientes: {e}")
            raise
    
    def sync_country(self, country_data) -> int:
        """Sincroniza/busca país en Odoo 18"""
        if not country_data or not isinstance(country_data, (list, tuple)):
            return None
        
        country_id_source = country_data[0]
        
        # Intentar buscar el país por el mismo ID
        existing = self.target.search('res.country', [('id', '=', country_id_source)])
        if existing:
            return country_id_source
        
        # Si no existe por ID, buscar por nombre
        country_name = country_data[1] if len(country_data) > 1 else None
        if country_name:
            existing = self.target.search('res.country', [('name', '=', country_name)], limit=1)
            if existing:
                return existing[0]
        
        return None
    
    def sync_state(self, state_data) -> int:
        """Sincroniza/busca provincia/estado en Odoo 18"""
        if not state_data or not isinstance(state_data, (list, tuple)):
            return None
        
        state_id_source = state_data[0]
        
        # Intentar buscar por ID
        existing = self.target.search('res.country.state', [('id', '=', state_id_source)])
        if existing:
            return state_id_source
        
        # Si no existe, buscar por nombre
        state_name = state_data[1] if len(state_data) > 1 else None
        if state_name:
            existing = self.target.search('res.country.state', [('name', '=', state_name)], limit=1)
            if existing:
                return existing[0]
        
        return None
    
    def sync_afip_responsibility(self, afip_data) -> int:
        """Sincroniza/busca tipo de responsabilidad AFIP en Odoo 18"""
        if not afip_data or not isinstance(afip_data, (list, tuple)):
            return None
        
        afip_id_source = afip_data[0]
        
        # Intentar buscar por ID
        existing = self.target.search(
            'l10n_ar.afip.responsibility.type', 
            [('id', '=', afip_id_source)]
        )
        if existing:
            return afip_id_source
        
        # Si no existe, buscar por nombre
        afip_name = afip_data[1] if len(afip_data) > 1 else None
        if afip_name:
            existing = self.target.search(
                'l10n_ar.afip.responsibility.type', 
                [('name', '=', afip_name)]
            )
            if existing:
                return existing[0]
        
        return None
    
    def prepare_values(self, customer: Dict) -> Dict:
        """Prepara los valores para crear/actualizar en Odoo 18"""
        vals = {
            'name': customer['name'],
            'customer_rank': 1,  # Marcar como cliente
            'is_company': customer.get('is_company', True),
            'active': customer.get('active', True),
        }
        
        # Campos opcionales (solo incluir si tienen valor)
        optional_fields = {
            'email': customer.get('email'),
            'phone': customer.get('phone'),
            'mobile': customer.get('mobile'),
            'vat': customer.get('vat'),
            'ref': customer.get('ref'),
            'street': customer.get('street'),
            'street2': customer.get('street2'),
            'city': customer.get('city'),
            'zip': customer.get('zip'),
            'website': customer.get('website'),
        }
        
        # Solo agregar campos que no sean False/None/''
        for field, value in optional_fields.items():
            if value:
                vals[field] = value
        
        # Campos relacionales
        # País
        if customer.get('country_id'):
            country_id = self.sync_country(customer['country_id'])
            if country_id:
                vals['country_id'] = country_id
        
        # Estado/Provincia
        if customer.get('state_id'):
            state_id = self.sync_state(customer['state_id'])
            if state_id:
                vals['state_id'] = state_id
        
        # Responsabilidad AFIP
        if customer.get('l10n_ar_afip_responsibility_type_id'):
            afip_id = self.sync_afip_responsibility(customer['l10n_ar_afip_responsibility_type_id'])
            if afip_id:
                vals['l10n_ar_afip_responsibility_type_id'] = afip_id
        
        return vals
    
    def find_existing_customer(self, external_id: str) -> int:
        """Busca si el cliente ya existe en Odoo 18"""
        try:
            # Buscar por external_id
            existing = self.target.search(
                'ir.model.data',
                [
                    ('name', '=', external_id),
                    ('model', '=', 'res.partner'),
                    ('module', '=', 'sync_script')
                ]
            )
            
            if existing:
                # Obtener el res_id
                data = self.target.search_read(
                    'ir.model.data',
                    [('id', '=', existing[0])],
                    ['res_id']
                )
                return data[0]['res_id'] if data else None
            
            return None
        except Exception as e:
            logger.error(f"Error buscando cliente existente: {e}")
            return None
    
    def create_external_id(self, external_id: str, record_id: int):
        """Crea un external_id en Odoo 18"""
        try:
            self.target.create('ir.model.data', {
                'name': external_id,
                'model': 'res.partner',
                'module': 'sync_script',
                'res_id': record_id
            })
        except Exception as e:
            logger.error(f"Error creando external_id: {e}")
    
    def sync_customer(self, customer: Dict):
        """Sincroniza un cliente individual"""
        source_id = customer['id']
        customer_name = customer['name']
        external_id = self.get_external_id(source_id)
        
        try:
            # Preparar valores
            vals = self.prepare_values(customer)
            
            # Buscar si existe
            existing_id = self.find_existing_customer(external_id)
            
            if existing_id:
                # Actualizar cliente existente
                self.target.write('res.partner', [existing_id], vals)
                logger.info(f"✓ Actualizado: {customer_name} (ID: {existing_id})")
                self.stats['updated'] += 1
            else:
                # Crear nuevo cliente
                new_id = self.target.create('res.partner', vals)
                
                # Crear external_id para futuras sincronizaciones
                self.create_external_id(external_id, new_id)
                
                logger.info(f"✓ Creado: {customer_name} (ID: {new_id})")
                self.stats['created'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error con {customer_name}: {e}")
            self.stats['errors'] += 1
    
    def run(self):
        """Ejecuta la sincronización completa"""
        start_time = datetime.now()
        
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 12 + "SINCRONIZACIÓN DE CLIENTES" + " " * 20 + "║")
        logger.info("║" + " " * 15 + "Odoo 16 → Odoo 18" + " " * 26 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        
        try:
            # Obtener clientes
            customers = self.get_customers_from_source()
            self.stats['total'] = len(customers)
            
            if not customers:
                logger.warning("⚠ No se encontraron clientes para sincronizar")
                return
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("SINCRONIZANDO CLIENTES")
            logger.info("=" * 60)
            
            # Sincronizar cada cliente
            for i, customer in enumerate(customers, 1):
                logger.info(f"[{i}/{len(customers)}] Procesando: {customer['name']}")
                self.sync_customer(customer)
            
            # Resumen
            elapsed = datetime.now() - start_time
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN DE SINCRONIZACIÓN")
            logger.info("=" * 60)
            logger.info(f"Total procesados: {self.stats['total']}")
            logger.info(f"✓ Creados:       {self.stats['created']}")
            logger.info(f"✓ Actualizados:  {self.stats['updated']}")
            logger.info(f"❌ Errores:       {self.stats['errors']}")
            logger.info(f"⏱ Tiempo:         {elapsed}")
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
        sync = CustomerSync()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n⚠ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)