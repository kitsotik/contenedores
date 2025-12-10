from odoo import models
import requests
import logging
from datetime import date
from bs4 import BeautifulSoup
from odoo.exceptions import UserError
import unicodedata  # Para normalizar acentos


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    _logger = logging.getLogger(__name__)

    def fetch_arg_dollars(self, company_id=None):
        """Fetch and update Argentine dollar rates based on configuration."""
        today = date.today()
        self._logger.info(
            f"Fetch Start: Starting fetch_arg_dollars for {today} (company_id: {company_id or 'Global'})"
        )
        config = self.env["ir.config_parameter"].sudo()

        # Mapping of 'casa' to currency codes
        casa_to_currency = {
            "oficial": "USO",
            "blue": "USB",
            "bolsa": "USL",
            "contadoconliqui": "USC",
            "mayorista": "USM",
            "cripto": "USCR",
            "tarjeta": "UST",
        }

        # Fetch all rates from API if any API-based is enabled
        api_enabled = any(
            config.get_param(f"dolares_arg.enable_{casa}", "False") == "True"
            for casa in casa_to_currency
        )
        rates_data = {}
        if api_enabled:
            url = "https://dolarapi.com/v1/dolares"
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                rates_data = {item["casa"]: item for item in response.json()}
            except Exception as e:
                self._logger.error(f"API Fetch Error: {str(e)}")
                return  # Stop if API fails, but continue for BNA if enabled

        # Process each enabled API rate
        for casa, code in casa_to_currency.items():
            if config.get_param(f"dolares_arg.enable_{casa}", "False") == "True":
                data = rates_data.get(casa)
                if not data:
                    self._logger.warning(
                        f"{casa.capitalize()} Data Missing: No data found in API response"
                    )
                    continue
                try:
                    buy = float(data.get("compra", 0))
                    sell = float(data.get("venta", 0))
                    if sell == 0:
                        raise ValueError("Invalid sell value")
                    if casa == "blue":
                        if buy == 0:
                            raise ValueError("Invalid buy value for blue")
                        rate_value = (buy + sell) / 2
                    else:
                        rate_value = sell
                    self._logger.info(
                        f"{casa.capitalize()} Rate: Calculated rate_value: {rate_value}"
                    )
                    self._update_rate(
                        code, today, 1.0 / rate_value, company_id=company_id
                    )
                except Exception as e:
                    self._logger.error(
                        f"{casa.capitalize()} Processing Error: {str(e)}"
                    )

        # Process BNA if enabled
        if config.get_param("dolares_arg.enable_bna", "False") == "True":
            self._logger.info(f"BNA Process Start: Starting BNA fetch for {today}")
            try:
                bna_url = "https://www.bna.com.ar/Personas"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
                }
                self._logger.info(f"BNA Request: Sending request to {bna_url}")
                page = requests.get(bna_url, timeout=10, headers=headers)
                self._logger.info(
                    f"BNA Response: Received response with status {page.status_code}"
                )
                soup = BeautifulSoup(page.content, "html.parser")
                self._logger.info(
                    "BNA Parsing: Soup created, searching for billetes table"
                )
                results = soup.find(id="billetes")
                if not results:
                    self._logger.error("BNA Error: BNA table not found")
                    raise UserError("BNA table not found")
                found = False
                for tr in results.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 3:
                        row_name = (
                            unicodedata.normalize("NFKD", tds[0].text.strip())
                            .encode("ascii", "ignore")
                            .decode("utf-8")
                            .lower()
                        )
                        self._logger.debug(
                            f"BNA Row Check: Found row with {len(tds)} columns: {row_name}"
                        )
                        if "dolar u.s.a" in row_name:
                            self._logger.info("BNA Match: Found Dolar U.S.A row")
                            value_str = tds[2].text.strip()  # Venta
                            self._logger.info(
                                f"BNA Value: Raw value string: {value_str}"
                            )
                            value = float(value_str.replace(",", "."))
                            if value == 0:
                                self._logger.error(
                                    "BNA Error: Invalid BNA value (zero)"
                                )
                                raise ValueError("Invalid BNA value")
                            self._logger.info(
                                f"BNA Rate: Calculated rate: {1.0 / value}"
                            )
                            self._update_rate(
                                "USN", today, 1.0 / value, company_id=company_id
                            )
                            found = True
                            self._logger.info(
                                f"BNA Success: Updated USN rate with value {value}"
                            )
                            break
                if not found:
                    self._logger.error(
                        "BNA Error: Dolar U.S.A row not found in BNA table"
                    )
                    raise UserError("Dolar U.S.A row not found in BNA table")
            except Exception as e:
                self._logger.error(f"BNA Exception: {str(e)}")

    def _update_rate(self, currency_code, date, rate, company_id=None):
        """Update or create currency rate for the given code and date."""
        self._logger.info(
            f"Update Rate Start: Processing {currency_code} with rate {rate}"
        )
        currency = self.env["res.currency"].search(
            [("name", "=", currency_code)], limit=1
        )
        # Mapping of currency codes to full names
        currency_full_names = {
            "USO": "Dolar Oficial",
            "USB": "United States Dollar Blue",
            "USL": "Dolar Bolsa (MEP)",
            "USC": "Dolar Contado con Liqui (CCL)",
            "USM": "Dolar Mayorista",
            "USCR": "Dolar Cripto",
            "UST": "Dolar Tarjeta",
            "USN": "Dolar Banco Nación (BNA)",
        }
        if not currency:
            try:
                currency = self.env["res.currency"].create(
                    {
                        "name": currency_code,
                        "symbol": currency_code,
                        "full_name": currency_full_names.get(
                            currency_code, currency_code
                        ),
                        "active": True,
                    }
                )
                self._logger.info(
                    f"Currency Created: Created {currency_code} with full_name {currency_full_names.get(currency_code)}"
                )
            except Exception as e:
                self._logger.error(
                    f"Currency Create Error: Failed to create {currency_code}: {str(e)}"
                )
                return  # Salir si falla el create, sin intentar rate
        domain = [("currency_id", "=", currency.id), ("name", "=", date)]
        if company_id:
            domain.append(("company_id", "=", company_id))
        else:
            domain.append(("company_id", "=", False))
        existing_rate = self.search(domain, limit=1)
        vals = {
            "currency_id": currency.id,
            "name": date,
            "rate": rate,
            "company_id": company_id or False,
        }
        if existing_rate:
            existing_rate.write(vals)
            self._logger.info(
                f"Rate Updated: Updated {currency_code} rate to {rate} for {date}"
            )
        else:
            self.create(vals)
            self._logger.info(
                f"Rate Created: Created new rate for {currency_code} with value {rate} on {date}"
            )
