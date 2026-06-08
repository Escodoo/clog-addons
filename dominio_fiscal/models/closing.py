# Copyright 2024 - TODAY, Kaynnan Lemes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FiscalClosing(models.Model):
    _inherit = "l10n_br_fiscal.closing"

    def _send_dominio_xml(self):
        try:
            url = "https://api.onvio.com.br/dominio/invoice/v3/batches"
            results = []
            auth_obtained = False
            access_token = ""
            integration_key = ""

            document_fields = [
                self.document_nfe_ids,
                self.document_nfse_ids,
                self.document_nfce_ids,
                self.document_cfe_ids,
                self.document_cfeecf_ids,
                self.document_nfse_ids,
                self.document_rl_ids,
            ]

            for document_field in document_fields:
                for document in document_field:
                    xml_file = document.authorization_file_id or document.send_file_id

                    if xml_file and xml_file.datas:
                        file_content = base64.b64decode(xml_file.datas)

                        # Get auth on the first document to create full event trail
                        if not auth_obtained:
                            _logger.info(
                                "Obtaining Dominio auth via first document %s...",
                                document.id,
                            )
                            access_token, integration_key = document._get_dominio_auth()
                            auth_obtained = True

                        _logger.info(
                            f"Preparing to send XML for document {document.id}"
                        )

                        headers = {
                            "Authorization": f"Bearer {access_token}",
                            "x-integration-key": integration_key,
                        }

                        data = {
                            "file[]": (None, file_content, "application/xml"),
                            "query": (None, '{"boxe/File": false}', "application/json"),
                        }

                        response = requests.post(url, headers=headers, files=data)
                        response.raise_for_status()
                        response_json = response.json()
                        batch_id = response_json["id"]

                        document._create_dominio_event(
                            event_type="xml_send",
                            status_code="SENT",
                            status_description="XML enviado via fechamento. "
                            "Batch ID: %s" % batch_id,
                            batch_id=batch_id,
                            response_json=json.dumps(response_json, indent=2),
                        )

                        results.append(
                            {
                                "integrationKey": integration_key,
                                "access_token": access_token,
                                "id": batch_id,
                                "document_id": document.id,
                            }
                        )

                        _logger.info(
                            f"Successfully sent XML for document {document.id}"
                        )

                    else:
                        document.state_dominio = "error"
                        document.state_dominio_msg = (
                            _("XML não encontrado no documento fiscal %s") % document.id
                        )

            if not auth_obtained:
                raise UserError(
                    _(
                        "Nenhum documento fiscal com XML encontrado "
                        "para enviar a Dominio."
                    )
                )

            return results

        except requests.HTTPError as e:
            raise UserError(
                _("Failed to send fiscal XML to Dominio API: %s") % e
            ) from e

    def _check_send_xml_dominio(self):
        try:
            results = self._send_dominio_xml()
            for result in results:
                access_token = result.get("access_token")
                integration_key = result.get("integrationKey")
                id_xml = result.get("id")
                document_id = result.get("document_id")

                document = self.env["l10n_br_fiscal.document"].browse(document_id)

                document.dominio_batch_id = str(id_xml)

                url = "https://api.onvio.com.br/dominio/invoice/v3/batches/%s" % id_xml
                headers = {
                    "x-integration-key": integration_key,
                    "Authorization": f"Bearer {access_token}",
                }

                _logger.info(
                    f"Requesting status for document {document.id} from Dominio API"
                )

                response = requests.get(url, headers=headers)
                response.raise_for_status()
                response_json = response.json()

                if response.status_code == 200:
                    file_expanded = response_json["filesExpanded"][0]
                    api_status_code = file_expanded["apiStatus"]["code"]
                    api_status_message = file_expanded["apiStatus"].get("message", "")

                    if api_status_code == "SA2":
                        document.state_dominio = "stored"
                        document.state_dominio_msg = _(
                            "Documento armazenado com sucesso "
                            "na Dominio. Código: %s, Mensagem: %s"
                        ) % (api_status_code, api_status_message or "Sucesso")
                        _logger.info(
                            f"Document {document.id} successfully stored in Dominio API"
                        )
                    elif api_status_code == "EA10":
                        document.state_dominio = "duplicated"
                        document.state_dominio_msg = _(
                            "Documento já existe na "
                            "Dominio. Código: %s, Mensagem: %s"
                        ) % (api_status_code, api_status_message or "Duplicado")
                        _logger.warning(
                            f"Document {document.id} already exists in Dominio API"
                        )
                    elif api_status_code == "EA13":
                        document.state_dominio = "pending"
                        document.state_dominio_msg = _(
                            "Documento em processamento "
                            "na Dominio. Código: %s, Mensagem: %s"
                        ) % (api_status_code, api_status_message or "Processando")
                        _logger.info(
                            f"Document {document.id} is pending processing "
                            "in Dominio API"
                        )
                    else:
                        document.state_dominio = "error"
                        document.state_dominio_msg = _(
                            "Falha ao processar documento "
                            "na Dominio. Código: %s, Mensagem: %s"
                        ) % (
                            api_status_code,
                            api_status_message or "N/A",
                        )
                        _logger.error(
                            f"Error storing document {document.id} in Dominio API"
                        )

                    document.state_dominio_code = api_status_code
                    document._create_dominio_event(
                        event_type="status_query",
                        status_code=api_status_code,
                        status_description=api_status_message,
                        batch_id=id_xml,
                        response_json=json.dumps(response_json, indent=2),
                    )
                else:
                    _logger.error(
                        f"Request error: its status was {response.status_code}"
                    )
                    raise UserError(
                        _(f"Request error: its status was {response.status_code}")
                    )

            _logger.info("Finished checking XML data sent to Dominio API")

        except requests.HTTPError as e:
            _logger.error(
                "HTTP error occurred while checking XML status with Dominio API: %s", e
            )
            raise UserError(_("Request error: %s") % e) from e

    def action_dominio_send(self):
        self._check_send_xml_dominio()
