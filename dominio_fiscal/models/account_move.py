# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_send_dominio(self):
        self.ensure_one()
        self.fiscal_document_id.action_send_dominio()

    def action_sync_dominio(self):
        self.ensure_one()
        self.fiscal_document_id.action_sync_dominio()
