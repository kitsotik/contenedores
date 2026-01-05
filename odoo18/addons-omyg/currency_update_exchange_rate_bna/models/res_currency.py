import logging
import requests
from bs4 import BeautifulSoup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def update_dolarbna(self):
        try:
            dolarbna_url = self.env['ir.config_parameter'].sudo().get_param(
                'dolar_bna', 'https://www.bna.com.ar/Personas'
            )
            if not dolarbna_url:
                raise UserError('No está presente URL de BNA')

            page = requests.get(dolarbna_url, timeout=10)
            page.raise_for_status()

            soup = BeautifulSoup(page.content, "html.parser")
            results = soup.find(id="billetes")

            if not results:
                raise ValidationError('No se encontró la tabla de billetes en BNA')

            tds = results.find_all("td", class_=False)
            if len(tds) < 2:
                raise ValidationError('No se puede determinar el dolar BNA')

            value = tds[1].text.strip().replace(',', '.')
            value = float(value) + 20  # ajuste manual

            currency = self.search([('name', '=', 'USD')], limit=1)
            if not currency:
                raise UserError('No se encontró la moneda USD')

            today = fields.Date.today()
            rate_value = 1 / value

            rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', currency.id),
                ('name', '=', today)
            ], limit=1)

            if rate:
                rate.write({'rate': rate_value})
            else:
                self.env['res.currency.rate'].create({
                    'name': today,
                    'currency_id': currency.id,
                    'rate': rate_value
                })

        except Exception as e:
            _logger.exception('Error actualizando tasa de cambio BNA')
            raise
