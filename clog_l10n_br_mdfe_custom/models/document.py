# Copyright 2025 Escodoo, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Document(models.Model):

    _inherit = "l10n_br_fiscal.document"

    mdfe_veiculo = fields.Many2one(comodel_name="fleet.vehicle", string="Veículo")
    mdfe_destino_prestacao = fields.Many2one(
        comodel_name="res.partner",
        string="Destino Prestação",
    )
    mdfe_nfe_count = fields.Integer(
        string="Total de Notas Fiscais",
        compute="_compute_mdfe_values",
        default=0,
    )
    mdfe_freteCIF = fields.Float(
        string="Valor Frete CIF",
        compute="_compute_mdfe_values",
    )
    mdfe_freteFOB = fields.Float(
        string="Valor Frete FOB",
        compute="_compute_mdfe_values",
    )
    mdfe_freteTERC = fields.Float(
        string="Valor Frete TERC",
        compute="_compute_mdfe_values",
    )
    mdfe_total_merc_averbacao = fields.Float(
        string="Total Mercadoria p/ Averbação",
        compute="_compute_mdfe_values",
    )
    mdfe_total_merc_seguro_proprio = fields.Float(
        string="Total Mercadoria Cliente Seguro Próprio (RCFDC)",
        compute="_compute_mdfe_values",
    )

    @api.onchange("mdfe_veiculo")
    def _onchange_mdfe_veiculo(self):
        if self.mdfe_veiculo:
            self.mdfe30_cInt = self.mdfe_veiculo.reference
            self.mdfe30_placa = self.mdfe_veiculo.license_plate
            self.mdfe30_RENAVAM = self.mdfe_veiculo.renavam
            self.mdfe30_tpCar = self.mdfe_veiculo.mdfe30_tpCar
            self.mdfe30_tpRod = self.mdfe_veiculo.mdfe30_tpRod
            self.rodo_vehicle_state_id = self.mdfe_veiculo.vehicle_state_id
            self.mdfe30_tara = self.mdfe_veiculo.mdfe30_tara
            self.mdfe30_capKG = self.mdfe_veiculo.mdfe30_capKG
            self.mdfe30_capM3 = self.mdfe_veiculo.mdfe30_capM3
        else:
            self.mdfe30_cInt = False
            self.mdfe30_placa = False
            self.mdfe30_RENAVAM = False
            self.mdfe30_tpCar = False
            self.mdfe30_tpRod = False
            self.rodo_vehicle_state_id = False
            self.mdfe30_tara = False
            self.mdfe30_capKG = False
            self.mdfe30_capM3 = False

    @api.onchange("mdfe30_infMunDescarga")
    def _onchange_mdfe30_infMunDescarga(self):
        self.mdfe30_seg = [(5, 0, 0)]
        mdfe_seg_lines = []

        for doc in self.mdfe30_infMunDescarga:
            if doc.document_type == "cte":
                for cte in doc.cte_ids:
                    document = cte.document_related_id
                    vals = {
                        "mdfe30_infResp": document.partner_id,
                        "mdfe30_infSeg": document.partner_insurance_id,
                        "mdfe30_nApol": document.insurance_policy,
                        "mdfe30_nAver": document.insurance_endorsement,
                    }
                    mdfe_seg_lines.append((0, 0, vals))

        self.mdfe30_seg = mdfe_seg_lines

    @api.depends("mdfe30_infMunDescarga")
    def _compute_mdfe_values(self):
        nfe_count = 0
        freteCIF = 0
        freteFOB = 0
        freteTERC = 0
        total_merc_averbacao = 0
        total_merc_seguro_proprio = 0

        for doc in self.mdfe30_infMunDescarga:
            if doc.document_type == "cte":
                for cte in doc.cte_ids:
                    document = cte.document_related_id
                    move_id = document.move_ids[0]

                    nfes = document.document_related_ids.filtered(
                        lambda x: x.document_type_id.code == "55"
                    )
                    nfe_count += len(nfes)

                    incoterm = move_id.invoice_incoterm_id.code
                    if incoterm == "CIF":
                        freteCIF += document.amount_total
                    elif incoterm == "FOB":
                        freteFOB += document.amount_total
                    else:
                        freteTERC += document.amount_total

                    if document.partner_id.mdfe30_respSeg == "1":
                        total_merc_averbacao += document.cte40_vCargaAverb
                    elif document.partner_id.mdfe30_respSeg == "2":
                        total_merc_seguro_proprio += document.cte40_vCargaAverb

        self.mdfe_nfe_count = nfe_count
        self.mdfe_freteCIF = freteCIF
        self.mdfe_freteFOB = freteFOB
        self.mdfe_freteTERC = freteTERC
        self.mdfe_total_merc_averbacao = total_merc_averbacao
        self.mdfe_total_merc_seguro_proprio = total_merc_seguro_proprio
