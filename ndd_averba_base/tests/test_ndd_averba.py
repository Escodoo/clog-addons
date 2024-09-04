# Copyright 2024 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

from ..constants.ndd_averba import (
    NDD_AVERBA_HOMOLOGATION_URL,
    NDD_AVERBA_PRODUCTION_URL,
)


class MockResponse:
    def __init__(self, json_data, status_code, ok):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = ok

    def ok(self):
        return self.ok

    def json(self):
        return self.json_data


def mocked_ndd_averba_token(*args, **kwargs):
    return MockResponse({"token_acesso": "ABC"}, 200, True)


def mocked_ndd_averba_token_error(*args, **kwargs):
    return MockResponse({"mensagem": "error"}, 400, False)


def mocked_ndd_averba_user(*args, **kwargs):
    return MockResponse({"mensagem": "logged"}, 200, True)


def mocked_ndd_averba_user_error(*args, **kwargs):
    return MockResponse({"mensagem": "error"}, 400, False)


class TestNddAverba(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestNddAverba, cls).setUpClass()
        cls.company = cls.env.company
        cls.user_email = "user@example.com"
        cls.user_pwd = "123456"
        cls.user_prod_email = "admin@example.com"
        cls.user_prod_pwd = "Admin123456"

    def test_get_ndd_averba_environment(self):
        self.company.ndd_averba_environment = "2"
        self.company.ndd_averba_homologation_user_email = self.user_email
        self.company.ndd_averba_homologation_user_password = self.user_pwd

        environment = self.company.get_ndd_averba_environment()
        self.assertEqual(environment["url"], NDD_AVERBA_HOMOLOGATION_URL)
        self.assertEqual(environment["email"], self.user_email)
        self.assertEqual(environment["password"], self.user_pwd)

        self.company.ndd_averba_environment = "1"
        self.company.ndd_averba_production_user_email = self.user_prod_email
        self.company.ndd_averba_production_user_password = self.user_prod_pwd

        environment = self.company.get_ndd_averba_environment()
        self.assertEqual(environment["url"], NDD_AVERBA_PRODUCTION_URL)
        self.assertEqual(environment["email"], self.user_prod_email)
        self.assertEqual(environment["password"], self.user_prod_pwd)

    @mock.patch("requests.post", side_effect=mocked_ndd_averba_token)
    def test_generate_ndd_averba_token(self, mock_post):
        self.company.ndd_averba_homologation_user_email = self.user_email
        self.company.ndd_averba_homologation_user_password = self.user_pwd
        response = self.company._generate_ndd_averba_token()
        self.assertEqual(response["token_acesso"], "ABC")

    @mock.patch("requests.post", side_effect=mocked_ndd_averba_token_error)
    def test_generate_ndd_averba_token_error(self, mock_post):
        self.company.ndd_averba_homologation_user_email = self.user_email
        self.company.ndd_averba_homologation_user_password = self.user_pwd
        with self.assertRaises(UserError):
            self.company._generate_ndd_averba_token()

    @mock.patch("requests.post", side_effect=mocked_ndd_averba_token)
    @mock.patch("requests.get", side_effect=mocked_ndd_averba_user)
    def test_check_ndd_averba_user(self, mock_post, mock_get):
        self.company.ndd_averba_homologation_user_email = self.user_email
        self.company.ndd_averba_homologation_user_password = self.user_pwd
        response = self.company._check_ndd_averba_user()
        self.assertEqual(response["mensagem"], "logged")

    @mock.patch("requests.post", side_effect=mocked_ndd_averba_token)
    @mock.patch("requests.get", side_effect=mocked_ndd_averba_user_error)
    def test_check_ndd_averba_user_error(self, mock_post, mock_get):
        self.company.ndd_averba_homologation_user_email = self.user_email
        self.company.ndd_averba_homologation_user_password = self.user_pwd
        with self.assertRaises(UserError):
            self.company._check_ndd_averba_user()
