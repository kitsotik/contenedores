from odoo import api, models,fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_show_price = fields.Boolean(related="pos_config_id.show_price", readonly=False)

