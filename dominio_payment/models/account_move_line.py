# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re
from datetime import date, datetime
from xml.etree import ElementTree as ET

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.dominio_fiscal.constants import species_to_document_type

_logger = logging.getLogger(__name__)

DOMINIO_BATCHES_URL = "https://api.onvio.com.br/dominio/invoice/v3/batches"

# Mapping from l10n_br fiscal document type code to Dominio "modelo".
DOMINIO_MODELO_BY_CODE = {
    "55": "55",  # NF-e
    "65": "65",  # NFC-e
    "SE": "03",  # NFS-e
}


class AccountMoveLine(models.Model):
    """Account move line extension for Dominio payment settlements (baixas).

    The customization lives on the payment counterpart lines (the lines that
    reconcile and settle a fiscal invoice). Each such line tracks the
    synchronization state of its baixa with the Dominio API and is able to
    build the baixa XML (by string, following the Dominio layout) and send it.
    """

    _inherit = "account.move.line"

    dominio_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("stored", "Stored"),
            ("duplicated", "Duplicated"),
            ("error", "Error"),
        ],
        string="Dominio Baixa",
        readonly=True,
        copy=False,
    )
    dominio_batch_id = fields.Char(
        string="Dominio Batch ID",
        readonly=True,
        copy=False,
    )
    dominio_code = fields.Char(
        string="Dominio Code",
        readonly=True,
        copy=False,
    )
    dominio_msg = fields.Text(
        string="Dominio Feedback",
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _dominio_only_digits(value):
        return re.sub(r"\D", "", value or "")

    @staticmethod
    def _dominio_fmt_date(value):
        if not value:
            return ""
        if isinstance(value, (date, datetime)):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10]

    def _dominio_tipo_especie_modelo(self, document):
        """Return the (tipo, especie, modelo) tuple for a fiscal document.

        - tipo: "1" entrada, "2" saida, "4" servico.
        - especie: configured Dominio sequential code on the document type.
        - modelo: fallback identification when especie is not configured.
        """
        doc_type = document.document_type_id
        especie = doc_type.dominio_specie or ""

        tipo = ""
        if especie:
            tipo = str(species_to_document_type.get(especie, "") or "")
        if not tipo:
            if doc_type.type == "service":
                tipo = "4"
            elif document.fiscal_operation_type == "in":
                tipo = "1"
            else:
                tipo = "2"

        modelo = ""
        if not especie:
            modelo = DOMINIO_MODELO_BY_CODE.get(document.document_type or "", "")
            if not modelo:
                raise UserError(
                    _(
                        "Não foi possível identificar a parcela para a Dominio. "
                        "Configure o campo 'Dominio Especie' no tipo de documento "
                        "fiscal '%s' ou utilize um documento NF-e/NFC-e/NFS-e."
                    )
                    % (doc_type.name or document.document_type or "")
                )
        return tipo, especie, modelo

    # ------------------------------------------------------------------
    # XML builder (built by string, following the Dominio baixa layout)
    # ------------------------------------------------------------------
    def _dominio_build_baixa_xml(self, document, due_date, pay_date, amount, invoice):
        """Build the baixa (payment settlement) XML for this payment line."""
        self.ensure_one()

        company = document.company_id or invoice.company_id
        tipo, especie, modelo = self._dominio_tipo_especie_modelo(document)

        company_doc = self._dominio_only_digits(company.cnpj_cpf)
        if len(company_doc) not in (11, 14):
            raise UserError(
                _(
                    "A empresa '%s' está sem CNPJ/CPF válido (valor atual: '%s'). "
                    "A baixa exige a inscrição da empresa registrada na Dominio. "
                    "Preencha o CNPJ da empresa em Configurações > Empresas."
                )
                % (company.name, company.cnpj_cpf or "")
            )

        root = ET.Element("Baixas")
        inf_baixas = ET.SubElement(root, "infBaixas", {"versao": "1.00"})
        parcela = ET.SubElement(inf_baixas, "parcela")

        ET.SubElement(
            parcela, "cpf" if len(company_doc) == 11 else "cnpj"
        ).text = company_doc

        ET.SubElement(parcela, "tipo").text = tipo
        if especie:
            ET.SubElement(parcela, "especie").text = especie
        else:
            ET.SubElement(parcela, "modelo").text = modelo
        ET.SubElement(parcela, "serie").text = (document.document_serie or "")[:3]
        ET.SubElement(parcela, "subserie")
        ET.SubElement(parcela, "numero").text = (document.document_number or "")[:15]
        ET.SubElement(parcela, "datavencimento").text = self._dominio_fmt_date(due_date)
        ET.SubElement(parcela, "datapagamento").text = self._dominio_fmt_date(pay_date)
        ET.SubElement(parcela, "valorrecebido").text = "%.2f" % abs(amount or 0.0)
        ET.SubElement(parcela, "juros").text = "0.00"
        ET.SubElement(parcela, "multa").text = "0.00"
        ET.SubElement(parcela, "desconto").text = "0.00"
        ET.SubElement(parcela, "outras").text = "0.00"

        fornecedor = ET.SubElement(parcela, "fornecedor")
        if tipo == "1" and invoice.partner_id:
            fornecedor.text = self._dominio_only_digits(invoice.partner_id.cnpj_cpf)

        historico = (self.name or invoice.name or "")[:200]
        ET.SubElement(parcela, "historico").text = historico
        titulo = (self.ref or invoice.name or "")[:60]
        ET.SubElement(parcela, "titulo").text = titulo

        xml_body = ET.tostring(root, encoding="unicode")
        return '<?xml version="1.0"?>\n' + xml_body

    # ------------------------------------------------------------------
    # API send / status
    # ------------------------------------------------------------------
    def _dominio_check_baixa_status(self, document, batch_id, headers):
        self.ensure_one()
        url = "%s/%s" % (DOMINIO_BATCHES_URL, batch_id)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        check_json = response.json()
        file_expanded = check_json["filesExpanded"][0]
        api_status_code = file_expanded["apiStatus"]["code"]
        api_status_message = file_expanded["apiStatus"].get("message", "")

        if api_status_code == "SA2":
            self.dominio_state = "stored"
            msg = _("Baixa armazenada com sucesso na Dominio. Código: %s, Mensagem: %s")
        elif api_status_code == "EA10":
            self.dominio_state = "duplicated"
            msg = _("Baixa já existe na Dominio. Código: %s, Mensagem: %s")
        else:
            self.dominio_state = "error"
            msg = _("Falha ao processar baixa na Dominio. Código: %s, Mensagem: %s")

        self.dominio_code = api_status_code
        self.dominio_msg = msg % (api_status_code, api_status_message or "N/A")

        self.env["dominio.event"].create(
            {
                "document_id": document.id,
                "move_line_id": self.id,
                "event_type": "baixa_status",
                "batch_id": str(batch_id),
                "status_code": api_status_code,
                "status_description": document._fix_encoding(api_status_message),
                "response_json": document._mask_credentials(
                    json.dumps(check_json, indent=2)
                ),
            }
        )

    def _dominio_send_one_baixa(
        self, document, due_date, pay_date, amount, invoice, headers=None
    ):
        """Build and send a single baixa for this payment line.

        ``headers`` may be provided to reuse an existing Dominio
        authentication and avoid hitting the API rate limit when several
        baixas are sent in a row.
        """
        self.ensure_one()
        xml_content = self._dominio_build_baixa_xml(
            document, due_date, pay_date, amount, invoice
        )
        try:
            if not headers:
                access_token, integration_key = document._get_dominio_auth()
                headers = {
                    "Authorization": "Bearer %s" % access_token,
                    "x-integration-key": integration_key,
                }
            files = {
                "file[]": (None, xml_content.encode("utf-8"), "application/xml"),
                "query": (None, '{"boxe/File": false}', "application/json"),
            }
            _logger.info("Sending baixa for payment line %s to Dominio", self.id)
            response = requests.post(DOMINIO_BATCHES_URL, headers=headers, files=files)
            response.raise_for_status()
            response_json = response.json()
            batch_id = response_json["id"]

            self.dominio_batch_id = str(batch_id)
            self.env["dominio.event"].create(
                {
                    "document_id": document.id,
                    "move_line_id": self.id,
                    "event_type": "baixa_send",
                    "status_code": "SENT",
                    "status_description": "Baixa enviada. Batch ID: %s" % batch_id,
                    "batch_id": str(batch_id),
                    "request_xml": xml_content,
                    "response_json": document._mask_credentials(
                        json.dumps(response_json, indent=2)
                    ),
                }
            )

            self._dominio_check_baixa_status(document, batch_id, headers)
        except requests.HTTPError as e:
            self.dominio_state = "error"
            self.dominio_code = "HTTP"
            self.dominio_msg = _("Falha na comunicação com a API Dominio: %s") % e
            raise UserError(
                _("Falha ao enviar a baixa para a API Dominio: %s") % e
            ) from e

    # ------------------------------------------------------------------
    # Reconciliation navigation
    # ------------------------------------------------------------------
    def _dominio_reconciled_invoice_partials(self):
        """Yield (invoice, invoice_line, amount) tuples this payment settles."""
        self.ensure_one()
        for partial in self.matched_debit_ids:
            if partial.credit_move_id == self:
                yield (
                    partial.debit_move_id.move_id,
                    partial.debit_move_id,
                    partial.amount,
                )
        for partial in self.matched_credit_ids:
            if partial.debit_move_id == self:
                yield (
                    partial.credit_move_id.move_id,
                    partial.credit_move_id,
                    partial.amount,
                )

    def action_dominio_send_baixa(self):
        """Per-line action: send the baixa for the invoice(s) this line settles."""
        affected_invoices = self.env["account.move"]
        for line in self:
            sent = False
            auth_by_document = {}
            for (
                invoice,
                inv_line,
                amount,
            ) in line._dominio_reconciled_invoice_partials():
                if not (invoice.is_invoice() and invoice.fiscal_document_id):
                    continue
                document = invoice.fiscal_document_id
                if document.state_dominio not in ("stored", "duplicated"):
                    raise UserError(
                        _(
                            "Envie o documento fiscal '%s' para a Dominio antes "
                            "de enviar a baixa de pagamento."
                        )
                        % (document.document_number or invoice.name)
                    )
                if document not in auth_by_document:
                    access_token, integration_key = document._get_dominio_auth()
                    auth_by_document[document] = {
                        "Authorization": "Bearer %s" % access_token,
                        "x-integration-key": integration_key,
                    }
                line._dominio_send_one_baixa(
                    document,
                    inv_line.date_maturity,
                    line.date,
                    amount,
                    invoice,
                    headers=auth_by_document[document],
                )
                affected_invoices |= invoice
                sent = True
            if not sent:
                raise UserError(
                    _(
                        "Nenhuma fatura fiscal conciliada foi encontrada para "
                        "esta linha de pagamento."
                    )
                )
        # Refresh the aggregated baixa status on the touched invoices.
        affected_invoices._compute_dominio_payment_state()
        return True
