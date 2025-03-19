# Copyright 2024 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock
from xml.dom import minidom

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

    @property
    def content(self):
        if self.http_error:
            raise requests.HTTPError("Mocked HTTP Error")
        else:
            return self._content


def mocked_http_error(*args, **kwargs):
    return MockResponse({}, 500, False, False, True)


def mocked_ndd_averba_token(*args, **kwargs):
    return MockResponse({"token_acesso": "ABC"}, 200, True)


def mocked_cte_endorsement(*args, **kwargs):
    return MockResponse(
        {
            "status": "sucesso",
            "mensagem": "A averbação foi aprovada!",
            "documento": {
                "serie": "1",
                "numero": 12345678,
                "chave": "35240908318053000248570030000287201001594030",
                "status": "endorsed",
            },
            "averbacoes": [
                {
                    "protocolo": "9d168936-470d-4435-b159-c8fcb8977da6",
                    "tipo": "CT-e",
                    "cte_id": "9d168936-2ca2-445f-aa30-25b3844d3f41",
                    "serie": "1",
                    "numero": 12345678,
                    "numero_averbacao": "0000012240831805300024857003000028720130",
                    "apolice_id": "9d1679b9-5e72-4934-ab8c-d7173fd8e87f",
                    "seguradora_id": "9bfa7549-02df-4fd9-ac9a-da697434d434",
                    "corretora_id": "9bfa79ad-c626-4a29-a8a4-8baab56fbbee",
                    "numero_documento_emissor": "08318053000248",
                    "valor_carga": 16392.55,
                    "total_segurado": 16392.55,
                    "data_atualizacao": "2024-09-24 15:06:08",
                    "data_criacao": "2024-09-24 15:06:08",
                },
            ],
        },
        200,
        True,
    )


def mocked_cte_endorsement_error(*args, **kwargs):
    return MockResponse(
        {"status": "erro", "mensagem": "simplexml_load_string(): parser error"},
        400,
        False,
    )


def mocked_cancel_cte_endorsement(*args, **kwargs):
    return MockResponse(
        {
            "status": "sucesso",
            "mensagem": "O cancelamento foi registrado para o CT-e!",
            "documento": {
                "serie": "1",
                "numero": 12345678,
                "chave": "35240908318053000248570030000287201001594030",
                "status": "canceled",
            },
            "averbacoes": [
                {
                    "protocolo": "9d1821d5-ccc0-470c-ae38-27047c6f4e4d",
                    "data_emissao": "2024-08-13 15:43:14",
                    "data_embarque": "2024-09-25 10:08:15",
                    "data_criacao": "2024-09-25 10:08:15",
                    "total_segurado": "16392.55",
                }
            ],
        },
        200,
        True,
    )


def mocked_cancel_cte_endorsement_error(*args, **kwargs):
    return MockResponse(
        {
            "status": "erro",
            "mensagem": "Não foi possível registrar o cancelamento para o CT-e!",
            "erros": ["O evento já foi registrado anteriormente!"],
        },
        400,
        False,
    )


def mocked_cte_retrieve(*args, **kwargs):
    return MockResponse(
        {},
        200,
        True,
        """<?xml version="1.0"?>
        <cteProc versao="4.00"><CTe></CTe><protCTe></protCTe></cteProc>""",
    )


class TestNddAverbaCte(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestNddAverbaCte, cls).setUpClass()
        cls.company = cls.env.company
        cls.company.ndd_averba_environment = "2"
        cls.company.ndd_averba_homologation_user_email = "user@example.com"
        cls.company.ndd_averba_homologation_user_password = "123456"
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
        self.fiscal_document._compute_ndd_averba_event_ids()
        self.assertEqual(
            self.fiscal_document.ndd_averba_event_ids, self.env["ndd.averba.event"]
        )

        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, False)

        self.fiscal_document._compute_ndd_averba_date_send()
        self.assertEqual(self.fiscal_document.ndd_averba_date_send, False)

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_ndd_averba_token(),
            mocked_cte_endorsement(),
        ],
    )
    def test_cte_endorsement(self, mock_post):
        self.fiscal_document.cte_endorsement()
        ndd_averba_event = self.env["ndd.averba.event"].search(
            [("document_id", "=", self.fiscal_document.id)],
            limit=1,
        )
        self.assertEqual(ndd_averba_event.endorsement_state, "endorsed")
        self.assertEqual(
            ndd_averba_event.endorsement_message, "A averbação foi aprovada!"
        )

        self.fiscal_document._compute_ndd_averba_event_ids()
        self.assertEqual(self.fiscal_document.ndd_averba_event_ids, ndd_averba_event)

        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, "endorsed")

        self.fiscal_document._compute_ndd_averba_date_send()
        self.assertEqual(
            self.fiscal_document.ndd_averba_date_send, ndd_averba_event.date
        )

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_ndd_averba_token(),
            mocked_cte_endorsement_error(),
        ],
    )
    def test_cte_endorsement_error(self, mock_post):
        self.fiscal_document.cte_endorsement()
        ndd_averba_event = self.env["ndd.averba.event"].search(
            [("document_id", "=", self.fiscal_document.id)],
            limit=1,
        )
        self.assertEqual(ndd_averba_event.endorsement_state, "error")
        self.assertEqual(
            ndd_averba_event.endorsement_message,
            "simplexml_load_string(): parser error",
        )

        self.fiscal_document._compute_ndd_averba_event_ids()
        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, "error")

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_ndd_averba_token(),
            mocked_http_error(),
        ],
    )
    def test_cte_endorsement_http_error(self, mock_post):
        with self.assertRaises(UserError) as error:
            self.fiscal_document.cte_endorsement()

        self.assertEqual(
            str(error.exception),
            "Failed to send XML to NDD Averba API: Mocked HTTP Error",
        )

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_ndd_averba_token(),
            mocked_cte_endorsement(),
            mocked_ndd_averba_token(),
            mocked_cancel_cte_endorsement(),
        ],
    )
    def test_cancel_cte_endorsement(self, mock_post):
        self.fiscal_document.cte_endorsement()
        self.fiscal_document._compute_ndd_averba_event_ids()
        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, "endorsed")

        self.fiscal_document.state_edoc = "cancelada"
        self.fiscal_document.cancel_cte_endorsement()
        ndd_averba_event = self.env["ndd.averba.event"].search(
            [("document_id", "=", self.fiscal_document.id)],
            limit=1,
        )
        self.assertEqual(ndd_averba_event.endorsement_state, "cancel")
        self.assertEqual(
            ndd_averba_event.endorsement_message,
            "O cancelamento foi registrado para o CT-e!",
        )

        self.fiscal_document._compute_ndd_averba_event_ids()
        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, "cancel")

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_ndd_averba_token(),
            mocked_cte_endorsement(),
            mocked_ndd_averba_token(),
            mocked_cancel_cte_endorsement_error(),
        ],
    )
    def test_cancel_cte_endorsement_error(self, mock_post):
        self.fiscal_document.cte_endorsement()
        self.fiscal_document._compute_ndd_averba_event_ids()
        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, "endorsed")

        self.fiscal_document.state_edoc = "cancelada"
        self.fiscal_document.cancel_cte_endorsement()
        ndd_averba_event = self.env["ndd.averba.event"].search(
            [("document_id", "=", self.fiscal_document.id)],
            limit=1,
        )
        self.assertEqual(ndd_averba_event.endorsement_state, "error")
        self.assertEqual(
            ndd_averba_event.endorsement_message,
            "Não foi possível registrar o cancelamento para o CT-e!",
        )
        self.assertEqual(
            ndd_averba_event.error_message, "O evento já foi registrado anteriormente!"
        )

        self.fiscal_document._compute_ndd_averba_event_ids()
        self.fiscal_document._compute_ndd_averba_endorsement_state()
        self.assertEqual(self.fiscal_document.ndd_averba_endorsement_state, "endorsed")

    @mock.patch(
        "requests.post",
        side_effect=[
            mocked_ndd_averba_token(),
            mocked_cte_endorsement(),
            mocked_ndd_averba_token(),
            mocked_http_error(),
        ],
    )
    def test_cancel_cte_endorsement_http_error(self, mock_post):
        with self.assertRaises(UserError) as error:
            self.fiscal_document.cte_endorsement()
            self.fiscal_document._compute_ndd_averba_event_ids()
            self.fiscal_document._compute_ndd_averba_endorsement_state()
            self.assertEqual(
                self.fiscal_document.ndd_averba_endorsement_state, "endorsed"
            )

            self.fiscal_document.state_edoc = "cancelada"
            self.fiscal_document.cancel_cte_endorsement()

        self.assertEqual(
            str(error.exception),
            "Failed to send cancelation request to NDD Averba API: Mocked HTTP Error",
        )

    @mock.patch("requests.post", side_effect=mocked_ndd_averba_token)
    @mock.patch("requests.get", side_effect=mocked_cte_retrieve)
    def test_ndd_averba_cte_retrieve(self, mock_post, mock_get):
        with self.assertRaises(UserError) as error:
            self.fiscal_document.ndd_averba_cte_retrieve()

        error_message = str(error.exception)
        parsed_xml = minidom.parseString(
            """<?xml version="1.0"?>
            <cteProc versao="4.00"><CTe></CTe><protCTe></protCTe></cteProc>"""
        )
        formatted_xml = parsed_xml.toprettyxml()
        self.assertEqual(error_message, formatted_xml)

    @mock.patch("requests.post", side_effect=mocked_ndd_averba_token)
    @mock.patch("requests.get", side_effect=mocked_http_error)
    def test_ndd_averba_cte_retrieve_http_error(self, mock_post, mock_get):
        with self.assertRaises(UserError) as error:
            self.fiscal_document.ndd_averba_cte_retrieve()

        self.assertEqual(
            str(error.exception),
            "Failed to retrieve XML from NDD Averba API: Mocked HTTP Error",
        )
