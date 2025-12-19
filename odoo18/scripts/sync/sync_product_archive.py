#!/usr/bin/env python3
"""
Sincronización de ESTADO DE PRODUCTOS (Activo / Archivado)
Odoo 16 (VPS) -> Odoo 18 (Local)

Clave única: internal_code (campo custom en product.template)
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ODOO_16, ODOO_18

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("sync_product_archive.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# ODOO CONNECTION
# ------------------------------------------------------------
class OdooConnection:
    def __init__(self, config: Dict, name: str):
        self.config = config
        self.name = name
        self.uid = None
        self.models = None
        self.connect()

    def connect(self):
        logger.info(f"Conectando a {self.name}...")
        common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")

        self.uid = common.authenticate(
            self.config["db"],
            self.config["username"],
            self.config["password"],
            {}
        )
        if not self.uid:
            raise Exception(f"Fallo autenticación en {self.name}")

        self.models = xmlrpc.client.ServerProxy(
            f"{self.config['url']}/xmlrpc/2/object"
        )

        version = common.version()
        logger.info(f"✓ {self.name} conectado ({version['server_version']})")

    def search_read(self, model, domain, fields, context=None):
        kwargs = {"fields": fields}
        if context:
            kwargs["context"] = context

        return self.models.execute_kw(
            self.config["db"],
            self.uid,
            self.config["password"],
            model,
            "search_read",
            [domain],
            kwargs
        )

    def write(self, model, ids, values, context=None):
        kwargs = {}
        if context:
            kwargs["context"] = context

        return self.models.execute_kw(
            self.config["db"],
            self.uid,
            self.config["password"],
            model,
            "write",
            [ids, values],
            kwargs
        )


# ------------------------------------------------------------
# SYNC
# ------------------------------------------------------------
class ProductArchiveSync:

    def __init__(self):
        self.o16 = OdooConnection(ODOO_16, "Odoo 16")
        self.o18 = OdooConnection(ODOO_18, "Odoo 18")

        self.stats = {
            "matched": 0,
            "activated": 0,
            "archived": 0,
            "unchanged": 0,
            "errors": 0,
        }

    # --------------------------------------------------------
    # LOAD PRODUCTS (READ CODE FROM TEMPLATE)
    # --------------------------------------------------------
    def load_products(self, conn: OdooConnection) -> Dict[str, Tuple[int, str, bool]]:
        """
        Retorna:
        {
            internal_code: (product_id, name, active)
        }
        """
        logger.info(f"Cargando productos de {conn.name}...")

        products = conn.search_read(
            "product.product",
            [],
            ["id", "name", "active", "product_tmpl_id"],
            context={"active_test": False}
        )

        tmpl_ids = {
            p["product_tmpl_id"][0]
            for p in products
            if p.get("product_tmpl_id")
        }

        templates = conn.search_read(
            "product.template",
            [("id", "in", list(tmpl_ids))],
            ["id", "internal_code"],
            context={"active_test": False}
        )

        tmpl_code_map = {
            t["id"]: (t.get("internal_code") or "").strip()
            for t in templates
        }

        result = {}
        skipped = 0

        for p in products:
            tmpl_id = p["product_tmpl_id"][0]
            code = tmpl_code_map.get(tmpl_id)

            if not code:
                skipped += 1
                continue

            # Si hubiera múltiples variantes, se queda con la última
            result[code] = (
                p["id"],
                p.get("name", "Sin nombre"),
                p["active"]
            )

        logger.info(
            f"✓ {len(result)} productos con internal_code "
            f"({skipped} ignorados sin código)"
        )

        return result

    # --------------------------------------------------------
    # SYNC STATUS
    # --------------------------------------------------------
    def sync_status(self, code, o18_id, name, o18_active, should_be_active):
        try:
            if o18_active == should_be_active:
                self.stats["unchanged"] += 1
                return

            self.o18.write(
                "product.product",
                [o18_id],
                {"active": should_be_active},
                context={"active_test": False}
            )

            if should_be_active:
                logger.info(f"✓ ACTIVADO [{code}] {name}")
                self.stats["activated"] += 1
            else:
                logger.info(f"📦 ARCHIVADO [{code}] {name}")
                self.stats["archived"] += 1

        except Exception as e:
            logger.error(f"❌ Error [{code}] {name}: {e}")
            self.stats["errors"] += 1

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------
    def run(self):
        start = datetime.now()

        logger.info("==============================================")
        logger.info(" SINCRONIZACIÓN ACTIVO / ARCHIVADO")
        logger.info(" Clave: internal_code (product.template)")
        logger.info(" Odoo 16 → Odoo 18")
        logger.info("==============================================")

        products_16 = self.load_products(self.o16)
        products_18 = self.load_products(self.o18)

        for code, (o18_id, o18_name, o18_active) in products_18.items():
            if code not in products_16:
                continue

            _, _, o16_active = products_16[code]
            self.stats["matched"] += 1

            self.sync_status(
                code,
                o18_id,
                o18_name,
                o18_active,
                o16_active
            )

        elapsed = datetime.now() - start

        logger.info("==============================================")
        logger.info(" RESUMEN")
        logger.info("==============================================")
        logger.info(f"Coincidentes: {self.stats['matched']}")
        logger.info(f"Activados:    {self.stats['activated']}")
        logger.info(f"Archivados:   {self.stats['archived']}")
        logger.info(f"Sin cambios:  {self.stats['unchanged']}")
        logger.info(f"Errores:      {self.stats['errors']}")
        logger.info(f"Tiempo:       {elapsed}")
        logger.info("==============================================")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        ProductArchiveSync().run()
    except KeyboardInterrupt:
        logger.warning("⛔ Cancelado por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
