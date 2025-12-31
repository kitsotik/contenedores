from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_oficial = fields.Boolean(
        string="Enable Oficial Dollar",
        config_parameter="dolares_arg.enable_oficial",
        help="Fetch and update the official dollar rate.",
    )
    enable_blue = fields.Boolean(
        string="Enable Blue Dollar",
        config_parameter="dolares_arg.enable_blue",
        help="Fetch and update the blue dollar rate (average of buy/sell).",
    )
    enable_bolsa = fields.Boolean(
        string="Enable Bolsa Dollar",
        config_parameter="dolares_arg.enable_bolsa",
        help="Fetch and update the bolsa (MEP) dollar rate.",
    )
    enable_contadoconliqui = fields.Boolean(
        string="Enable Contado con Liqui Dollar",
        config_parameter="dolares_arg.enable_contadoconliqui",
        help="Fetch and update the CCL dollar rate.",
    )
    enable_mayorista = fields.Boolean(
        string="Enable Mayorista Dollar",
        config_parameter="dolares_arg.enable_mayorista",
        help="Fetch and update the mayorista dollar rate.",
    )
    enable_cripto = fields.Boolean(
        string="Enable Cripto Dollar",
        config_parameter="dolares_arg.enable_cripto",
        help="Fetch and update the crypto dollar rate.",
    )
    enable_tarjeta = fields.Boolean(
        string="Enable Tarjeta Dollar",
        config_parameter="dolares_arg.enable_tarjeta",
        help="Fetch and update the tarjeta dollar rate.",
    )
    enable_bna = fields.Boolean(
        string="Enable BNA Dollar",
        config_parameter="dolares_arg.enable_bna",
        help="Fetch and update the BNA dollar rate via scraping.",
    )
