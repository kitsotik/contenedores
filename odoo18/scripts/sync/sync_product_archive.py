#!/usr/bin/env python3
"""
Archivado por ausencia
Odoo 16 (fuente) -> Odoo 18 (destino)

Si un producto existe en Odoo 18 pero NO existe en Odoo 16
(se busca por internal_code),
entonces se ARCHIVA en Odoo 18.
"""

import xmlrpc.client
import logging
from datetime import datetime
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
        logging.FileHandler("sync_archive_by_absence.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# ODOO CONNECTION
# ------------------------------------------------------------
class Odoo:
    def __init__(self, cfg, name):
        self.cfg = cfg
        self.name = name

        common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
        self.uid = common.authenticate(
            cfg["db"], cfg["username"], cfg["password"], {}
        )
        if not self.uid:
            raise Exception(f"Auth failed {name}")

        self.models = xmlrpc.client.ServerProxy(
            f"{cfg['url']}/xmlrpc/2/object"
        )
        logger.info(f"✓ {name} conectado ({common.version()['server_version']})")

    def search_read(self, model, domain, fields, active_test=True):
        ctx = {"active_test": active_test}
        return self.models.execute_kw(
            self.cfg["db"],
            self.uid,
            self.cfg["password"],
            model,
            "search_read",
            [domain],
            {"fields": fields, "context": ctx}
        )

    def search(self, model, domain):
        return self.models.execute_kw(
            self.cfg["db"],
            self.uid,
            self.cfg["password"],
            model,
            "search",
            [domain],
            {"context": {"active_test": False}}
        )

    def write(self, model, ids, values):
        return self.models.execute_kw(
            self.cfg["db"],
            self.uid,
            self.cfg["password"],
            model,
            "write",
            [ids, values],
            {"context": {"active_test": False}}
        )


# ------------------------------------------------------------
# SYNC
# ------------------------------------------------------------
class ArchiveByAbsence:

    def __init__(self):
        self.o16 = Odoo(ODOO_16, "Odoo 16")
        self.o18 = Odoo(ODOO_18, "Odoo 18")

        self.stats = {
            "checked": 0,
            "archived": 0,
            "skipped_no_code": 0,
            "errors": 0,
        }

    def load_active_codes_o16(self):
        """Devuelve set de internal_code activos en Odoo 16"""
        logger.info("Cargando productos ACTIVOS de Odoo 16...")

        templates = self.o16.search_read(
            "product.template",
            [],
            ["internal_code"],
            active_test=True
        )

        codes = {
            (t.get("internal_code") or "").strip()
            for t in templates
            if t.get("internal_code")
        }

        logger.info(f"✓ {len(codes)} internal_code activos en Odoo 16")
        return codes

    def load_active_templates_o18(self):
        logger.info("Cargando productos ACTIVOS de Odoo 18...")

        return self.o18.search_read(
            "product.template",
            [],
            ["id", "internal_code"],
            active_test=True
        )

    def run(self):
        start = datetime.now()

        logger.info("==============================================")
        logger.info(" ARCHIVADO POR AUSENCIA")
        logger.info(" internal_code | Odoo 16 → Odoo 18")
        logger.info("==============================================")

        codes_16 = self.load_active_codes_o16()
        templates_18 = self.load_active_templates_o18()

        for t in templates_18:
            self.stats["checked"] += 1

            code = (t.get("internal_code") or "").strip()
            if not code:
                self.stats["skipped_no_code"] += 1
                continue

            if code in codes_16:
                continue  # existe en 16 → OK

            try:
                tmpl_id = t["id"]

                # 1) archivar template
                self.o18.write(
                    "product.template",
                    [tmpl_id],
                    {"active": False}
                )

                # 2) archivar variantes
                variant_ids = self.o18.search(
                    "product.product",
                    [("product_tmpl_id", "=", tmpl_id)]
                )

                if variant_ids:
                    self.o18.write(
                        "product.product",
                        variant_ids,
                        {"active": False}
                    )

                logger.info(f"📦 ARCHIVADO [{code}]")
                self.stats["archived"] += 1

            except Exception as e:
                logger.error(f"❌ Error archivando [{code}]: {e}")
                self.stats["errors"] += 1

        elapsed = datetime.now() - start

        logger.info("==============================================")
        logger.info(" RESUMEN FINAL")
        logger.info("==============================================")
        logger.info(f"Revisados:          {self.stats['checked']}")
        logger.info(f"Archivados:         {self.stats['archived']}")
        logger.info(f"Sin internal_code:  {self.stats['skipped_no_code']}")
        logger.info(f"Errores:            {self.stats['errors']}")
        logger.info(f"Tiempo:             {elapsed}")
        logger.info("==============================================")


# ------------------------------------------------------------
if __name__ == "__main__":
    ArchiveByAbsence().run()
