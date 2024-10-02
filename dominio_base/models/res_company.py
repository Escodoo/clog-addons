# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..constants.dominio import (
    DOMINIO_ENVIRONMENT_DEFAULT,
    DOMINIO_ENVIRONMENTS,
    get_dominio_api_url,
)


class ResCompany(models.Model):

    _inherit = "res.company"

    dominio_environment = fields.Selection(
        selection=DOMINIO_ENVIRONMENTS,
        string="Environment",
        default=DOMINIO_ENVIRONMENT_DEFAULT,
    )
    dominio_client_token = fields.Char(
        string="Client ID Token",
    )
    dominio_secret_token = fields.Char(
        string="Client Secret Token",
    )
    dominio_production_integration_key = fields.Char(
        string="Integration Production Token"
    )
    dominio_homologation_integration_key = fields.Char(
        string="Integration Homologation Token"
    )
    dominio_cookie = fields.Char(
        string="Cookie",
    )
    dominio_audience = fields.Char(
        string="Audience",
    )
    dominio_box_e = fields.Selection(
        selection=[("true", "Yes"), ("false", "No")],
        string="Contract BOX-e",
        default="false",
        required=True,
    )

    def get_dominio_environment(self):
        """
        Retrieve the appropriate Dominio token based on the current environment setting.
        Decide between the production and homologation (test) environment tokens by
        examining the 'dominio_environment' field of the record.

        Precondition:
        - Call this method on a single record only. The method uses ensure_one to
        enforce this rule.

        Returns:
        - str: The Dominio token. Return the production token if 'dominio_environment'
        is set to "1"; otherwise, return the homologation token.

        Raises:
        - ValueError: If the method is called on a recordset containing more than one
        record.
        """
        self.ensure_one()
        return (
            self.dominio_production_integration_key
            if self.dominio_environment == "1"
            else self.dominio_homologation_integration_key
        )

    def _generate_dominio_token(self):
        """
        Generate OAuth2 token for Dominio service.

        Returns:
            requests.Response: Response object containing the token.

        Raises:
            UserError: If an error occurs during token generation.
        """
        try:
            api_url = get_dominio_api_url(self.env)
            url = api_url.get("token_url")

            payload = {
                "grant_type": "client_credentials",
                "client_id": self.dominio_client_token,
                "client_secret": self.dominio_secret_token,
                "audience": self.dominio_audience,
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": self.dominio_cookie,
            }

            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()
            return response

        except requests.HTTPError as e:
            raise UserError(
                _("Error communicating with Dominio service: %s") % e
            ) from e

    def _generate_key_integration(self):
        """
        Generate integration key for Dominio activation.

        Returns:
            str: Integration key retrieved from the response.

        Raises:
            UserError: If an error occurs during integration key generation.
        """
        try:
            api_url = get_dominio_api_url(self.env)
            url = api_url.get("key_integration_url")

            x_integration_key = self.get_dominio_environment()
            token_response = self._generate_dominio_token()
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "x-integration-key": x_integration_key,
            }

            response = requests.post(url, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            return {
                "integrationKey": response_data.get("integrationKey"),
                "access_token": access_token,
            }

        except requests.HTTPError as e:
            raise UserError(
                _("Error while generating integration key in Dominio: %s") % e
            ) from e

    def _check_dominio_customer(self):
        """
        Check customer authorization status in Dominio service.

        Returns:
            requests.Response: Response object containing the authorization status.

        Raises:
            UserError: If an error occurs while verifying customer authorization.
        """
        try:
            api_url = get_dominio_api_url(self.env)
            url = api_url.get("check_customer_url")

            x_integration_key = self.get_dominio_environment()
            token_response = self._generate_dominio_token()
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            headers = {
                "Authorization": "Bearer " + access_token,
                "x-integration-key": x_integration_key,
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response

        except requests.HTTPError as e:
            raise UserError(
                _("Error while verifying customer authorization: %s") % e
            ) from e
