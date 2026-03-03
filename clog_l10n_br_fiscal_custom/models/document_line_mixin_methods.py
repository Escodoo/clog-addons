# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin.methods"

    def _get_fiscal_partner(self):
        """
        Returns the fiscal partner by searching all many2one
        fields for a related document
        with partner_shipping_id or partner_id.
        """
        self.ensure_one()
        for field in self._fields.values():
            if field.type == "many2one":
                doc = getattr(self, field.name, False)
                if doc:
                    partner = getattr(doc, "partner_shipping_id", False)
                    if partner:
                        return partner
        return super()._get_fiscal_partner()
