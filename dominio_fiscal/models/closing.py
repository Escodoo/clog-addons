# Copyright 2024 - TODAY, Kaynnan Lemes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.dominio_base.constants.dominio import get_dominio_api_url

_logger = logging.getLogger(__name__)


class FiscalClosing(models.Model):
    _inherit = "l10n_br_fiscal.closing"

    def _send_dominio_xml(self):
        """
        Sends fiscal XML data to a third-party API endpoint (Dominio).

        This method prepares and sends an XML payload containing fiscal data
        to a specified endpoint using OAuth2 authorization and integration key.

        Raises a UserError if the HTTP request encounters an error.

        Returns:
            requests.Response: Response object from the API call.
        """
        try:
            api_url = get_dominio_api_url(self.env)
            url = api_url.get("xml_url")

            integration_data = self.company_id._generate_key_integration()
            access_token = integration_data.get("access_token")
            integration_key = integration_data.get("integrationKey")

            results = []

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
                    if document.dominio_state == "stored":
                        _logger.info(
                            f"Document {document.id} already stored, skipping."
                        )
                        continue

                    if document.dominio_state != "stored":
                        xml_file = (
                            document.authorization_file_id or document.send_file_id
                        )
                        if xml_file and xml_file.datas:
                            file_content = base64.b64decode(xml_file.datas)

                            _logger.info(
                                f"Preparing to send XML for document {document.id}"
                            )

                            headers = {
                                "Authorization": f"Bearer {access_token}",
                                "x-integration-key": integration_key,
                            }

                            data = {
                                "file[]": (None, file_content, "application/xml"),
                                "query": (
                                    None,
                                    json.dumps(
                                        {"boxe/File": self.company_id.dominio_box_e}
                                    ),
                                    "application/json",
                                ),
                            }

                            response = requests.post(url, headers=headers, files=data)
                            response.raise_for_status()
                            response_json = response.json()

                            results.append(
                                {
                                    "integrationKey": integration_key,
                                    "access_token": access_token,
                                    "id": response_json["id"],
                                    "document_id": document.id,
                                }
                            )

                            _logger.info(
                                f"Successfully sent XML for document {document.id}"
                            )

                        else:
                            raise UserError(_("XML Not found in Fiscal Document"))

            return results

        except requests.HTTPError as e:
            raise UserError(
                _("Failed to send fiscal XML to Dominio API: %s") % e
            ) from e

    def _check_send_xml_dominio(self, results):
        """
        Checks the status of fiscal XML data sent to a third-party API endpoint (Dominio).

        This method checks the status of fiscal XML data previously sent to a specified API
        endpoint using OAuth2 authorization and integration key retrieved from each result in
        the `results` list. It expects the `results` to be fetched beforehand using the
        `_send_dominio_xml()` method.

        Raises a UserError if the API returns an error status related to XML validation,
        company registration, or if the HTTP request encounters an error.

        Returns:
            bool: True if the XML data was successfully stored in the API.
                Raises UserError for any errors encountered during the process.
        """
        try:
            # Process each result
            for result in results:
                access_token = result.get("access_token")
                integration_key = result.get("integrationKey")
                id_xml = result.get("id")
                document_id = result.get("document_id")

                document = self.env["l10n_br_fiscal.document"].browse(document_id)

                # Check if the document is already stored to prevent re-checking
                if document.dominio_state == "stored":
                    _logger.info(
                        f"Document {document.id} already checked and stored, skipping."
                    )
                    continue

                # Construct URL for API endpoint
                api_url = get_dominio_api_url(self.env)
                url = api_url.get("xml_url") + f"/{id_xml}"

                # Prepare headers with integration key and access token
                headers = {
                    "x-integration-key": integration_key,
                    "Authorization": f"Bearer {access_token}",
                }

                _logger.info(
                    f"Requesting status for document {document.id} from Dominio API"
                )

                # Make a GET request to the API endpoint
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                response_json = response.json()

                # Check for different API response conditions
                if response.status_code == 200:
                    status_code = response_json["filesExpanded"][0]["apiStatus"]["code"]
                    id_transaction = response_json["id"]
                    response_msg = response_json["filesExpanded"][0]["apiStatus"][
                        "message"
                    ]
                    if status_code == "SA2":
                        document.dominio_transaction = id_transaction
                        document.dominio_code = status_code
                        document.dominio_response = response_msg
                        document.dominio_state = "stored"
                        _logger.info(
                            f"Document {document.id} successfully stored in Dominio API"
                        )
                    elif status_code == "EA10":
                        document.dominio_transaction = id_transaction
                        document.dominio_code = status_code
                        document.dominio_response = response_msg
                        document.dominio_state = "stored"
                        _logger.warning(
                            f"Document {document.id} already exists in Dominio API"
                        )
                    else:
                        document.dominio_transaction = id_transaction
                        document.dominio_code = status_code
                        document.dominio_response = response_msg
                        document.dominio_state = "error"
                        _logger.error(
                            f"Error storing document {document.id} in Dominio API"
                        )
                else:
                    _logger.error(f"Request error: status code {response.status_code}")
                    raise UserError(_("Request error: %s") % response.status_code)

            _logger.info("Finished checking XML data sent to Dominio API")

        except requests.HTTPError as e:
            _logger.error(
                "HTTP error occurred while checking XML status with Dominio API: %s", e
            )
            raise UserError(_("Request error: %s") % e) from e

    def action_dominio_send(self):
        # Fetch XML sending results
        results = self._send_dominio_xml()
        # Check XML response
        self._check_send_xml_dominio(results)

    def action_close(self):
        res = super().action_close()
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
                if document.dominio_state != "stored":
                    raise UserError(
                        _(
                            "Unable to close Fiscal Closing: Some documents are not "
                            "stored in the Dominio API."
                        )
                    )
        return res
