# Copyright 2025 - TODAY, Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest import mock

import requests

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


class MockResponse:
    def __init__(self, json_data, status_code, ok, text="", http_error=False):
        self._json = json_data
        self.status_code = status_code
        self.ok = ok
        self._text = text
        self.http_error = http_error

    def json(self):
        if self.http_error:
            raise requests.HTTPError("Mocked HTTP Error")
        return self._json

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"Mocked error with status {self.status_code}")

    @property
    def text(self):
        return self._text


def mocked_token_ok(*args, **kwargs):
    return MockResponse({"token": "ABC"}, 200, True)


def mocked_mdfe_close_ok(*args, **kwargs):
    return MockResponse(
        {
            "Numero": "3",
            "Serie": "1",
            "Filial": "001",
            "Declarado": [
                {
                    "dhChancela": "2025-09-15T06:47:27",
                    "Protocolo": "PROTO-123456",
                }
            ],
            "Infos": {
                "Info": [
                    {"Codigo": "001", "Descricao": "Documento ja encerrado"},
                ]
            },
        },
        200,
        True,
    )


def mocked_mdfe_close_http_400(*args, **kwargs):
    return MockResponse(
        {
            "Numero": "3",
            "Serie": "1",
            "Filial": "001",
            "Erros": {
                "Erro": [
                    {
                        "Codigo": "912",
                        "Descricao": "XML invalido para utilizacao neste webserver",
                    }
                ]
            },
        },
        400,
        False,
        text='{"retorno":{"Erros":{"Erro":[{"Codigo":"912","Descricao":"XML invalido"}]}}}',
    )


def mocked_http_error(*args, **kwargs):
    return MockResponse({}, 500, False, "Internal error", http_error=False)


class TestAtmAverbaMdfeClose(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.company.atm_averba_environment = "2"
        cls.company.atm_averba_user = "user@example.com"
        cls.company.atm_averba_user_password = "123456"
        cls.fiscal_document = cls.env.ref("l10n_br_fiscal.demo_nfe_other_state")
        cls.fiscal_document.document_type_id = cls.env.ref(
            "l10n_br_fiscal.document_58"
        ).id
        cls.event_close = cls.env["l10n_br_fiscal.event"].create(
            {
                "type": "15",
                "company_id": cls.company.id,
                "document_id": cls.fiscal_document.id,
                "document_type_id": cls.fiscal_document.document_type_id.id,
                "justification": "Encerrar MDF-e para testes unitários",
                "protocol_number": "XYZ",
                "document_serie_id": 1,
                "document_number": "3",
                "file_request_id": cls.env.ref("l10n_br_fiscal.dummy_file_1").id,
                "file_response_id": cls.env.ref("l10n_br_fiscal.dummy_file_1").id,
            }
        )

    @mock.patch(
        "requests.post",
        side_effect=[mocked_token_ok(), mocked_mdfe_close_ok()],
    )
    @mock.patch(
        "odoo.addons.atm_averba_mdfe.models.document.Document.build_proc_evento_mdfe_v3",
        return_value=b"<procEventoMDFe/>",
    )
    def test_mdfe_close_success(self, mock_build_proc, mock_post):
        self.fiscal_document.mdfe_close()
        evt = self.env["atm.averba.event"].search(
            [
                ("document_id", "=", self.fiscal_document.id),
                ("action_type", "=", "close"),
            ],
            limit=1,
            order="id desc",
        )
        self.assertTrue(evt, "Evento de averbação não foi criado.")
        self.assertEqual(evt.endorsement_state, "endorsed")
        self.assertEqual(evt.protocol_number, "PROTO-123456")
        self.assertEqual(evt.endorsement_message, "Documento ja encerrado")
        self.assertEqual(
            fields.Datetime.to_string(evt.date),
            fields.Datetime.to_string(datetime(2025, 9, 15, 6, 47, 27)),
        )
        self.fiscal_document._compute_atm_averba_event_ids()
        self.fiscal_document._compute_atm_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.atm_averba_endorsement_state, "endorsed")

    @mock.patch(
        "requests.post",
        side_effect=[mocked_token_ok(), mocked_mdfe_close_http_400()],
    )
    @mock.patch(
        "odoo.addons.atm_averba_mdfe.models.document.Document.build_proc_evento_mdfe_v3",
        return_value=b"<procEventoMDFe/>",
    )
    def test_mdfe_close_http_400(self, mock_build_proc, mock_post):
        with self.assertRaises(UserError) as err:
            self.fiscal_document.mdfe_close()

        msg = str(err.exception)
        self.assertIn("Erro AT&M (400)", msg)
        self.assertIn("912", msg)
        evt = self.env["atm.averba.event"].search(
            [("document_id", "=", self.fiscal_document.id)], limit=1
        )
        self.assertFalse(evt)

    @mock.patch(
        "requests.post",
        side_effect=[mocked_token_ok(), mocked_http_error()],
    )
    @mock.patch(
        "odoo.addons.atm_averba_mdfe.models.document.Document.build_proc_evento_mdfe_v3",
        return_value=b"<procEventoMDFe/>",
    )
    def test_mdfe_close_http_500(self, mock_build_proc, mock_post):
        with self.assertRaises(UserError) as err:
            self.fiscal_document.mdfe_close()

        self.assertIn("Falha ao enviar XML para AT&M", str(err.exception))
