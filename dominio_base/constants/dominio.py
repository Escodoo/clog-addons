# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import config

DOMINIO_ENVIRONMENTS = [("1", "Produção"), ("2", "Homologação")]
DOMINIO_ENVIRONMENT_DEFAULT = "2"


def get_dominio_api_url(env):
    xml_url = (
        os.environ.get("DOMINIO_XML_URL")
        or config.get("dominio_xml_url")
        or env["ir.config_parameter"].sudo().get_param("dominio_xml_url")
    )

    token_url = (
        os.environ.get("DOMINIO_TOKEN_URL")
        or config.get("dominio_token_url")
        or env["ir.config_parameter"].sudo().get_param("dominio_token_url")
    )

    key_integration_url = (
        os.environ.get("DOMINIO_KEY_INTEGRATION_URL")
        or config.get("dominio_key_integration_url")
        or env["ir.config_parameter"].sudo().get_param("dominio_key_integration_url")
    )

    check_customer_url = (
        os.environ.get("DOMINIO_CHECK_CUSTOMER_URL")
        or config.get("dominio_check_customer_url")
        or env["ir.config_parameter"].sudo().get_param("dominio_check_customer_url")
    )

    if not all([xml_url, token_url, key_integration_url, check_customer_url]):
        raise UserError(
            _(
                "Dominio API URLs are not properly configured.\n\n"
                "Please set the URLs using one of these methods:\n\n"
            )
        )

    return {
        "xml_url": xml_url,
        "token_url": token_url,
        "key_integration_url": key_integration_url,
        "check_customer_url": check_customer_url,
    }
