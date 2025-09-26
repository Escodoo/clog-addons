# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import fields, models


class AtmAverbaEvent(models.Model):
    _name = "atm.averba.event"
    _description = "AT&M Averba Event"
    _order = "date desc"

    company_id = fields.Many2one("res.company", string="Company")
    document_id = fields.Many2one("l10n_br_fiscal.document", string="Fiscal Document")
    endorsement_state = fields.Selection(
        [("endorsed", "Endorsed"), ("error", "Error"), ("cancel", "Cancel")],
        string="Endorsement State",
        readonly=True,
    )
    error_message = fields.Text(string="Error Message")
    cte_id = fields.Char(string="CT-e ID")
    document_number = fields.Char(string="Document Number")
    date = fields.Datetime(string="Date")
    protocol_number = fields.Char(string="Protocol Number")
    endorsement_number = fields.Char(string="Endorsement Number")
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", store=True, readonly=True
    )
    amount = fields.Monetary(currency_field="currency_id", string="Amount")
    total_insured = fields.Monetary(
        currency_field="currency_id", string="Total Insured"
    )
    insurance_company = fields.Char(string="Insurance Company")
    insurance_company_cnpj = fields.Char(string="Insurance Company CNPJ")
    policy_number = fields.Char(string="Policy Number")

    def create_event(self, document, response, cancel=False):
        dados_seguro = response.get("Averbado", {}).get("DadosSeguro", [{}])[0]
        TpMov = dados_seguro.get("TpMov")
        declarado = response.get("Declarado", {})
        protocolo = declarado.get("Protocolo")
        infos = response.get("Infos", {}).get("Info", [])
        if infos:
            primeira_info = infos[0]
            primeira_info.get("Codigo")
            descricao = primeira_info.get("Descricao")
        infos = response.get("Infos", {}).get("Info", [])

        vals = {
            "company_id": document.company_id.id,
            "document_id": document.id,
            "date": datetime.now(),
        }

        if cancel or TpMov == "2":
            vals.update(
                {
                    "endorsement_state": "cancel",
                    "cte_id": document.authorization_event_id.id,
                    "document_number": response.get("Numero"),
                    "protocol_number": response.get("Averbado", {}).get("Protocolo"),
                    "amount": float(dados_seguro.get("ValorAverbado", 0) or 0),
                    "total_insured": float(dados_seguro.get("ValorAverbado", 0) or 0),
                }
            )
        elif protocolo == "TESTE" or descricao == "Documento ja cadastrado":
            vals.update(
                {
                    "endorsement_state": "endorsed",
                    "cte_id": document.authorization_event_id.id,
                    "document_number": response.get("Numero"),
                    "protocol_number": response.get("Averbado", {}).get("Protocolo"),
                    "amount": float(dados_seguro.get("ValorAverbado", 0) or 0),
                    "total_insured": float(dados_seguro.get("ValorAverbado", 0) or 0),
                }
            )
        elif TpMov == "1":
            vals.update(
                {
                    "endorsement_state": "endorsed",
                    "cte_id": document.authorization_event_id.id,
                    "document_number": response.get("Numero"),
                    "protocol_number": response.get("Averbado", {}).get("Protocolo"),
                    "endorsement_number": dados_seguro.get("NumeroAverbacao"),
                    "amount": float(dados_seguro.get("ValorAverbado", 0)),
                    "total_insured": float(dados_seguro.get("ValorAverbado", 0)),
                    "insurance_company": dados_seguro.get("NomeSeguradora"),
                    "insurance_company_cnpj": dados_seguro.get("CNPJSeguradora"),
                    "policy_number": dados_seguro.get("NumApolice"),
                }
            )
        elif infos:
            error_message = "\n".join(
                f"{info.get('Codigo')}: {info.get('Descricao')}" for info in infos
            )
            vals.update(
                {
                    "endorsement_state": "error",
                    "amount": document.amount_total,
                    "error_message": error_message,
                }
            )
        else:
            vals.update(
                {
                    "endorsement_state": "error",
                    "amount": document.amount_total,
                }
            )

        return super().create(vals)
