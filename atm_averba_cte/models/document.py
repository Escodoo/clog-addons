# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

import requests
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

CTE_NS = "http://www.portalfiscal.inf.br/cte"
NS = {"cte": CTE_NS}


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    atm_averba_event_ids = fields.Many2many(
        comodel_name="atm.averba.event",
        string="AT&M Averba Events",
        compute="_compute_atm_averba_event_ids",
        readonly=True,
    )
    atm_averba_endorsement_state = fields.Selection(
        [("endorsed", "Endorsed"), ("error", "Error"), ("cancel", "Cancel")],
        string="AT&M Averba Endorsement State",
        compute="_compute_atm_averba_endorsement_state",
        readonly=True,
        default=False,
    )
    atm_averba_date_send = fields.Datetime(
        string="AT&M Averba Date Send",
        compute="_compute_atm_averba_date_send",
        readonly=True,
        default=False,
    )

    @api.depends("atm_averba_event_ids", "atm_averba_event_ids.endorsement_state")
    def _compute_insurance_from_events(self):
        for document in self:
            policy = endorsement = False
            events = document.atm_averba_event_ids.sorted("date", reverse=True)
            if events:
                has_cancel = any(ev.endorsement_state == "cancel" for ev in events)
                if not has_cancel:
                    endorsed = next(
                        (ev for ev in events if ev.endorsement_state == "endorsed"),
                        None,
                    )
                    if endorsed:
                        policy = getattr(endorsed, "policy_number", False) or getattr(
                            endorsed, "numero_apolice", False
                        )
                        endorsement = getattr(
                            endorsed, "endorsement_number", False
                        ) or getattr(endorsed, "numero_averbacao", False)
            document.insurance_policy = policy or False
            document.insurance_endorsement = endorsement or False

    @api.depends()
    def _compute_atm_averba_event_ids(self):
        for document in self:
            document.atm_averba_event_ids = self.env["atm.averba.event"].search(
                [("document_id", "=", document.id)],
                order="date desc",
            )

    @api.depends("atm_averba_event_ids")
    def _compute_atm_averba_endorsement_state(self):
        for document in self:
            if document.atm_averba_event_ids:
                last_event = document.atm_averba_event_ids[0]
                states = document.atm_averba_event_ids.mapped("endorsement_state")
                if "endorsed" in states and "cancel" not in states:
                    document.atm_averba_endorsement_state = "endorsed"
                else:
                    document.atm_averba_endorsement_state = last_event.endorsement_state
            else:
                document.atm_averba_endorsement_state = False

    @api.depends("atm_averba_event_ids")
    def _compute_atm_averba_date_send(self):
        for document in self:
            if document.atm_averba_event_ids:
                document.atm_averba_date_send = document.atm_averba_event_ids[0].date
            else:
                document.atm_averba_date_send = False

    def cte_endorsement(self):
        for document in self:
            if (
                document.document_type_id.code == "57"
                and document.atm_averba_endorsement_state not in ("endorsed", "cancel")
            ):
                xml_file = document.authorization_file_id or document.send_file_id
                if xml_file and xml_file.datas:
                    try:
                        env_data = document.company_id.get_atm_averba_environment()
                        token = document.company_id.generate_atm_token()

                        headers = {
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",
                            "Content-Type": "application/xml",
                        }

                        xml_content = base64.b64decode(xml_file.datas).decode("utf-8")
                        url = env_data["url"].rstrip("/")

                        response = requests.post(
                            url=url,
                            headers=headers,
                            data=xml_content,
                            timeout=20,
                        )
                        response.raise_for_status()
                        content = response.json()
                        self.env["atm.averba.event"].create_event(document, content)

                    except requests.RequestException as e:
                        raise UserError(_("Falha ao enviar XML para AT&M: %s") % str(e))

    def build_ret_canc_cte(self, xml_str: str) -> str:
        root = etree.fromstring(xml_str.encode("utf-8"))
        ret = root.find(".//cte:retEventoCTe", namespaces=NS)
        if ret is None:
            raise ValueError("retEventoCTe não encontrado no XML.")

        inf = ret.find("./cte:infEvento", namespaces=NS)
        if inf is None:
            inf = ret.find("./cte:retInfEvento", namespaces=NS)

        def _txt(tag):
            el = inf.find(f"./cte:{tag}", namespaces=NS)
            return (el.text or "").strip() if el is not None else ""

        tpAmb = _txt("tpAmb") or "2"
        cUF = _txt("cOrgao") or "35"
        chCTe = _txt("chCTe")
        dhRegEvento = _txt("dhRegEvento")
        nProt = _txt("nProt")
        xMotivo = _txt("xMotivo")

        retCanc = etree.Element(f"{{{CTE_NS}}}retCancCTe", nsmap={None: CTE_NS})
        retCanc.set("versao", "1.04")
        infCanc = etree.SubElement(retCanc, f"{{{CTE_NS}}}infCanc")
        etree.SubElement(infCanc, f"{{{CTE_NS}}}tpAmb").text = tpAmb
        etree.SubElement(infCanc, f"{{{CTE_NS}}}cUF").text = cUF
        etree.SubElement(infCanc, f"{{{CTE_NS}}}verAplic").text = "99"
        etree.SubElement(infCanc, f"{{{CTE_NS}}}cStat").text = "101"
        etree.SubElement(infCanc, f"{{{CTE_NS}}}xMotivo").text = xMotivo
        etree.SubElement(infCanc, f"{{{CTE_NS}}}chCTe").text = chCTe
        if dhRegEvento:
            etree.SubElement(infCanc, f"{{{CTE_NS}}}dhRecbto").text = dhRegEvento
        if nProt:
            etree.SubElement(infCanc, f"{{{CTE_NS}}}nProt").text = nProt

        return etree.tostring(retCanc, encoding="utf-8", xml_declaration=True).decode(
            "utf-8"
        )

    def cancel_cte_endorsement(self):
        for document in self:
            if (
                document.document_type_id.code == "57"
                and document.state_edoc == "cancelada"
                and document.atm_averba_endorsement_state == "endorsed"
            ):
                cancel_file = document.cancel_file_id
                if cancel_file and cancel_file.datas:
                    try:
                        env_data = document.company_id.get_atm_averba_environment()
                        token = document.company_id.generate_atm_token()

                        headers = {
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",
                            "Content-Type": "application/xml",
                        }

                        xml_content = base64.b64decode(cancel_file.datas).decode(
                            "utf-8"
                        )
                        xml_content = self.build_ret_canc_cte(xml_content)
                        cancel_url = env_data["url"].rstrip("/")

                        response = requests.post(
                            url=cancel_url,
                            headers=headers,
                            data=xml_content,
                            timeout=20,
                        )
                        response.raise_for_status()
                        content = response.json()
                        self.env["atm.averba.event"].create_event(
                            document, content, cancel=True
                        )

                    except requests.HTTPError as e:
                        raise UserError(
                            _("Falha ao enviar cancelamento para AT&M: %s") % e
                        ) from e
