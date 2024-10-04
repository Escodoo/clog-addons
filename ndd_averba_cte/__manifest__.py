# Copyright 2024 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Ndd Averba Cte",
    "summary": """
        Send CT-e XML to NDD Averba Service""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo",
    "website": "https://github.com/Escodoo/clog-addons",
    "depends": [
        "ndd_averba_base",
        "l10n_br_fiscal_edi",
    ],
    "data": [
        "views/document_view.xml",
        "views/ndd_averba_event.xml",
        "security/ir.model.access.csv",
    ],
}
