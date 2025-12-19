#!/usr/bin/env python3
"""
Sincronización REAL de estado de productos
Replica exactamente lo que se ve en Odoo 16

Clave: internal_code (product.template)
Sincroniza:
- product.template.active
- product.product.active (variantes)
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
        logging.FileHandler("sync_product_archive.log"),
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
        self.uid = common.authenticate(cfg["db"], cfg["username"], cfg["password"], {})
        if not self.uid:
            raise Exception(f"Auth failed {name}")

        self.models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
        logger.info(f"✓ {name} conectado ({common.version()['server_version']})")

    def search_read(self, model, domain, fields):
        return self.models.execute_kw(
            self.cfg["db"], self.uid, self.cfg["password"],
            model, "search_read", [domain],
            {"fields": fields, "context": {"active_test": False}}
        )

    def search(self, model, domain):
        return self.models.execute_kw(
            self.cfg["db"], self.uid, self.cfg["password"],
            model, "search", [domain],
            {"context": {"active_test": False}}
        )

    def write(self, model, ids, values):
        return self.models.execute_kw(
            self.cfg["db"], self.uid, self.cfg["password"],
            model, "write", [ids, values],
            {"context": {"active_test": False}}
        )


# ------------------------------------------------------------
# SYNC
# ------------------------------------------------------------
class Sync:

    def __init__(self):
        self.o16 = Odoo(ODOO_16, "Odoo 16")
        self.o18 = Odoo(ODOO_18, "Odoo 18")

        self.stats = {
            "matched": 0,
            "tmpl_changed": 0,
            "variants_changed": 0,
            "errors": 0,
        }

    def load_templates(self, odoo):
        tpls = odoo.search_read(
            "product.template",
            [],
            ["id", "internal_code", "active"]
        )

        res = {}
        for t in tpls:
            code = (t.get("internal_code") or "").strip()
            if code:
                res[code] = t
        return res

    def load_variants(self, odoo, tmpl_id):
        return odoo.search_read(
            "product.product",
            [("product_tmpl_id", "=", tmpl_id)],
            ["id", "active"]
        )

    def run(self):
        start = datetime.now()

        t16 = self.load_templates(self.o16)
        t18 = self.load_templates(self.o18)

        for code, tpl18 in t18.items():
            if code not in t16:
                continue

            self.stats["matched"] += 1
            tpl16 = t16[code]

            # --- TEMPLATE ---
            if tpl16["active"] != tpl18["active"]:
                self.o18.write(
                    "product.template",
                    [tpl18["id"]],
                    {"active": tpl16["active"]}
                )
                self.stats["tmpl_changed"] += 1
                logger.info(
                    f"TEMPLATE {'ACTIVADO' if tpl16['active'] else 'ARCHIVADO'} [{code}]"
                )

            # --- VARIANTES ---
            v16 = self.load_variants(self.o16, tpl16["id"])
            v18 = self.load_variants(self.o18, tpl18["id"])

            map16 = {v["id"]: v["active"] for v in v16}

            for v in v18:
                if v["active"] != map16.get(v["id"], v["active"]):
                    self.o18.write(
                        "product.product",
                        [v["id"]],
                        {"active": map16.get(v["id"], v["active"])}
                    )
                    self.stats["variants_changed"] += 1

        elapsed = datetime.now() - start

        logger.info("==============================================")
        logger.info(" RESUMEN FINAL")
        logger.info("==============================================")
        logger.info(f"Coincidentes:        {self.stats['matched']}")
        logger.info(f"Templates cambiados:{self.stats['tmpl_changed']}")
        logger.info(f"Variantes cambiadas:{self.stats['variants_changed']}")
        logger.info(f"Errores:            {self.stats['errors']}")
        logger.info(f"Tiempo:             {elapsed}")
        logger.info("==============================================")


# ------------------------------------------------------------
if __name__ == "__main__":
    Sync().run()
