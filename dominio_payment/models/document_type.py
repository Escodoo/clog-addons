# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DocumentType(models.Model):
    """Fiscal Document Type extension for Dominio payment settlements.

    Maps a fiscal document type to its Dominio "especie" sequential code, used
    to identify the parcela (installment) when sending a baixa to the Dominio
    API. When left empty, the baixa falls back to the "modelo" tag derived from
    the document type code (55 for NF-e, 65 for NFC-e, 03 for NFS-e).
    """

    _inherit = "l10n_br_fiscal.document.type"

    dominio_specie = fields.Char(
        string="Dominio Especie",
        size=6,
        help="Dominio species sequential code used to identify the parcela in "
        "a baixa (payment settlement). See dominio_fiscal species mapping. "
        "If empty, the document type code is used as 'modelo' instead.",
    )
