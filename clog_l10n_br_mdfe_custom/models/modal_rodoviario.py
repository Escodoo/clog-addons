# Copyright 2025 Escodoo, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields

from odoo.addons.spec_driven_model.models import spec_models


class MDFeModalRodoviarioVeiculoCondutor(spec_models.SpecModel):
    _inherit = "l10n_br_mdfe.modal.rodoviario.veiculo.condutor"

    mdfe_motorista = fields.Many2one(
        comodel_name="res.partner",
        string="Motorista",
        domain=[("tms_type", "=", "driver")],
    )

    @api.onchange("mdfe_motorista")
    def _onchange_mdfe_motorista(self):
        if self.mdfe_motorista:
            self.mdfe30_xNome = self.mdfe_motorista.name
            self.mdfe30_CPF = self.mdfe_motorista.cnpj_cpf_stripped
        else:
            self.mdfe30_xNome = False
            self.mdfe30_CPF = False


class MDFeModalRodoviarioReboque(spec_models.SpecModel):
    _inherit = "l10n_br_mdfe.modal.rodoviario.reboque"

    mdfe_veiculo_reboque = fields.Many2one(
        comodel_name="fleet.vehicle", string="Veículo Reboque"
    )

    @api.onchange("mdfe_veiculo_reboque")
    def _onchange_mdfe_veiculo_reboque(self):
        if self.mdfe_veiculo_reboque:
            self.mdfe30_cInt = self.mdfe_veiculo_reboque.reference
            self.mdfe30_placa = self.mdfe_veiculo_reboque.license_plate
            self.mdfe30_RENAVAM = self.mdfe_veiculo_reboque.renavam
            self.mdfe30_tpCar = self.mdfe_veiculo_reboque.mdfe30_tpCar
            self.mdfe30_UF = self.mdfe_veiculo_reboque.vehicle_state_id.code
            self.mdfe30_tara = self.mdfe_veiculo_reboque.mdfe30_tara
            self.mdfe30_capKG = self.mdfe_veiculo_reboque.mdfe30_capKG
            self.mdfe30_capM3 = self.mdfe_veiculo_reboque.mdfe30_capM3
        else:
            self.mdfe30_cInt = False
            self.mdfe30_placa = False
            self.mdfe30_RENAVAM = False
            self.mdfe30_tpCar = False
            self.mdfe30_UF = False
            self.mdfe30_tara = False
            self.mdfe30_capKG = False
            self.mdfe30_capM3 = False
