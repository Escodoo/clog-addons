# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    coa_generic_tmpl = env.ref("l10n_br_coa_clog.clog_coa_template")
    if env["ir.module.module"].search_count(
        [
            ("name", "=", "l10n_br_account"),
            ("state", "=", "installed"),
        ]
    ):
        # Relate fiscal taxes to account taxes.
        clog_coa_charts = env["account.chart.template"].search(
            [("parent_id", "=", env.ref("l10n_br_coa_clog.clog_coa_template").id)]
        )
        for clog_coa_chart in clog_coa_charts:
            clog_coa_chart.load_fiscal_taxes(env, coa_generic_tmpl)
