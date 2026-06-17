# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    dominio_baixa_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Dominio Payment Lines",
        compute="_compute_dominio_baixa_line_ids",
        help="Payment lines that reconcile and settle this invoice, used to "
        "send the payment settlement (baixa) to the Dominio API.",
    )

    dominio_payment_state = fields.Selection(
        selection=[
            ("pending", "A Enviar"),
            ("error", "Erro"),
            ("done", "Integrado"),
        ],
        string="Dominio Baixa Status",
        compute="_compute_dominio_payment_state",
        store=True,
        readonly=True,
        copy=False,
        help="Payment settlement (baixa) integration status with Dominio, "
        "aggregated from the reconciled payment lines. Only computed for "
        "invoices whose fiscal document is already stored in Dominio.",
    )

    @api.depends(
        "line_ids.amount_residual",
        "payment_state",
        "fiscal_document_id.state_dominio",
    )
    def _compute_dominio_baixa_line_ids(self):
        for move in self:
            lines = move.env["account.move.line"]
            # Baixas only make sense once the fiscal document is in Dominio.
            if move.is_invoice(
                include_receipts=True
            ) and move.fiscal_document_id.state_dominio in ("stored", "duplicated"):
                for (
                    _partial,
                    _amount,
                    counterpart,
                ) in move._get_reconciled_invoices_partials():
                    lines |= counterpart
            move.dominio_baixa_line_ids = lines

    @api.depends(
        "payment_state",
        "line_ids.amount_residual",
        "fiscal_document_id.state_dominio",
        "dominio_baixa_line_ids.dominio_state",
    )
    def _compute_dominio_payment_state(self):
        for move in self:
            lines = move.dominio_baixa_line_ids
            if not lines:
                move.dominio_payment_state = False
            elif any(line.dominio_state == "error" for line in lines):
                move.dominio_payment_state = "error"
            elif all(line.dominio_state in ("stored", "duplicated") for line in lines):
                move.dominio_payment_state = "done"
            else:
                move.dominio_payment_state = "pending"

    def _dominio_iter_baixa_partials(self):
        """Yield (payment_line, invoice_line, amount) for each settled parcela."""
        self.ensure_one()
        pay_term_lines = self.line_ids.filtered(
            lambda line: line.account_internal_type in ("receivable", "payable")
        )
        for partial in pay_term_lines.matched_debit_ids:
            yield partial.debit_move_id, partial.credit_move_id, partial.amount
        for partial in pay_term_lines.matched_credit_ids:
            yield partial.credit_move_id, partial.debit_move_id, partial.amount

    def action_send_dominio_baixa(self):
        """Send the baixa(s) for every payment that settles this invoice."""
        self.ensure_one()
        document = self.fiscal_document_id
        if not document:
            raise UserError(_("Esta fatura não possui um documento fiscal vinculado."))
        if document.state_dominio not in ("stored", "duplicated"):
            raise UserError(
                _(
                    "Envie o documento fiscal para a Dominio antes de enviar "
                    "a baixa de pagamento."
                )
            )
        access_token, integration_key = document._get_dominio_auth()
        headers = {
            "Authorization": "Bearer %s" % access_token,
            "x-integration-key": integration_key,
        }
        sent = False
        for payment_line, inv_line, amount in self._dominio_iter_baixa_partials():
            payment_line._dominio_send_one_baixa(
                document,
                inv_line.date_maturity,
                payment_line.date,
                amount,
                self,
                headers=headers,
            )
            sent = True
        if not sent:
            raise UserError(
                _("Nenhum pagamento conciliado foi encontrado para esta fatura.")
            )
        # The stored status field depends on the payment lines' state, which is
        # reached through reconciliation and not auto-tracked; refresh it now.
        self._compute_dominio_payment_state()
        return True

    def action_send_dominio_baixa_multi(self):
        """Mass action: send baixas for several invoices without aborting on the
        first error (used by the list view server action)."""
        # dominio_payment_state is only set ("pending"/"error") when the fiscal
        # document is already stored in Dominio and there are payments to send.
        eligible = self.filtered(
            lambda m: m.dominio_payment_state in ("pending", "error")
        )
        for move in eligible:
            try:
                move.action_send_dominio_baixa()
            except UserError as e:
                _logger.warning(
                    "Envio de baixa em massa falhou para a fatura %s: %s",
                    move.id,
                    e,
                )
        return True

    @api.model
    def _cron_send_dominio_baixa(self, limit=None):
        """Daily job: send the baixas of invoices pending integration."""
        moves = self.search([("dominio_payment_state", "=", "pending")], limit=limit)
        if moves:
            _logger.info(
                "Dominio cron: enviando baixas de %s fatura(s) pendente(s)",
                len(moves),
            )
            moves.action_send_dominio_baixa_multi()
        return True
