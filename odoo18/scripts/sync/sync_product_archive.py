#!/usr/bin/env python3
"""
Sincronización REAL de estado de productos (visual)
Odoo 16 (VPS) -> Odoo 18 (Local)

Clave única: internal_code (campo custom en product.template)

Sincroniza:
- product.template.active
- TODAS las product.product.active asociadas
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict
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
    def __init__(self, config, name):
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

    def search(self, model, domain, context=None):
        kwargs = {}
        if context:
            kwargs["context"] = context

        return self.models.execute_kw(
            self.config["db"],
            self.uid,
            self.config["password"],
            model,
            "search",
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
            "archived": 0,
            "activated": 0,
            "unchanged": 0,
            "errors": 0,
        }

    # --------------------------------------------------------
    # LOAD PRODUCTS (FROM TEMPLATE)
    # --------------------------------------------------------
    def load_templates(self, conn: OdooConnection) -> Dict[str, Dict]:
        logger.info(f"Cargando templates de {conn.name}...")

        templates = conn.search_read(
            "product.template",
            [],
            ["id", "internal_code", "active"],
            context={"active_test": False}
        )

        result = {}

        for t in templates:
            code = (t.get("internal_code") or "").strip()
            if not code:
                continue

            result[code] = {
                "tmpl_id": t["id"],
                "active": t["active"]
            }

        logger.info(f"✓ {len(result)} templates con internal_code")
        return result

    # --------------------------------------------------------
    # SYNC ONE PRODUCT
    # --------------------------------------------------------
    def sync_product(self, code, tmpl18_id, active18, active16):
        try:
            if active18 == active16:
                self.stats["unchanged"] += 1
                return

            # 1) TEMPLATE
            self.o18.write(
                "product.template",
                [tmpl18_id],
                {"active": active16},
                context={"active_test": False}
            )

            # 2) TODAS LAS VARIANTES
            variant_ids = self.o18.search(
                "product.product",
                [("product_tmpl_id", "=", tmpl18_id)],
                context={"active_test": False}
            )

            if variant_ids:
                self.o18.write(
                    "product.product",
                    variant_ids,
                    {"active": active16},
                    context={"active_test": False}
                )

            if active16:
                logger.info(f"✓ ACTIVADO [{code}] ({len(variant_ids)} variantes)")
                self.stats["activated"] += 1
            else:
                logger.info(f"📦 ARCHIVADO [{code}] ({len(variant_ids)} variantes)")
                self.stats["archived"] += 1

        except Exception as e:
            logger.error(f"❌ Error [{code}]: {e}")
            self.stats["errors"] += 1

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------
    def run(self):
        start = datetime.now()

        logger.info("================================================")
        logger.info(" SINCRONIZACIÓN VISUAL REAL DE PRODUCTOS")
        logger.info(" internal_code | template + variantes")
        logger.info(" Odoo 16 → Odoo 18")
        logger.info("================================================")

        t16 = self.load_templates(self.o16)
        t18 = self.load_templates(self.o18)

        for code, data18 in t18.items():
            if code not in t16:
                continue

            self.stats["matched"] += 1

            self.sync_product(
                code=code,
                tmpl18_id=data18["tmpl_id"],
                active18=data18["active"],
                active16=t16[code]["active"]
            )

        elapsed = datetime.now() - start

        logger.info("================================================")
        logger.info(" RESUMEN FINAL")
        logger.info("================================================")
        logger.info(f"Coincidentes: {self.stats['matched']}")
        logger.info(f"Activados:    {self.stats['activated']}")
        logger.info(f"Archivados:   {self.stats['archived']}")
        logger.info(f"Sin cambios:  {self.stats['unchanged']}")
        logger.info(f"Errores:      {self.stats['errors']}")
        logger.info(f"Tiempo:       {elapsed}")
        logger.info("================================================")


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
