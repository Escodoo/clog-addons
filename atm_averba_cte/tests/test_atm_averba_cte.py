# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock
from unittest.mock import MagicMock

import requests

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


class MockResponse:
    def __init__(self, json_data, status_code, ok, content=False, http_error=False):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = ok
        self._content = content
        self.http_error = http_error

    def json(self):
        if self.http_error:
            raise requests.HTTPError("Mocked HTTP Error")
        else:
            return self.json_data

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"Mocked error with status {self.status_code}")

    @property
    def content(self):
        if self.http_error:
            raise requests.HTTPError("Mocked HTTP Error")
        else:
            return self._content


def mocked_http_error(*args, **kwargs):
    return MockResponse({}, 500, False, False, True)


def mocked_atm_averba_token(*args, **kwargs):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.raise_for_status.return_value = None
    mock_res.json.return_value = {"Bearer": "ABC"}
    mock_res.text = '{"Bearer":"ABC"}'
    mock_res.content = b'{"Bearer":"ABC"}'
    return mock_res


def mocked_cte_endorsement(*args, **kwargs):
    return MockResponse(
        {
            "Numero": "12345678",
            "Serie": "1",
            "Filial": "001",
            "CNPJCli": "08318053000248",
            "TpDoc": "Ordem de Carga",
            "InfAdic": "Averbação registrada com sucesso.",
            "Averbado": {
                "dhAverbacao": "2025-07-23T12:34:56",
                "Protocolo": "ABC123-PROTOCOLO-456",
                "DadosSeguro": [
                    {
                        "NumeroAverbacao": "987654321000001",
                        "CNPJSeguradora": "12345678000199",
                        "NomeSeguradora": "Seguradora Exemplo S/A",
                        "NumApolice": "AP123456789",
                        "TpMov": "1",
                        "ValorAverbado": 16392.55,
                    }
                ],
            },
            "Infos": {
                "Info": [
                    {"Codigo": "0", "Descricao": "Averbação realizada com sucesso"},
                ]
            },
        },
        200,
        True,
    )


def mocked_cte_endorsement_error(*args, **kwargs):
    return MockResponse(
        {
            "Numero": "12345678",
            "Serie": "1",
            "Filial": "001",
            "CNPJCli": "08318053000248",
            "TpDoc": "2",
            "InfAdic": "Erro ao processar a averbação.",
            "Erros": [
                {
                    "Codigo": "001",
                    "Descricao": "Valor da carga excede o limite da apólice.",
                    "ValorEsperado": "15000.00",
                    "ValorInformado": "25000.00",
                }
            ],
        },
        400,
        False,
    )


class TestAtmAverbaCte(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestAtmAverbaCte, cls).setUpClass()
        cls.company = cls.env.company
        cls.company.atm_averba_environment = "2"
        cls.company.atm_averba_user = "user@example.com"
        cls.company.atm_averba_user_password = "123456"
        cls.fiscal_document = cls.env.ref("l10n_br_fiscal.demo_nfe_other_state")
        cls.fiscal_document.document_type_id = cls.env.ref(
            "l10n_br_fiscal.document_57"
        ).id
        cls.fiscal_document_event_success = cls.env["l10n_br_fiscal.event"].create(
            {
                "type": "0",
                "company_id": cls.company.id,
                "document_id": cls.fiscal_document.id,
                "document_type_id": cls.fiscal_document.document_type_id.id,
                "justification": "Generate the XML file",
                "protocol_number": "123",
                "document_serie_id": 1,
                "document_number": "12345678",
                "file_request_id": cls.env.ref("l10n_br_fiscal.dummy_file_1").id,
            }
        )
        cls.fiscal_document_event_cancel = cls.env["l10n_br_fiscal.event"].create(
            {
                "type": "2",
                "company_id": cls.company.id,
                "document_id": cls.fiscal_document.id,
                "document_type_id": cls.fiscal_document.document_type_id.id,
                "justification": "Cancel the XML file",
                "protocol_number": "123",
                "document_serie_id": 1,
                "document_number": "12345678",
                "file_response_id": cls.env.ref("l10n_br_fiscal.dummy_file_1").id,
            }
        )
        cls.fiscal_document.authorization_event_id = (
            cls.fiscal_document_event_success.id
        )
        cls.fiscal_document.cancel_event_id = cls.fiscal_document_event_cancel.id
        cls.fiscal_document.document_key = (
            "35240908318053000248570030000287201001594030"
        )

    def test_fiscal_document_computes(self):
        self.fiscal_document._compute_atm_averba_event_ids()
        self.assertEqual(
            self.fiscal_document.atm_averba_event_ids, self.env["atm.averba.event"]
        )

        self.fiscal_document._compute_atm_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.atm_averba_endorsement_state, False)

        self.fiscal_document._compute_atm_averba_date_send()
        self.assertEqual(self.fiscal_document.atm_averba_date_send, False)

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_atm_averba_token(),
            mocked_cte_endorsement(),
        ],
    )
    def test_cte_endorsement(self, mock_post):
        self.fiscal_document.cte_endorsement()
        atm_averba_event = self.env["atm.averba.event"].search(
            [("document_id", "=", self.fiscal_document.id)],
            limit=1,
        )
        self.assertEqual(atm_averba_event.endorsement_state, "endorsed")

        self.fiscal_document._compute_atm_averba_event_ids()
        self.assertEqual(self.fiscal_document.atm_averba_event_ids, atm_averba_event)

        self.fiscal_document._compute_atm_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.atm_averba_endorsement_state, "endorsed")

        self.fiscal_document._compute_atm_averba_date_send()
        self.assertEqual(
            self.fiscal_document.atm_averba_date_send, atm_averba_event.date
        )

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_atm_averba_token(),
            mocked_cte_endorsement_error(),
        ],
    )
    def test_cte_endorsement_error(self, mock_post):
        with self.assertRaises(UserError) as err:
            self.fiscal_document.cte_endorsement()
        self.assertIn("Falha ao enviar XML para AT&M", str(err.exception))

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_atm_averba_token(),
            mocked_http_error(),
        ],
    )
    def test_cte_endorsement_http_error(self, mock_post):
        with self.assertRaises(UserError) as error:
            self.fiscal_document.cte_endorsement()

        self.assertEqual(
            str(error.exception),
            "Falha ao enviar XML para AT&M: Mocked error with status 500",
        )
