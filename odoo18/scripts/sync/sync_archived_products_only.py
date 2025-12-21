#!/usr/bin/env python3

import xmlrpc.client
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ODOO_16, ODOO_18

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("sync_archived_products.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


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

    def search_read(self, model, domain, fields):
        return self.models.execute_kw(
            self.cfg["db"],
            self.uid,
            self.cfg["password"],
            model,
            "search_read",
            [domain],
            {"fields": fields, "context": {"active_test": False}}
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


def run():
    o16 = Odoo(ODOO_16, "Odoo 16")
    o18 = Odoo(ODOO_18, "Odoo 18")

    logger.info("=" * 60)
    logger.info("SINCRONIZACIÓN DE ARCHIVADOS (Odoo 16 → Odoo 18)")
    logger.info("=" * 60)

    mappings = o18.search_read(
        "ir.model.data",
        [
            ("module", "=", "sync_script"),
            ("model", "=", "product.product"),
            ("name", "like", "sync_product_product_%"),
        ],
        ["name", "res_id"]
    )

    logger.info(f"🔗 Productos sincronizados encontrados: {len(mappings)}")

    checked = 0
    archived = 0
    skipped_missing = 0

    for m in mappings:
        checked += 1

        try:
            source_id = int(m["name"].replace("sync_product_product_", ""))
        except Exception:
            continue

        # Estado en Odoo 16
        src = o16.search_read(
            "product.product",
            [("id", "=", source_id)],
            ["active"]
        )

        if not src or src[0]["active"] is not False:
            continue

        product_18_id = m["res_id"]

        # 🔐 VERIFICAR EXISTENCIA EN ODOO 18
        exists = o18.search_read(
            "product.product",
            [("id", "=", product_18_id)],
            ["id"]
        )

        if not exists:
            skipped_missing += 1
            continue

        # Archivar producto
        o18.write(
            "product.product",
            [product_18_id],
            {"active": False}
        )

        # Archivar template
        tmpl = o18.search_read(
            "product.product",
            [("id", "=", product_18_id)],
            ["product_tmpl_id"]
        )

        if tmpl and tmpl[0].get("product_tmpl_id"):
            o18.write(
                "product.template",
                [tmpl[0]["product_tmpl_id"][0]],
                {"active": False}
            )

        archived += 1

    logger.info("=" * 60)
    logger.info(f"Revisados:                 {checked}")
    logger.info(f"Archivados en Odoo 18:     {archived}")
    logger.info(f"IDs inexistentes en Odoo 18: {skipped_missing}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
