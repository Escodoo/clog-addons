# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.l10n_br_mdfe_spec.models.v3_0.mdfe_modal_rodoviario_v3_00 import (
    VEICTRACAO_TPCAR,
    VEICTRACAO_TPROD,
)


class FleetVehicle(models.Model):

    _inherit = "fleet.vehicle"

    reference = fields.Char(size=10)
    renavam = fields.Char(string="RENAVAM", size=11)
    vehicle_state_id = fields.Many2one(
        comodel_name="res.country.state",
        domain=[("country_id.code", "=", "BR")],
    )
    mdfe30_tpCar = fields.Selection(
        selection=VEICTRACAO_TPCAR,
        related="model_id.mdfe30_tpCar",
        string="Tipo de Carroceria",
    )
    mdfe30_tpRod = fields.Selection(
        selection=VEICTRACAO_TPROD,
        related="model_id.mdfe30_tpRod",
        string="Tipo do Rodado",
    )
    mdfe30_tara = fields.Char(related="model_id.mdfe30_tara", string="Tara em KG")
    mdfe30_capKG = fields.Char(
        related="model_id.mdfe30_capKG", string="Capacidade em KG"
    )
    mdfe30_capM3 = fields.Char(
        related="model_id.mdfe30_capM3", string="Capacidade em M3"
    )
    risk_manager = fields.Many2one(comodel_name="res.partner")
    risk_manager_authorization_number = fields.Char(string="Authorization Number")
    risk_manager_expiration_date = fields.Date(string="Expiration Date")
    risk_manager_profile = fields.Float(string="Profile")

    _sql_constraints = [
        ("unique_reference", "unique(reference)", "The reference must be unique!")
    ]


class FleetVehicleModel(models.Model):

    _inherit = "fleet.vehicle.model"

    mdfe30_tpCar = fields.Selection(
        selection=VEICTRACAO_TPCAR,
        string="Tipo de Carroceria",
    )
    mdfe30_tpRod = fields.Selection(
        selection=VEICTRACAO_TPROD,
        string="Tipo do Rodado",
    )
    mdfe30_tara = fields.Char(string="Tara em KG", size=6)
    mdfe30_capKG = fields.Char(string="Capacidade em KG", size=6)
    mdfe30_capM3 = fields.Char(string="Capacidade em M3", size=3)
