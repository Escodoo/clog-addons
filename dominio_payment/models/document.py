# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FiscalDocument(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def _dominio_send_paid_baixas(self):
        """Send the baixas of every paid invoice linked to these documents."""
        for document in self:
            if document.state_dominio not in ("stored", "duplicated"):
                continue
            invoices = self.env["account.move"].search(
                [("fiscal_document_id", "=", document.id)]
            )
            for invoice in invoices:
                if invoice.payment_state not in ("paid", "in_payment"):
                    continue
                try:
                    invoice.action_send_dominio_baixa()
                except UserError as e:
                    _logger.warning(
                        "Could not auto-send baixa for invoice %s: %s", invoice.id, e
                    )

    def action_send_dominio(self):
        res = super().action_send_dominio()
        # Once the fiscal document is stored in Dominio, automatically send the
        # payment settlements (baixas) for the invoice if it is already paid.
        self._dominio_send_paid_baixas()
        return res
