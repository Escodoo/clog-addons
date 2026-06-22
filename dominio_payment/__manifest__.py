# Copyright 2026 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Dominio Payment",
    "summary": """
        Dominio integration for payment settlements (baixas de parcelas)""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo",
    "website": "https://github.com/Escodoo/clog-addons",
    "depends": [
        "dominio_fiscal",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/l10n_br_fiscal_document_type.xml",
        "views/account_move.xml",
    ],
}
