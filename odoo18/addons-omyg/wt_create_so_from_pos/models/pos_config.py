# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    create_so = fields.Boolean("Create Sales Order", help="Allow to create Sales Order in POS", default=True)