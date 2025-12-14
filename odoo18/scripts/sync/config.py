"""
Archivo de configuración para sincronización Odoo
Edita los valores según tu entorno
"""

# ==========================================
# CONFIGURACIÓN ODOO 16 (VPS - ORIGEN)
# ==========================================
ODOO_16 = {
    'url': 'http://149.50.138.116:8069',  # URL completa sin /web al final
    'db': 'db',             # Nombre de la base de datos
    'username': 'admin',                   # Usuario de Odoo
    'password': 'bgt56yhn*971'              # Contraseña
}

# ==========================================
# CONFIGURACIÓN ODOO 18 (LOCAL - DESTINO)
# ==========================================
ODOO_18 = {
    'url': 'http://localhost:8069',        # URL local (o IP:puerto)
    'db': 'o18db',       # Nombre de la base de datos
    'username': 'admin',                   # Usuario de Odoo
    'password': 'bgt56yhn*971'                    # Contraseña
}

# ==========================================
# OPCIONES DE SINCRONIZACIÓN
# ==========================================
SYNC_OPTIONS = {
    # Solo sincronizar proveedores activos
    'only_active': True,
    
    # Campos adicionales a sincronizar (opcional)
    'extra_fields': [],
    
    # Filtro personalizado (dejar vacío para todos los proveedores)
    # Ejemplo: [('country_id.code', '=', 'AR')] para solo Argentina
    'custom_filter': [],
    
    # Límite de productos a sincronizar (0 = sin límite)
    # Útil para pruebas: usar 50 o 100 para probar primero
    'product_limit': 0,
    
    # Sincronizar imágenes de productos (puede ser lento)
    # True = sincronizar imágenes, False = solo datos
    'sync_images': True,
    
    # Sincronización incremental (solo productos nuevos/modificados)
    # True = solo sincronizar cambios desde última vez
    # False = sincronizar todos los productos
    'incremental_sync': True,
    
    # Campos personalizados de productos a sincronizar
    'custom_product_fields': [
        'replenishment_base_cost',
        'replenishment_base_cost_currency_id',  # Moneda del costo base
        'list_price_type',
        'sale_margin'
    ],
    
    # Mapeo manual de impuestos (Odoo 16 ID → Odoo 18 ID)
    # Basado en las imágenes proporcionadas
    'tax_mapping': {
        # IVA 21%
        63: 64,  # IVA 21% venta
        62: 65,  # IVA 21% venta (alternativo)
        
        # IVA 10.5%
        61: 62,  # IVA 10.5% venta
        60: 63,  # IVA 10.5% venta (alternativo)
        
        # IVA 27%
        64: 66,  # IVA 27% venta
        65: 67,  # IVA 27% venta (alternativo)
        
        # IVA 0% / Exento / No Gravado
        53: 54,  # IVA No Corresponde
        54: 55,  # IVA No Gravado
        55: 56,  # IVA No Gravado (alternativo)
        56: 57,  # IVA Exento
        57: 58,  # IVA Exento (alternativo)
        58: 60,  # IVA 0%
        59: 61,  # IVA 0% (alternativo)
        
        # Percepciones
        25: 27,  # Percepción IVA Aplicada
        70: 72,  # Percepción IVA Sufrida
        
        # Adicionales
        71: 73,  # IVA Adicional 20%
        67: 68,  # IVA 2,5%
        66: 69,  # IVA 2,5% (alternativo)
        68: 70,  # IVA 5%
        69: 71,  # IVA 5% (alternativo)
        
        # Compras (si los IDs son diferentes, agrégalos aquí)
        # Ejemplo: si en Odoo 16 compras usa ID 100 → Odoo 18 usa ID 200
    }
}