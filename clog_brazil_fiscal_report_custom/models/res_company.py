from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    dacte_display_ibs_cbs = fields.Boolean(
        string="IBS/CBS",
        default=False,
        help="Selecione para exibir os campos IBS e CBS no DACTE gerado.",
    )

    damdfe_display_origem_destino_prestacao = fields.Boolean(
        string="Origem/Destino da Prestação",
        default=False,
        help=(
            "Selecione para exibir os campos de origem e destino da prestação "
            "no DAMDFE gerado."
        ),
    )
