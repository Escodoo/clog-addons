# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    pivot_month = fields.Date(
        string="Reference Month",
        compute="_compute_pivot_month",
        store=True,
    )

    maintenance_type = fields.Selection(
        selection_add=[("claim", "Claim"), ("tire", "Tire")],
    )

    fleet_code = fields.Char(
        string="Fleet",
        related="equipment_id.fleet_code",
        store=True,
    )
    year_model = fields.Char(
        string="Year/Model",
        related="equipment_id.year_model",
        store=True,
    )
    license_plate = fields.Char(
        string="License Plate",
        related="equipment_id.license_plate",
        store=True,
    )
    equipment_cost = fields.Float(
        string="Equipment Cost",
        related="equipment_id.cost",
        store=True,
    )

    @api.depends("schedule_date", "request_date")
    def _compute_pivot_month(self):
        for rec in self:
            rec.pivot_month = rec.schedule_date or rec.request_date
