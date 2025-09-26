# Copyright 2025 - TODAY, Cristiano Mafra Junior <cristiano.mafra@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import fields, models


class AtmAverbaEvent(models.Model):
    _inherit = "atm.averba.event"

    endorsement_message = fields.Text()

    endorsement_state = fields.Selection(
        selection_add=[
            ("encerrado", "Encerrado"),
        ],
    )

    def create_event_mdfe(  # noqa: C901
        self, document, response, *, cancel=False, close=False
    ):
        resp = response or {}
        numero = resp.get("Numero") or ""
        resp.get("Serie") or ""
        resp.get("Filial") or ""
        declarado = resp.get("Declarado")
        if isinstance(declarado, list):
            declarado_list = declarado
        elif declarado:
            declarado_list = [declarado]
        else:
            declarado_list = []

        d0 = declarado_list[0] if declarado_list else {}
        protocolo = d0.get("Protocolo") or ""
        raw_date = d0.get("dhChancela")

        dh_chancela_dt = None
        if raw_date:
            try:
                dh_chancela_dt = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                try:
                    dh_chancela_dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
        info_obj = (resp.get("Infos") or {}).get("Info")
        if isinstance(info_obj, list):
            infos_list = info_obj
        elif info_obj:
            infos_list = [info_obj]
        else:
            infos_list = []
        erro_obj = (resp.get("Erros") or {}).get("Erro")
        if isinstance(erro_obj, list):
            erros_list = erro_obj
        elif erro_obj:
            erros_list = [erro_obj]
        else:
            erros_list = []

        vals = {
            "company_id": document.company_id.id,
            "document_id": document.id,
            "date": dh_chancela_dt or fields.Datetime.now(),
            "amount": document.amount_total or 0.0,
            "total_insured": document.amount_total or 0.0,
            "document_number": str(numero),
            "protocol_number": str(protocolo),
        }

        if declarado_list:
            vals.update(
                {
                    "endorsement_state": "cancel" if cancel else "encerrado",
                    "endorsement_message": infos_list[0].get("Descricao", "")
                    if infos_list
                    else "",
                }
            )
        else:
            msgs = []
            for i in infos_list:
                if isinstance(i, dict):
                    cod = i.get("Codigo")
                    desc = i.get("Descricao")
                    if cod and desc:
                        msgs.append(f"{cod} - {desc}")
                    elif desc:
                        msgs.append(desc)
                elif isinstance(i, str):
                    msgs.append(i)
            for e in erros_list:
                if isinstance(e, dict):
                    cod = e.get("Codigo")
                    desc = e.get("Descricao")
                    ve = e.get("ValorEsperado")
                    vi = e.get("ValorInformado")
                    base = f"{cod} - {desc}" if cod and desc else (desc or "")
                    if base:
                        if ve or vi:
                            base += f" (Esperado: {ve or '-'} / Informado: {vi or '-'})"
                        msgs.append(base)
                elif isinstance(e, str):
                    msgs.append(e)

            vals.update(
                {
                    "endorsement_state": "error",
                    "error_message": "\n".join(msgs) if msgs else "",
                }
            )

        return super().create(vals)
