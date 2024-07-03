# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Dominio Fiscal",
    "summary": """
        Dominio integration with L10n BR Fiscal Closing""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo",
    "website": "https://github.com/Escodoo/clog-addons",
    "depends": [
        "dominio_base",
        "l10n_br_fiscal_closing",
    ],
    "data": [
        "views/l10n_br_fiscal_document.xml",
        "views/l10n_br_fiscal_closing.xml",
    ],
}
