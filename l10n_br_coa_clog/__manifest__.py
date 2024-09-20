# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "CLOG - Plano de Contas",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Escodoo, Odoo Community Association (OCA)",
    "website": "https://github.com/Escodoo/clog-addons",
    "depends": ["l10n_br_coa"],
    "data": [
        "data/clog_coa_template.xml",
        "data/account_group.xml",
        "data/account.account.template.csv",
        "data/l10n_br_coa.account.tax.group.account.template.csv",
        "data/account_fiscal_position_template.xml",
        "data/clog_coa_template_post.xml",
    ],
    "post_init_hook": "post_init_hook",
}
