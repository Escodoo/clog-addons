# Copyright 2025 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import sql

from odoo import fields, models, tools


class FleetReport(models.Model):
    _inherit = "fleet.vehicle.cost.report"

    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        query = """
WITH service_costs AS (
    SELECT
        ve.id AS vehicle_id,
        ve.company_id AS company_id,
        ve.name AS name,
        ve.driver_id AS driver_id,
        se.vendor_id AS partner_id,
        ve.fuel_type AS fuel_type,
        date(date_trunc('month', d)) AS date_start,
        COALESCE(sum(se.amount), 0) AS cost,
        'service' AS cost_type
    FROM fleet_vehicle ve
    CROSS JOIN generate_series(
        (SELECT min(date) FROM fleet_vehicle_log_services),
        CURRENT_DATE + '1 month'::interval,
        '1 month'
    ) d
    LEFT JOIN fleet_vehicle_log_services se
        ON se.vehicle_id = ve.id
        AND date_trunc('month', se.date) = date_trunc('month', d)
    WHERE ve.active
        AND se.active
        AND se.state != 'cancelled'
    GROUP BY
        ve.id,
        ve.company_id,
        ve.name,
        ve.driver_id,
        se.vendor_id,
        ve.fuel_type,
        date_start,
        d
),

contract_costs AS (
    SELECT
        ve.id AS vehicle_id,
        ve.company_id AS company_id,
        ve.name AS name,
        ve.driver_id AS driver_id,
        COALESCE(
            co.insurer_id,
            cod.insurer_id,
            com.insurer_id,
            coy.insurer_id
        ) AS partner_id,
        ve.fuel_type AS fuel_type,
        date(date_trunc('month', d)) AS date_start,
        (
            COALESCE(sum(co.amount), 0)
            + COALESCE(
                sum(
                    cod.cost_generated * extract(
                        day FROM least(
                            date_trunc('month', d) + interval '1 month',
                            cod.expiration_date
                        ) - greatest(
                            date_trunc('month', d),
                            cod.start_date
                        )
                    )
                ), 0
            )
            + COALESCE(sum(com.cost_generated), 0)
            + COALESCE(sum(coy.cost_generated), 0)
        ) AS cost,
        'contract' AS cost_type
    FROM fleet_vehicle ve
    CROSS JOIN generate_series(
        (SELECT min(acquisition_date) FROM fleet_vehicle),
        CURRENT_DATE + '1 month'::interval,
        '1 month'
    ) d
    LEFT JOIN fleet_vehicle_log_contract co
        ON co.vehicle_id = ve.id
        AND date_trunc('month', co.date) = date_trunc('month', d)
    LEFT JOIN fleet_vehicle_log_contract cod
        ON cod.vehicle_id = ve.id
        AND date_trunc('month', cod.start_date) <= date_trunc('month', d)
        AND date_trunc('month', cod.expiration_date) >= date_trunc('month', d)
        AND cod.cost_frequency = 'daily'
    LEFT JOIN fleet_vehicle_log_contract com
        ON com.vehicle_id = ve.id
        AND date_trunc('month', com.start_date) <= date_trunc('month', d)
        AND date_trunc('month', com.expiration_date) >= date_trunc('month', d)
        AND com.cost_frequency = 'monthly'
    LEFT JOIN fleet_vehicle_log_contract coy
        ON coy.vehicle_id = ve.id
        AND date_trunc('month', coy.date) = date_trunc('month', d)
        AND date_trunc('month', coy.start_date) <= date_trunc('month', d)
        AND date_trunc('month', coy.expiration_date) >= date_trunc('month', d)
        AND coy.cost_frequency = 'yearly'
    WHERE ve.active
    GROUP BY
        ve.id,
        ve.company_id,
        ve.name,
        ve.driver_id,
        partner_id,
        ve.fuel_type,
        date_start,
        d
)

SELECT
    vehicle_id AS id,
    company_id,
    vehicle_id,
    name,
    driver_id,
    partner_id,
    fuel_type,
    date_start,
    cost,
    cost_type
FROM service_costs

UNION ALL

SELECT
    vehicle_id AS id,
    company_id,
    vehicle_id,
    name,
    driver_id,
    partner_id,
    fuel_type,
    date_start,
    cost,
    cost_type
FROM contract_costs
"""

        self.env.cr.execute(
            sql.SQL("CREATE OR REPLACE VIEW {} AS ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query),
            )
        )
