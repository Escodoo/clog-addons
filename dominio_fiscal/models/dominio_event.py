# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class DominioEvent(models.Model):
    _name = "dominio.event"
    _description = "Dominio Event"
    _order = "create_date desc"
    _rec_name = "display_name"

    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Fiscal Document",
        index=True,
        required=True,
        ondelete="cascade",
    )

    event_type = fields.Selection(
        selection=[
            ("token_generation", "Token Generation"),
            ("key_confirmation", "Key Confirmation"),
            ("integration_key", "Integration Key"),
            ("xml_send", "XML Send"),
            ("status_query", "Status Query"),
            ("sync", "Sync"),
        ],
        string="Event Type",
        readonly=True,
    )

    batch_id = fields.Char(
        string="Batch ID",
        readonly=True,
    )

    status_code = fields.Char(
        string="Status Code",
        readonly=True,
    )

    status_description = fields.Text(
        string="API Message",
        readonly=True,
    )

    last_api_status_on = fields.Datetime(
        string="Last API Status On",
        readonly=True,
    )

    boxe_status_code = fields.Char(
        string="Boxe Status Code",
        readonly=True,
    )

    boxe_status_message = fields.Char(
        string="Boxe Status Message",
        readonly=True,
    )

    response_json = fields.Text(
        string="Full API Response",
        readonly=True,
    )

    create_date = fields.Datetime(
        string="Date",
        readonly=True,
        index=True,
    )

    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.create_date:
                parts.append(record.create_date.strftime("%Y-%m-%d %H:%M"))
            if record.event_type:
                parts.append(
                    dict(record._fields["event_type"].selection).get(
                        record.event_type, record.event_type
                    )
                )
            if record.status_code:
                parts.append("[%s]" % record.status_code)
            record.display_name = " - ".join(parts) if parts else str(record.id)
