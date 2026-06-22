# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DominioEvent(models.Model):
    _inherit = "dominio.event"

    move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Payment Line",
        index=True,
        ondelete="cascade",
        help="Payment move line related to this baixa event, if any.",
    )

    request_xml = fields.Text(
        string="Request XML",
        readonly=True,
        help="XML payload sent to the Dominio API (baixa events).",
    )

    event_type = fields.Selection(
        selection_add=[
            ("baixa_send", "Baixa Send"),
            ("baixa_status", "Baixa Status"),
        ],
        ondelete={"baixa_send": "cascade", "baixa_status": "cascade"},
    )
