# Copyright 2025 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "ATM Averba MDF-e",
    "summary": """
        Send MDF-e XML to ATM Averba Service""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo",
    "development_status": "Alpha",
    "website": "https://github.com/Escodoo/clog-addons",
    "depends": [
        "atm_averba_cte",
        "l10n_br_fiscal_edi",
    ],
    "data": [
        "views/document_view.xml",
        "security/ir.model.access.csv",
    ],
}
