# Copyright 2025 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsRoute(models.Model):

    _inherit = "tms.route"

    # Verificar.. porque cada um poderia ser uma rota
    clog_region_type = fields.Selection(
        [("hub", "Hub"), ("inland", "Inland"), ("region", "Region")],
        string="Region Type",
        required=True,
    )
    clog_type = fields.Selection(
        [("a", "A"), ("b", "B")], string="Operation Type", required=True
    )
    clog_restricted = fields.Boolean(string="Restricted")
    clog_pickup = fields.Boolean(string="Pickup")
    clog_delivery = fields.Boolean(string="Delivery")
    clog_deadline1 = fields.Integer(string="Deadline 1")
    clog_deadline2 = fields.Integer(string="Deadline 2")
    clog_quantity = fields.Integer(string="Quantity")
    clog_value_td = fields.Float(string="TD Value")
    clog_value_su = fields.Float(string="SU Value")
    clog_value_pickup = fields.Float(string="Pickup Value")
    clog_square = fields.Char(string="Square")
