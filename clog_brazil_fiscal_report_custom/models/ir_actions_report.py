from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _get_dacte_config(self, tmpLogo, company):
        config = super()._get_dacte_config(tmpLogo, company)
        if company.dacte_display_ibs_cbs:
            config.display_ibs_cbs = True
        return config

    @api.model
    def _get_damdfe_config(self, tmpLogo, company):
        config = super()._get_damdfe_config(tmpLogo, company)
        if company.damdfe_display_origem_destino_prestacao:
            config.display_origem_destino_prestacao = True
        return config
