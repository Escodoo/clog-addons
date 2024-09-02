# Copyright 2024 - TODAY, Kaynnan Lemes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# flake8: noqa: B950

import base64
import json
import logging
from datetime import datetime

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.dominio_base.constants.dominio import get_dominio_api_url

from ..constants.dominio_species import species_to_document_type

_logger = logging.getLogger(__name__)


class FiscalClosing(models.Model):
    _inherit = "l10n_br_fiscal.closing"

    incoming_payment_move_line_ids = fields.Many2many(
        "account.move.line",
        compute="_compute_incoming_payment_move_line_ids",
        readonly=True,
    )
    outgoing_payment_move_line_ids = fields.Many2many(
        "account.move.line",
        compute="_compute_outgoing_payment_move_line_ids",
        readonly=True,
    )

    def _compute_incoming_payment_move_line_ids(self):
        for record in self:
            # Inicializa o campo com uma lista vazia para garantir que ele esteja sempre atribu�do
            record.incoming_payment_move_line_ids = []

            # Busca todas as linhas de lan�amento cont�bil no sistema
            move_line = self.env["account.move.line"].search([])

            # Recupera o intervalo de datas (date_min e date_max)
            date_min, date_max = record._date_range()

            # Aplica o filtro nas linhas de movimento: seleciona linhas que s�o 'receivable',
            # dentro do intervalo de datas e que perten�am � mesma empresa que o registro
            line_ids = move_line.filtered(
                lambda line: line.account_id.internal_type == "receivable"
                and datetime.combine(line.date, datetime.min.time()) >= date_min
                and datetime.combine(line.date, datetime.min.time()) <= date_max
                and line.company_id == record.company_id
            )

            # Se houver linhas filtradas, processa-as
            if line_ids:
                payment_move_lines = []
                for lines in line_ids:
                    # Verifica se o move_id existe para a linha atual
                    if lines.move_id:
                        for move in lines.move_id.filtered(
                            lambda move: move.document_type_id
                        ):
                            # Acumula os partials reconciliados para cada move
                            payment_move_lines += [
                                aml.id
                                for partial, amount, aml in move._get_reconciled_invoices_partials()
                            ]

                # Atribui o resultado acumulado ao campo
                record.incoming_payment_move_line_ids = payment_move_lines

    def _compute_outgoing_payment_move_line_ids(self):
        for record in self:
            # Inicializa o campo com uma lista vazia para garantir que ele esteja sempre atribuído
            record.outgoing_payment_move_line_ids = []

            # Busca todas as linhas de lançamento contábil no sistema
            move_line = self.env["account.move.line"].search([])

            # Recupera o intervalo de datas (date_min e date_max)
            date_min, date_max = record._date_range()

            # Aplica o filtro nas linhas de movimento: seleciona linhas que são 'payable',
            # dentro do intervalo de datas e que pertençam à mesma empresa que o registro
            line_ids = move_line.filtered(
                lambda line: line.account_id.internal_type == "payable"
                and datetime.combine(line.date, datetime.min.time()) >= date_min
                and datetime.combine(line.date, datetime.min.time()) <= date_max
                and line.company_id == record.company_id
            )

            # Se houver linhas filtradas, processa-as
            if line_ids:
                payment_move_lines = []
                for lines in line_ids:
                    # Verifica se o move_id existe para a linha atual
                    if lines.move_id:
                        for move in lines.move_id.filtered(
                            lambda move: move.document_type_id
                        ):
                            # Acumula os partials reconciliados para cada move
                            payment_move_lines += [
                                aml.id
                                for partial, amount, aml in move._get_reconciled_invoices_partials()
                            ]

                # Atribui o resultado acumulado ao campo
                record.outgoing_payment_move_line_ids = payment_move_lines

    def _prepare_xml_payments(self):
        results = []

        payment_fields = [
            self.incoming_payment_move_line_ids,
            self.outgoing_payment_move_line_ids,
        ]

        for payment_field in payment_fields:
            for payment in payment_field:
                if payment.dominio_state == "stored":
                    _logger.info(f"Payment {payment.id} already stored, skipping.")
                    continue

                document_type_specie = None
                move = payment.move_id

                if move.move_type in (
                    "in_invoice",
                    "out_invoice",
                    "in_refund",
                    "out_refund",
                ):
                    fiscal_document = move.fiscal_document_id
                else:
                    reconciled_invoices = move._get_reconciled_invoices_partials()
                    if reconciled_invoices:
                        fiscal_document = reconciled_invoices[0][
                            2
                        ].move_id.fiscal_document_id
                    else:
                        fiscal_document = None

                if not fiscal_document:
                    _logger.warning(f"Fiscal document not found for move {move.id}.")
                    continue

                document_specie = fiscal_document.dominio_species_code
                document_serie = fiscal_document.document_serie
                document_number = fiscal_document.document_number

                reference = payment.name
                title = move.name
                value_received = (
                    abs(payment.debit) if payment.debit > 0 else abs(payment.credit)
                )
                date = payment.date
                due_date = payment.date_maturity
                supplier = None

                document_type_specie = species_to_document_type.get(
                    str(document_specie), None
                )

                if document_type_specie is None:
                    _logger.warning(
                        f"Document specie {document_specie} not recognized."
                    )
                    continue

                if document_type_specie == 1:  # Purchase
                    supplier = move.partner_id.cnpj_cpf_stripped
                    _logger.info(
                        f"Processing incoming payment for partner {move.partner_id.name}."
                    )
                elif document_type_specie == 2:  # Sales
                    _logger.info(
                        f"Processing outgoing payment for partner {move.partner_id.name}."
                    )
                elif document_type_specie == 4:  # Service
                    _logger.info(
                        f"Processing service payment for partner {move.partner_id.name}."
                    )

                file_content = f"""
                    <Baixas>
                        <infBaixas versao="1.00">
                            <parcela>
                                <cnpj>{move.company_id.cnpj_cpf_stripped}</cnpj>
                                <tipo>{document_type_specie}</tipo>
                                <especie>{document_specie}</especie>
                                <serie>{document_serie}</serie>
                                <numero>{document_number}</numero>
                                <datavencimento>{due_date}</datavencimento>
                                <datapagamento>{date}</datapagamento>
                                <valorrecebido>{value_received}</valorrecebido>
                                <fornecedor>{supplier}</fornecedor>
                                <historico>{reference}</historico>
                                <titulo>{title}</titulo>
                            </parcela>
                        </infBaixas>
                    </Baixas>
                """

                _logger.debug(f"Generated XML for payment {payment.id}: {file_content}")

                result = self._send_xml(file_content)
                result["payment_id"] = payment.id
                results.append(result)
                _logger.info(f"XML sent for payment {payment.id}, response: {result}")

        return results

    def _prepare_xml_documents(self):
        results = []
        document_fields = [
            self.document_nfe_ids,
            self.document_nfse_ids,
            self.document_nfce_ids,
            self.document_cfe_ids,
            self.document_cfeecf_ids,
            self.document_nfse_ids,
            self.document_rl_ids,
            self.document_cte_ids,
        ]

        for document_field in document_fields:
            for document in document_field:
                if document.dominio_state == "stored":
                    _logger.info(f"Document {document.id} already stored, skipping.")
                    continue
                if document.dominio_state != "stored":
                    xml_file = document.authorization_file_id or document.send_file_id
                    if xml_file and xml_file.datas:
                        file_content = base64.b64decode(xml_file.datas)
                        _logger.info(
                            f"Preparing to send XML for Fiscal Document {document.id}"
                        )
                        result = self._send_xml(file_content)
                        result["document_id"] = document.id
                        results.append(result)

        return results

    def _send_xml(self, file_content):
        """
        Sends the prepared XML data to the Dominio API.

        Args:
            file_content (bytes): The content of the XML file to be sent.

        Raises:
            requests.HTTPError: If there is an issue with the HTTP request.

        Returns:
            dict: The response data from the API, including the document ID.
        """
        try:
            # Obter a URL da API e os dados de integração diretamente dentro do método
            api_url = get_dominio_api_url(self.env)
            url = api_url.get("xml_url")

            # Geração dos dados de integração
            integration_data = self.company_id._generate_key_integration()
            access_token = integration_data.get("access_token")
            integration_key = integration_data.get("integrationKey")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "x-integration-key": integration_key,
            }

            # Estrutura do payload a ser enviado
            data = {
                "file[]": (None, file_content, "application/xml"),
                "query": (
                    None,
                    json.dumps({"boxe/File": self.company_id.dominio_box_e}),
                    "application/json",
                ),
            }

            # Envio da requisição
            response = requests.post(url, headers=headers, files=data)
            response.raise_for_status()

            response_json = response.json()
            _logger.info(f"Successfully sent XML to Dominio API")

            return {
                "integrationKey": integration_key,
                "access_token": access_token,
                "id": response_json.get("id"),
            }

        except requests.HTTPError as e:
            _logger.error(f"Failed to send XML to Dominio API: {e}")
            raise UserError(_("Failed to send XML to Dominio API: %s") % e)

    def _check_send_xml_dominio(self, payment_results=None, document_results=None):
        """
        Checks the status of the XML sent to Dominio for both payments and documents.

        Args:
            payment_results (list): List of payment results to check.
            document_results (list): List of document results to check.

        Raises:
            UserError: If there is an issue with the HTTP request.
        """
        try:
            # Process payment results
            if payment_results:
                for result in payment_results:
                    self._process_result(result, is_document=False)

            # Process document results
            if document_results:
                for result in document_results:
                    self._process_result(result, is_document=True)

            _logger.info("Finished checking XML data sent to Dominio API")

        except requests.HTTPError as e:
            _logger.error(
                "HTTP error occurred while checking XML status with Dominio API: %s", e
            )
            raise UserError(_("Request error: %s") % e) from e

    def _process_result(self, result, is_document):
        """
        Process the result for either a payment or document.

        Args:
            result (dict): The result dictionary containing response data.
            is_document (bool): Whether the result is for a document (True) or a payment (False).
        """
        access_token = result.get("access_token")
        integration_key = result.get("integrationKey")
        id_xml = result.get("id")

        # Check if it's a document or payment
        if is_document:
            record = self.env["l10n_br_fiscal.document"].browse(
                result.get("document_id")
            )
            record_type = "Fiscal Document"
        else:
            record = self.env["account.move.line"].browse(result.get("payment_id"))
            record_type = "Payment"

        if record.dominio_state == "stored":
            _logger.info(f"{record_type} {record.id} already stored, skipping.")
            return

        api_url = get_dominio_api_url(self.env)
        url = api_url.get("xml_url") + f"/{id_xml}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-integration-key": integration_key,
        }
        _logger.info(
            f"Requesting status for {record_type} {record.id} from Dominio API"
        )

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        if response.status_code == 200:
            status_code = response_json["filesExpanded"][0]["apiStatus"]["code"]
            id_transaction = response_json["id"]
            response_msg = response_json["filesExpanded"][0]["apiStatus"]["message"]
            self._check_xml_status(record, status_code, id_transaction, response_msg)
        else:
            _logger.error(f"Request error: status code {response.status_code}")
            raise UserError(_("Request error: %s") % response.status_code)

    def _check_xml_status(self, field, status_code, id_transaction, response_msg):
        """Updates the move line state based on the API response status."""
        if status_code == "SA2":
            field.dominio_transaction = id_transaction
            field.dominio_code = status_code
            field.dominio_response = response_msg
            field.dominio_state = "stored"
            _logger.info(f"Field {field.id} successfully stored in Dominio API")
        elif status_code == "EA10":
            field.dominio_transaction = id_transaction
            field.dominio_code = status_code
            field.dominio_response = response_msg
            field.dominio_state = "stored"
            _logger.warning(f"Field {field.id} already exists in Dominio API")
        else:
            field.dominio_transaction = id_transaction
            field.dominio_code = status_code
            field.dominio_response = response_msg
            field.dominio_state = "error"
            _logger.error(f"Field {field.id} in Dominio API")

    def action_dominio_send(self):
        # Fetch XML sending results for both payments and documents
        payment_results = self._prepare_xml_payments()
        document_results = self._prepare_xml_documents()

        # Check XML response for both payments and documents
        self._check_send_xml_dominio(
            payment_results=payment_results, document_results=document_results
        )

    def action_close(self):
        res = super().action_close()

        fields_to_check = {
            "Fiscal Documents (NFe)": self.document_nfe_ids,
            "Fiscal Documents (NFSe)": self.document_nfse_ids,
            "Fiscal Documents (NFCe)": self.document_nfce_ids,
            "Fiscal Documents (CF-e)": self.document_cfe_ids,
            "Fiscal Documents (CF-e ECF)": self.document_cfeecf_ids,
            "Fiscal Documents (CT-e)": self.document_cte_ids,
            "Incoming Payments": self.incoming_payment_move_line_ids,
            "Outgoing Payments": self.outgoing_payment_move_line_ids,
        }

        not_stored_docs = [
            f"Total for {field_name}: {len(records.filtered(lambda r: r.dominio_state != 'stored'))} not stored(s) in Dominio API"
            for field_name, records in fields_to_check.items()
            if any(records.filtered(lambda r: r.dominio_state != "stored"))
        ]

        if not_stored_docs:
            raise UserError(
                _("Cannot close Fiscal Period:\n\n") + "\n".join(not_stored_docs)
            )

        return res
