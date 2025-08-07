# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

import requests

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

from ..constants.atm_averba import (
    ATM_AVERBA_HOMOLOGATION_URL,
    ATM_AVERBA_PRODUCTION_URL,
)


class MockResponse:
    def __init__(self, json_data, status_code=200, ok=True, http_error=False):
        self._json_data = json_data
        self.status_code = status_code
        self.ok = ok
        self.http_error = http_error

    def json(self):
        if self.http_error:
            raise requests.HTTPError("Mocked HTTP Error")
        return self._json_data

    def raise_for_status(self):
        if self.http_error or not self.ok or self.status_code >= 400:
            raise requests.HTTPError("Mocked HTTP Error")


def mocked_atm_token_success(*args, **kwargs):
    return MockResponse({"Bearer": "ATM_TOKEN_123"})


def mocked_atm_token_failure(*args, **kwargs):
    return MockResponse({"mensagem": "Erro ao autenticar"}, status_code=400, ok=False)


def mocked_atm_token_http_error(*args, **kwargs):
    return MockResponse({}, status_code=500, ok=False, http_error=True)


class TestAtmAverba(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.atm_user = "ws2"
        cls.atm_pwd = "base123"
        cls.company.atm_averba_user = cls.atm_user
        cls.company.atm_averba_user_password = cls.atm_pwd
        cls.company.atm_code = "12345678"
        cls.company.atm_averba_environment = "2"

    def test_get_atm_averba_environment(self):
        env = self.company.get_atm_averba_environment()
        self.assertEqual(env["url"], ATM_AVERBA_HOMOLOGATION_URL)
        self.assertEqual(env["usuario"], self.atm_user)
        self.assertEqual(env["senha"], self.atm_pwd)
        self.assertEqual(env["codigoatm"], "12345678")

        self.company.atm_averba_environment = "1"
        env = self.company.get_atm_averba_environment()
        self.assertEqual(env["url"], ATM_AVERBA_PRODUCTION_URL)

    @mock.patch("requests.post", side_effect=mocked_atm_token_success)
    def test_generate_atm_token_success(self, mock_post):
        token = self.company.generate_atm_token()
        self.assertEqual(token, "ATM_TOKEN_123")
        self.assertEqual(self.company.atm_token, "ATM_TOKEN_123")
        self.assertIsNotNone(self.company.atm_token_expiration)

    @mock.patch("requests.post", side_effect=mocked_atm_token_failure)
    def test_generate_atm_token_api_error(self, mock_post):
        with self.assertRaises(UserError) as error:
            self.company.generate_atm_token()
        self.assertIn(
            "Erro na conexão com AT&M: Mocked HTTP Error", str(error.exception)
        )

    @mock.patch("requests.post", side_effect=mocked_atm_token_http_error)
    def test_generate_atm_token_http_error(self, mock_post):
        with self.assertRaises(UserError) as error:
            self.company.generate_atm_token()
        self.assertIn("Erro na conexão com AT&M", str(error.exception))
