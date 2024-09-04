# Copyright 2024 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..constants.ndd_averba import (
    NDD_AVERBA_HOMOLOGATION_URL,
    NDD_AVERBA_PRODUCTION_URL,
)


class ResCompany(models.Model):

    _inherit = "res.company"

    ndd_averba_environment = fields.Selection(
        selection=[("1", "Production"), ("2", "Homologation")],
        string="Environment",
        default="2",
    )
    ndd_averba_production_user_email = fields.Char(string="Production User E-mail")
    ndd_averba_production_user_password = fields.Char(string="Production User Password")
    ndd_averba_homologation_user_email = fields.Char(string="Homologation User E-mail")
    ndd_averba_homologation_user_password = fields.Char(
        string="Homologation User Password"
    )

    def get_ndd_averba_environment(self):
        self.ensure_one()
        if self.ndd_averba_environment == "1":
            return {
                "url": NDD_AVERBA_PRODUCTION_URL,
                "email": self.ndd_averba_production_user_email,
                "password": self.ndd_averba_production_user_password,
            }
        else:
            return {
                "url": NDD_AVERBA_HOMOLOGATION_URL,
                "email": self.ndd_averba_homologation_user_email,
                "password": self.ndd_averba_homologation_user_password,
            }

    def _generate_ndd_averba_token(self):
        try:
            environment = self.get_ndd_averba_environment()
            url = environment["url"] + "/auth/login"

            payload = {
                "email": environment["email"],
                "senha": environment["password"],
            }
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }
            response = requests.post(url, headers=headers, json=payload)
            content = response.json()
            if response.ok:
                return content
            else:
                raise UserError(_(content["mensagem"]))

        except requests.HTTPError as e:
            raise UserError(
                _("Error communicating with NDD Averba service: %s") % e
            ) from e

    def _check_ndd_averba_user(self):
        try:
            environment = self.get_ndd_averba_environment()
            url = environment["url"] + "/user"

            token_data = self._generate_ndd_averba_token()
            access_token = token_data.get("token_acesso")

            headers = {
                "Authorization": "Bearer " + access_token,
            }

            response = requests.get(url, headers=headers)
            content = response.json()
            if response.ok:
                return content
            else:
                raise UserError(_(content["mensagem"]))

        except requests.HTTPError as e:
            raise UserError(
                _("Error while verifying user authorization: %s") % e
            ) from e
