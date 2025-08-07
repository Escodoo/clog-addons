# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..constants.atm_averba import (
    ATM_AVERBA_HOMOLOGATION_URL,
    ATM_AVERBA_PRODUCTION_URL,
)


class ResCompany(models.Model):

    _inherit = "res.company"

    atm_averba_environment = fields.Selection(
        selection=[("1", "Production"), ("2", "Homologation")],
        string="Environment",
        default="2",
    )
    atm_averba_user = fields.Char(string="User")
    atm_averba_user_password = fields.Char(string="User Password")
    atm_code = fields.Char()
    atm_token = fields.Char()
    atm_token_expiration = fields.Datetime()

    def get_atm_averba_environment(self):
        self.ensure_one()
        return {
            "url": ATM_AVERBA_PRODUCTION_URL
            if self.atm_averba_environment == "1"
            else ATM_AVERBA_HOMOLOGATION_URL,
            "usuario": self.atm_averba_user,
            "senha": self.atm_averba_user_password,
            "codigoatm": self.atm_code,
        }

    def generate_atm_token(self):
        self.ensure_one()
        config = self.get_atm_averba_environment()

        url = "https://webserver.averba.com.br/rest/Auth"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "usuario": config["usuario"],
            "senha": config["senha"],
            "codigoatm": config["codigoatm"],
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as e:
            raise UserError(_("Erro na conexão com AT&M: %s") % str(e))
        except Exception as e:
            raise UserError(_("Erro inesperado: %s") % str(e))

        token = result.get("Bearer")
        if not token:
            raise UserError(_("Token não retornado pela AT&M: %s") % result)

        self.atm_token = token
        self.atm_token_expiration = datetime.now() + timedelta(hours=1)
        return token
