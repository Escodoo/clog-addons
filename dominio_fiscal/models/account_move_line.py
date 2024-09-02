# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    dominio_state = fields.Selection(
        [("stored", "Stored"), ("error", "Error")],
        string="State Dominio",
        readonly=True,
    )
    dominio_transaction = fields.Char(
        readonly=True,
    )
    dominio_code = fields.Char(
        readonly=True,
    )
    dominio_response = fields.Char(
        readonly=True,
    )
