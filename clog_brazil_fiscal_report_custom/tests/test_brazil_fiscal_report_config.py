from odoo.tests.common import SavepointCase


class TestBrazilFiscalReportConfig(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.report_model = cls.env["ir.actions.report"]

    def test_dacte_config_respects_company_flag(self):
        # Garantir valor padrão (False)
        self.company.dacte_display_ibs_cbs = False
        config = self.report_model._get_dacte_config(False, self.company)
        self.assertFalse(
            config.display_ibs_cbs,
            "display_ibs_cbs deve ser False quando o campo da empresa está desmarcado.",
        )

        # Quando marcado, deve ativar a flag no config
        self.company.dacte_display_ibs_cbs = True
        config = self.report_model._get_dacte_config(False, self.company)
        self.assertTrue(
            config.display_ibs_cbs,
            "display_ibs_cbs deve ser True quando o campo da empresa está marcado.",
        )

    def test_damdfe_config_respects_company_flag(self):
        # Garantir valor padrão (False)
        self.company.damdfe_display_origem_destino_prestacao = False
        config = self.report_model._get_damdfe_config(False, self.company)
        self.assertFalse(
            config.display_origem_destino_prestacao,
            (
                "display_origem_destino_prestacao deve ser False quando o campo da "
                "empresa está desmarcado."
            ),
        )

        # Quando marcado, deve ativar a flag no config
        self.company.damdfe_display_origem_destino_prestacao = True
        config = self.report_model._get_damdfe_config(False, self.company)
        self.assertTrue(
            config.display_origem_destino_prestacao,
            (
                "display_origem_destino_prestacao deve ser True quando o campo da "
                "empresa está marcado."
            ),
        )
