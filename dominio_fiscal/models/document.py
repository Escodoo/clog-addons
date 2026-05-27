# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
from datetime import datetime

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FiscalDocument(models.Model):
    _inherit = "l10n_br_fiscal.document"

    state_dominio = fields.Selection(
        [
            ("pending", "Pending"),
            ("stored", "Stored"),
            ("duplicated", "Duplicated"),
            ("error", "Error"),
        ],
        string="Dominio",
        readonly=True,
    )

    state_dominio_msg = fields.Text(
        string="Feedback",
        readonly=True,
        help="Detailed feedback from Dominio API about the last send attempt.",
    )

    state_dominio_code = fields.Char(
        string="Code",
        readonly=True,
        help="Last API status code (SA2, EA13, EA10, etc).",
    )

    dominio_batch_id = fields.Char(
        string="Batch ID",
        readonly=True,
        help="Batch ID returned by Dominio API for the last send.",
    )

    dominio_event_ids = fields.One2many(
        comodel_name="dominio.event",
        inverse_name="document_id",
        string="Dominio Events",
        readonly=True,
    )

    def _get_document_xml(self):
        self.ensure_one()
        xml_file = self.authorization_file_id or self.send_file_id
        if xml_file and xml_file.datas:
            return base64.b64decode(xml_file.datas)
        if self.authorization_event_id:
            event = self.authorization_event_id
            if event.file_response_id and event.file_response_id.datas:
                return base64.b64decode(event.file_response_id.datas)
            if event.file_request_id and event.file_request_id.datas:
                return base64.b64decode(event.file_request_id.datas)
        for event in self.event_ids:
            if event.file_response_id and event.file_response_id.datas:
                return base64.b64decode(event.file_response_id.datas)
            if event.file_request_id and event.file_request_id.datas:
                return base64.b64decode(event.file_request_id.datas)
        raise UserError(_("XML not found in Fiscal Document"))

    @staticmethod
    def _fix_encoding(value):
        if not value or not isinstance(value, str):
            return value
        if "\\u00" in value:
            try:
                value = value.encode("utf-8").decode("unicode_escape")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value

    @staticmethod
    def _mask_credentials(response_json):
        """Mask sensitive fields in a JSON response string for safe storage."""
        if not response_json or not isinstance(response_json, str):
            return response_json
        try:
            data = json.loads(response_json)
            sensitive_keys = {
                "access_token",
                "refresh_token",
                "client_secret",
                "integrationKey",
                "token_type",
            }
            if isinstance(data, dict):
                for key in data:
                    if key in sensitive_keys and data[key]:
                        val = str(data[key])
                        if len(val) > 8:
                            data[key] = val[:4] + "****" + val[-4:]
                        elif val:
                            data[key] = "********"
            return json.dumps(data, indent=2)
        except (json.JSONDecodeError, TypeError):
            return response_json

    def _create_dominio_event(
        self,
        event_type,
        status_code="",
        status_description="",
        batch_id="",
        last_api_status_on=None,
        boxe_status_code="",
        boxe_status_message="",
        response_json="",
    ):
        self.ensure_one()
        self.env["dominio.event"].create(
            {
                "document_id": self.id,
                "event_type": event_type,
                "batch_id": str(batch_id) if batch_id else "",
                "status_code": status_code,
                "status_description": self._fix_encoding(status_description),
                "last_api_status_on": last_api_status_on,
                "boxe_status_code": boxe_status_code,
                "boxe_status_message": self._fix_encoding(boxe_status_message),
                "response_json": self._mask_credentials(
                    self._fix_encoding(response_json)
                ),
            }
        )

    def _check_dominio_status(self, batch_id, headers):
        self.ensure_one()
        url = "https://api.onvio.com.br/dominio/invoice/v3/batches/%s" % batch_id
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        check_json = response.json()
        file_expanded = check_json["filesExpanded"][0]
        api_status_code = file_expanded["apiStatus"]["code"]
        api_status_message = file_expanded["apiStatus"].get("message", "")

        last_api_status_on_raw = file_expanded.get("lastApiStatusOn", "")
        last_api_status_on = None
        if last_api_status_on_raw:
            try:
                dt = datetime.strptime(last_api_status_on_raw[:19], "%Y-%m-%dT%H:%M:%S")
                last_api_status_on = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                _logger.warning(
                    "Could not parse lastApiStatusOn: %s", last_api_status_on_raw
                )

        boxe_status_code = file_expanded.get("boxeStatus", {}).get("code", "")
        boxe_status_message = file_expanded.get("boxeStatus", {}).get("message", "")

        if api_status_code == "SA2":
            self.state_dominio = "stored"
            msg = _(
                "Documento armazenado com sucesso na Dominio. "
                "Código: %s, Mensagem: %s"
            ) % (api_status_code, api_status_message or "Sucesso")
            _logger.info("Document %s successfully stored", self.id)
        elif api_status_code == "EA10":
            self.state_dominio = "duplicated"
            msg = _("Documento já existe na Dominio. " "Código: %s, Mensagem: %s") % (
                api_status_code,
                api_status_message or "Duplicado",
            )
            _logger.warning("Document %s already exists", self.id)
        elif api_status_code == "EA13":
            self.state_dominio = "pending"
            msg = _(
                "Documento em processamento na Dominio. " "Código: %s, Mensagem: %s"
            ) % (api_status_code, api_status_message or "Processando")
            _logger.info("Document %s is pending processing in Dominio", self.id)
        else:
            self.state_dominio = "error"
            msg = _(
                "Falha ao processar documento na Dominio. " "Código: %s, Mensagem: %s"
            ) % (
                api_status_code,
                api_status_message or "N/A",
            )
            _logger.error("Error storing document %s", self.id)

        self.state_dominio_msg = msg
        self.state_dominio_code = api_status_code

        self._create_dominio_event(
            event_type="status_query",
            status_code=api_status_code,
            status_description=api_status_message,
            batch_id=batch_id,
            last_api_status_on=last_api_status_on,
            boxe_status_code=boxe_status_code,
            boxe_status_message=boxe_status_message,
            response_json=json.dumps(check_json, indent=2),
        )

    def _get_dominio_auth(self):
        """Returns (access_token, integration_key) and logs each API flow step."""
        self.ensure_one()
        company = self.company_id

        # Step 1: Generate OAuth2 Token
        _logger.info("Step 1: Generating Dominio OAuth2 token...")
        try:
            token_response = company._generate_dominio_token()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            self._create_dominio_event(
                event_type="token_generation",
                status_code="OK" if access_token else "FAIL",
                status_description="Token OAuth2 gerado com sucesso"
                if access_token
                else "Falha ao gerar token OAuth2",
                response_json=json.dumps(token_data, indent=2),
            )
        except requests.HTTPError as e:
            self._create_dominio_event(
                event_type="token_generation",
                status_code="ERROR",
                status_description="Erro ao gerar token: %s" % e,
            )
            raise

        # Step 2: Confirm client key
        _logger.info("Step 2: Confirming client key...")
        try:
            x_integration_key = company.get_dominio_environment()
            confirm_headers = {
                "Authorization": "Bearer " + access_token,
                "x-integration-key": x_integration_key,
            }
            confirm_response = requests.get(
                "https://api.onvio.com.br/dominio/integration/v1/activation/info",
                headers=confirm_headers,
            )
            confirm_response.raise_for_status()
            confirm_data = confirm_response.json()
            self._create_dominio_event(
                event_type="key_confirmation",
                status_code="OK",
                status_description=("Contabilidade: %s, Cliente: %s, CNPJ: %s")
                % (
                    confirm_data.get("companyName", ""),
                    confirm_data.get("customerName", ""),
                    confirm_data.get("customerDocument", ""),
                ),
                response_json=json.dumps(confirm_data, indent=2),
            )
        except requests.HTTPError as e:
            self._create_dominio_event(
                event_type="key_confirmation",
                status_code="ERROR",
                status_description="Erro ao confirmar chave: %s" % e,
            )
            raise

        # Step 3: Generate Integration Key
        _logger.info("Step 3: Generating integration key...")
        try:
            enable_headers = {
                "Authorization": "Bearer " + access_token,
                "x-integration-key": x_integration_key,
            }
            enable_response = requests.post(
                "https://api.onvio.com.br/dominio/integration/v1/activation/enable",
                headers=enable_headers,
            )
            enable_response.raise_for_status()
            enable_data = enable_response.json()
            integration_key = enable_data.get("integrationKey")
            masked_key = (
                integration_key[:4] + "****" + integration_key[-4:]
                if integration_key and len(integration_key) > 8
                else "********"
            )
            self._create_dominio_event(
                event_type="integration_key",
                status_code="OK",
                status_description="Integration Key gerada: %s" % masked_key,
                response_json=json.dumps(enable_data, indent=2),
            )
        except requests.HTTPError as e:
            self._create_dominio_event(
                event_type="integration_key",
                status_code="ERROR",
                status_description="Erro ao gerar integration key: %s" % e,
            )
            raise

        return access_token, integration_key

    def action_send_dominio(self):
        self.ensure_one()
        try:
            access_token, integration_key = self._get_dominio_auth()

            headers = {
                "Authorization": "Bearer %s" % access_token,
                "x-integration-key": integration_key,
            }
            file_content = self._get_document_xml()

            url = "https://api.onvio.com.br/dominio/invoice/v3/batches"
            files = {
                "file[]": (None, file_content, "application/xml"),
                "query": (None, '{"boxe/File": false}', "application/json"),
            }

            _logger.info("Step 4: Sending document %s to Dominio API", self.id)

            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            response_json = response.json()
            batch_id = response_json["id"]

            self._create_dominio_event(
                event_type="xml_send",
                status_code="SENT",
                status_description="XML enviado. Batch ID: %s" % batch_id,
                batch_id=batch_id,
                response_json=json.dumps(response_json, indent=2),
            )

            self.dominio_batch_id = str(batch_id)

            # Step 5: Query the send status
            _logger.info("Step 5: Querying send status for batch %s...", batch_id)
            self._check_dominio_status(batch_id, headers)

        except requests.HTTPError as e:
            self.state_dominio = "error"
            self.state_dominio_code = "HTTP"
            self.state_dominio_msg = _("Falha na comunicação com a API Dominio: %s") % (
                e
            )
            raise UserError(
                _("Failed to send fiscal XML to Dominio API: %s") % e
            ) from e

    def action_sync_dominio(self):
        self.ensure_one()
        if not self.dominio_batch_id:
            raise UserError(
                _("Nenhum batch ID encontrado. Envie o documento primeiro.")
            )
        try:
            access_token, integration_key = self._get_dominio_auth()
            headers = {
                "Authorization": "Bearer %s" % access_token,
                "x-integration-key": integration_key,
            }
            self._check_dominio_status(self.dominio_batch_id, headers)
        except requests.HTTPError as e:
            self.state_dominio = "error"
            self.state_dominio_code = "HTTP"
            self.state_dominio_msg = _(
                "Falha ao sincronizar status com a API Dominio: %s"
            ) % (e)
            raise UserError(
                _("Falha ao sincronizar status com a API Dominio: %s") % e
            ) from e
