# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DocumentType(models.Model):
    _inherit = "l10n_br_fiscal.document.type"

    dominio_specie = fields.Char(
        size=8,
    )
