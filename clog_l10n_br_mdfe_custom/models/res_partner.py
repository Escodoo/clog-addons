# Copyright 2025 Escodoo, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    risk_manager = fields.Many2one(comodel_name="res.partner")
    risk_manager_authorization_number = fields.Char(string="Authorization Number")
    risk_manager_expiration_date = fields.Date(string="Expiration Date")
    risk_manager_profile = fields.Float(string="Profile")
