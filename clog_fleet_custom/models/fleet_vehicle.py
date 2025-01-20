# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicle(models.Model):

    _inherit = "fleet.vehicle"

    reference = fields.Char(
        string="Reference",
    )

    _sql_constraints = [
        ("unique_reference", "unique(reference)", "The reference must be unique!")
    ]
