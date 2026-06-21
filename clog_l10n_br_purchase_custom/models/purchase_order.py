# Copyright 2026 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    maintenance_type = fields.Selection(
        selection=[
            ("not_informed", "Not informed"),
            ("accident", "Accident"),
            ("corrective", "Corrective"),
            ("preventive", "Preventive"),
        ],
        default="not_informed",
    )
