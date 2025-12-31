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
            raise ValidationError('No se puede determinar el dolar BNA #1')
        
        value = tds[1].text.strip()
        value = value.replace(',', '.')
        value = float(value) + 20  # Ajustar según necesidad
        
        currency_id = self.search([('name', '=', 'USD')], limit=1)
        if not currency_id:
            raise UserError('No se encontró la moneda USD')
        
        vals = {
            'name': fields.Date.today(),
            'currency_id': currency_id.id,
            'rate': 1 / value
        }
        
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency_id.id),
            ('name', '=', fields.Date.today())
        ], limit=1)
        
        if rate:
            rate.write({'rate': 1 / value})
        else:
            self.env['res.currency.rate'].create(vals)
            
    except Exception as e:
        # Log el error para debugging
        _logger.error(f'Error actualizando tasa de cambio BNA: {str(e)}')
        raise