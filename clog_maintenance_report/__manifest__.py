# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "CLOG Maintenance Report",
    "summary": """Extended maintenance requests report
        with fleet information and equipment cost.""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Maintenance",
    "author": "CLOG, Escodoo",
    "website": "https://github.com/Escodoo/clog-addons",
    "depends": ["maintenance"],
    "data": [
        "views/maintenance_equipment_views.xml",
        "views/maintenance_request_views.xml",
    ],
    "installable": True,
}
