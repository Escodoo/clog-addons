# Copyright 2024 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from xml.dom import minidom

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Document(models.Model):

    _inherit = "l10n_br_fiscal.document"

    ndd_averba_event_ids = fields.Many2many(
        comodel_name="ndd.averba.event",
        string="NDD Averba Events",
        compute="_compute_ndd_averba_event_ids",
        readonly=True,
    )
    ndd_averba_endorsement_state = fields.Selection(
        [("endorsed", "Endorsed"), ("error", "Error"), ("cancel", "Cancel")],
        string="NDD Averba Endorsement State",
        compute="_compute_ndd_averba_endorsement_state",
        readonly=True,
        default=False,
    )
    ndd_averba_date_send = fields.Datetime(
        string="NDD Averba Date Send",
        compute="_compute_ndd_averba_date_send",
        readonly=True,
        default=False,
    )

    @api.depends()
    def _compute_ndd_averba_event_ids(self):
        for document in self:
            document.ndd_averba_event_ids = self.env["ndd.averba.event"].search(
                [("document_id", "=", document.id)],
                order="date desc",
            )

    @api.depends("ndd_averba_event_ids")
    def _compute_ndd_averba_endorsement_state(self):
        for document in self:
            if document.ndd_averba_event_ids:
                last_event = document.ndd_averba_event_ids[0]
                states = document.ndd_averba_event_ids.mapped("endorsement_state")
                if "endorsed" in states and "cancel" not in states:
                    document.ndd_averba_endorsement_state = "endorsed"
                else:
                    document.ndd_averba_endorsement_state = last_event.endorsement_state
            else:
                document.ndd_averba_endorsement_state = False

    @api.depends("ndd_averba_event_ids")
    def _compute_ndd_averba_date_send(self):
        for document in self:
            if document.ndd_averba_event_ids:
                last_event = document.ndd_averba_event_ids[0]
                document.ndd_averba_date_send = last_event.date
            else:
                document.ndd_averba_date_send = False

    def cte_endorsement(self):
        for document in self:
            if (
                document.document_type_id.code == "57"
                and document.ndd_averba_endorsement_state not in ("endorsed", "cancel")
            ):
                xml_file = document.authorization_file_id or document.send_file_id
                if xml_file and xml_file.datas:
                    try:
                        environment = document.company_id.get_ndd_averba_environment()
                        url = environment["url"] + "/cte/xml"

                        token_data = document.company_id._generate_ndd_averba_token()
                        access_token = token_data.get("token_acesso")

                        headers = {
                            "Authorization": "Bearer " + access_token,
                        }
                        payload = {
                            "xml": xml_file.datas,
                        }

                        response = requests.post(url, headers=headers, data=payload)
                        content = response.json()
                        self.env["ndd.averba.event"].create_event(document, content)

                    except requests.HTTPError as e:
                        raise UserError(
                            _("Failed to send XML to NDD Averba API: %s") % e
                        ) from e

    def cancel_cte_endorsement(self):
        for document in self:
            if (
                document.document_type_id.code == "57"
                and document.state_edoc == "cancelada"
                and document.ndd_averba_endorsement_state == "endorsed"
            ):
                cancel_file_id = document.cancel_file_id
                if cancel_file_id and cancel_file_id.datas:
                    try:
                        environment = document.company_id.get_ndd_averba_environment()
                        url = environment["url"] + "/cte/xml/cancel"

                        token_data = document.company_id._generate_ndd_averba_token()
                        access_token = token_data.get("token_acesso")

                        headers = {
                            "Authorization": "Bearer " + access_token,
                        }
                        payload = {
                            "xml": cancel_file_id.datas,
                        }

                        response = requests.post(url, headers=headers, data=payload)
                        content = response.json()
                        self.env["ndd.averba.event"].create_event(
                            document, content, True
                        )

                    except requests.HTTPError as e:
                        raise UserError(
                            _(
                                "Failed to send cancelation request to NDD Averba API: %s"
                            )
                            % e
                        ) from e

    def ndd_averba_cte_retrieve(self):
        for document in self:
            if document.document_type_id.code == "57" and document.document_key:
                try:
                    environment = document.company_id.get_ndd_averba_environment()
                    url = environment["url"] + f"/cte/{document.document_key}/retrieve"

                    token_data = document.company_id._generate_ndd_averba_token()
                    access_token = token_data.get("token_acesso")

                    headers = {
                        "Authorization": "Bearer " + access_token,
                    }

                    response = requests.get(url, headers=headers)
                    parsed_xml = minidom.parseString(response.content)
                    formatted_xml = parsed_xml.toprettyxml()
                    raise UserError(formatted_xml)

                except requests.HTTPError as e:
                    raise UserError(
                        _("Failed to retrieve XML from NDD Averba API: %s") % e
                    ) from e
