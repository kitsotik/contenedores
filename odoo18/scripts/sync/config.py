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
        'internal_code',
        'replenishment_base_cost',
        'replenishment_base_cost_currency_id',  # Moneda del costo base
        'list_price_type',
        'sale_margin'
        ],
}