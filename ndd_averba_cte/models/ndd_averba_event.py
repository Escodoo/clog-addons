# Copyright 2024 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import fields, models


class NddAverbaEvent(models.Model):

    _name = "ndd.averba.event"
    _description = "NDD Averba Event"
    _order = "date desc"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
    )
    document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Fiscal Document",
    )
    endorsement_state = fields.Selection(
        [("endorsed", "Endorsed"), ("error", "Error"), ("cancel", "Cancel")],
        string="Endorsement State",
        readonly=True,
    )
    endorsement_message = fields.Text(string="Endorsement Message")
    error_message = fields.Text(string="Error Message")
    cte_id = fields.Char(string="CTe ID")
    document_number = fields.Char(string="Document Number")
    date = fields.Datetime(string="Date")
    protocol_number = fields.Char(string="Protocol Number")
    endorsement_number = fields.Char(string="Endorsement Number")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
        related="company_id.currency_id",
        store=True,
    )
    amount = fields.Monetary(currency_field="currency_id", string="Amount")
    total_insured = fields.Monetary(
        currency_field="currency_id", string="Total Insured"
    )
    insurance_company = fields.Char(string="Insurance Company")
    insurance_company_cnpj = fields.Char(string="Insurance Company CNPJ")
    policy_number = fields.Char(string="Policy Number")

    def create_event(self, document, response, cancel=False):
        state = response.get("status")
        message = response.get("mensagem")
        errors = response.get("erros")

        vals = {
            "company_id": document.company_id.id,
            "document_id": document.id,
            "endorsement_message": message,
            "date": datetime.now(),
        }

        if state == "sucesso" and cancel:
            vals.update(
                {
                    "endorsement_state": "cancel",
                    "amount": response["averbacoes"][0]["total_segurado"],
                    "total_insured": response["averbacoes"][0]["total_segurado"],
                }
            )
        elif state == "sucesso":
            vals.update(
                {
                    "endorsement_state": "endorsed",
                    "cte_id": response["averbacoes"][0]["cte_id"],
                    "document_number": response["documento"]["numero"],
                    "protocol_number": response["averbacoes"][0]["protocolo"],
                    "endorsement_number": response["averbacoes"][0]["numero_averbacao"],
                    "amount": response["averbacoes"][0]["valor_carga"],
                    "total_insured": response["averbacoes"][0]["total_segurado"],
                    "insurance_company": response["averbacoes"][0]["seguradora_id"],
                    "policy_number": response["averbacoes"][0]["apolice_id"],
                }
            )
        elif state == "erro" and errors:
            vals.update(
                {
                    "endorsement_state": "error",
                    "amount": document.amount_total,
                    "error_message": "\n".join(errors),
                }
            )
        else:
            vals.update(
                {
                    "endorsement_state": "error",
                    "amount": document.amount_total,
                }
            )

        return super(NddAverbaEvent, self).create(vals)
