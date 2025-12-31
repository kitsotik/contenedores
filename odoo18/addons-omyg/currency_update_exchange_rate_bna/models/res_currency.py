# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from bs4 import BeautifulSoup
import requests

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def update_dolarbna(self):
        dolarbna_url = self.env['ir.config_parameter'].get_param('dolar_bna', 'https://www.bna.com.ar/Personas')
        if not dolarbna_url:
            raise UserError('No está presente URL de BNA')
        page = requests.get(dolarbna_url)
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find(id="billetes")
        tds = results.find_all("td", class_=False)
        if len(tds) < 2:
            raise ValidationError('No se puede determinar el dolar BNA #1')
        value = tds[1].text
        value = value.replace('<td>', '')
        value = value.replace('</td>', '')
        value = float(value.replace(',', '.')) + 20  # Sumar 2 unidades al valor obtenido
        currency_id = self.search([('name', '=', 'USD')])
        if currency_id:
            vals = {
                'name': str(datetime.now())[:10],
                'currency_id': currency_id.id,
                'rate': 1 / value
            }
            rate = self.env['res.currency.rate'].search([('currency_id', '=', currency_id.id), ('name', '=', str(datetime.now())[:10])])
            if rate:
                rate.write({'rate': 1 / value})  # Actualizar la tasa existente
            else:
                self.env['res.currency.rate'].create(vals)  # Crear una nueva tasa
