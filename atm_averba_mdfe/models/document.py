# Copyright 2025 - TODAY, Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

import requests
from lxml import etree

from odoo import _, models
from odoo.exceptions import UserError

from ..constants.atm_averba_mdfe import (
    MDFE_URL,
    NS_MDFE,
    NSMAP_MDFE,
    SOAP12_NS,
    MDFe_NS,
)


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    @staticmethod
    def _parse_xml_bytes(xml_bytes):
        return etree.fromstring(xml_bytes)

    @staticmethod
    def _extract_evento_assinado(evento_xml_bytes):
        root = Document._parse_xml_bytes(evento_xml_bytes)
        if root.tag == f"{{{MDFe_NS}}}eventoMDFe":
            return root
        ev = root.find(f".//{{{MDFe_NS}}}eventoMDFe")
        if ev is None:
            raise ValueError("eventoMDFe não encontrado no XML do evento assinado.")
        return ev

    @staticmethod
    def _extract_ret_evento_from_soap(soap_xml_bytes):
        root = Document._parse_xml_bytes(soap_xml_bytes)
        ret = root.find(f".//{{{MDFe_NS}}}retEventoMDFe")
        if ret is None:
            body = root.find(f".//{{{SOAP12_NS}}}Body")
            if body is not None:
                ret = body.find(f".//{{{MDFe_NS}}}retEventoMDFe")
        if ret is None:
            raise ValueError("retEventoMDFe não encontrado dentro do SOAP.")
        return etree.fromstring(etree.tostring(ret))

    @staticmethod
    def _normalize_nseqevento(xml_elem):
        """Converte <nSeqEvento> para valor sem zeros à esquerda (ex.: '001' -> '1')."""
        for node in xml_elem.xpath(".//mdfe:nSeqEvento", namespaces=NS_MDFE):
            if node.text and node.text.strip().isdigit():
                node.text = str(int(node.text.strip()))

    @staticmethod
    def build_proc_evento_mdfe_v3(evento_xml_bytes, soap_xml_bytes, normalize_seq=True):
        evento = Document._extract_evento_assinado(evento_xml_bytes)
        ret = Document._extract_ret_evento_from_soap(soap_xml_bytes)

        if evento.tag != f"{{{MDFe_NS}}}eventoMDFe":
            raise ValueError("eventoMDFe com namespace inesperado.")
        if ret.tag != f"{{{MDFe_NS}}}retEventoMDFe":
            raise ValueError("retEventoMDFe com namespace inesperado.")

        proc = etree.Element("procEventoMDFe", nsmap=NSMAP_MDFE)
        proc.set("versao", "3.00")

        evento_clone = etree.fromstring(etree.tostring(evento))
        ret_clone = etree.fromstring(etree.tostring(ret))

        if normalize_seq:
            Document._normalize_nseqevento(evento_clone)
            Document._normalize_nseqevento(ret_clone)

        proc[:] = [evento_clone, ret_clone]
        return etree.tostring(
            proc, xml_declaration=True, encoding="utf-8", standalone=False
        )

    def _parse_atm_errors(self, resp):
        try:
            data = resp.json()
        except ValueError:
            data = None

        if isinstance(data, dict):
            erros = (data.get("Erros") or {}).get("Erro")
            if erros:
                if isinstance(erros, dict):
                    erros = [erros]
                msgs = []
                for err in erros:
                    if not isinstance(err, dict):
                        continue
                    codigo = err.get("Codigo")
                    descricao = err.get("Descricao")
                    if codigo and descricao:
                        msgs.append(f"{codigo} - {descricao}")
                    elif descricao:
                        msgs.append(descricao)
                if msgs:
                    return "; ".join(msgs)

        texto = (resp.text or "").strip()
        return texto[:800] if texto else None

    def _post_mdfe_to_atm(self, xml_content, content_type="application/xml"):
        token = self.env.company.generate_atm_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": content_type,
        }
        try:
            resp = requests.post(
                MDFE_URL, headers=headers, data=xml_content, timeout=30
            )
            resp.raise_for_status()
        except requests.HTTPError as e:
            resp = getattr(e, "response", None)
            if resp is not None:
                detalhe = self._parse_atm_errors(resp)
                status = resp.status_code
                if detalhe:
                    raise UserError(_("Erro AT&M (%s): %s") % (status, detalhe))
                raise UserError(_("Erro AT&M (%s).") % status)
            raise UserError(_("Falha HTTP ao enviar XML para AT&M: %s") % str(e))
        except requests.RequestException as e:
            raise UserError(_("Falha ao enviar XML para AT&M: %s") % str(e))

        try:
            return resp.json()
        except ValueError:
            raise UserError(_("Resposta inesperada da AT&M (sem JSON)."))

    def _get_mdfe_event_files(self, document, type_string):
        event = self.env["l10n_br_fiscal.event"].search(
            [("document_id", "=", document.id), ("type", "=", type_string)], limit=1
        )
        if not event:
            raise UserError(_("Não encontrei evento para este documento."))

        if not event.file_request_id:
            raise UserError(
                _("Não encontrei o XML assinado do evento (file_request_id).")
            )
        if not event.file_response_id:
            raise UserError(_("Não encontrei o retorno do evento (file_response_id)."))

        evento_assinado_bytes = base64.b64decode(event.file_request_id.datas or b"")
        soap_bytes = base64.b64decode(event.file_response_id.datas or b"")

        if not evento_assinado_bytes:
            raise UserError(_("XML assinado do evento está vazio."))
        if not soap_bytes:
            raise UserError(_("Retorno (SOAP) do evento está vazio."))

        return evento_assinado_bytes, soap_bytes

    def mdfe_close(self):
        for document in self:
            if document.document_type_id.code != "58":
                continue
            if document.atm_averba_endorsement_state in ("endorsed", "cancel"):
                raise UserError(
                    _(
                        "O MDF-e %s já foi averbado (estado: %s). "
                        "Não é possível enviar novamente."
                    )
                    % (document.display_name, document.atm_averba_endorsement_state)
                )

            evento_assinado_bytes, soap_bytes = self._get_mdfe_event_files(
                document, "15"
            )
            proc_bytes = self.build_proc_evento_mdfe_v3(
                evento_assinado_bytes, soap_bytes, normalize_seq=True
            )
            content = self._post_mdfe_to_atm(proc_bytes, content_type="application/xml")
            self.env["atm.averba.event"].create_event_mdfe(
                document, content, close=True
            )

    def mdfe_cancel(self):
        for document in self:
            if document.document_type_id.code != "58":
                continue
            if document.atm_averba_endorsement_state in ("endorsed", "cancel"):
                raise UserError(
                    _(
                        "O MDF-e %s já foi averbado (estado: %s). "
                        "Não é possível enviar novamente."
                    )
                    % (document.display_name, document.atm_averba_endorsement_state)
                )
            try:
                evento_assinado_bytes, soap_bytes = self._get_mdfe_event_files(
                    document, "2"
                )
            except UserError:
                xml_content = self._get_mdfe_event(document, "2")
                if not xml_content:
                    raise UserError(_("Não encontrei o evento de cancelamento."))
                content = self._post_mdfe_to_atm(
                    xml_content.encode("utf-8"), content_type="application/xml"
                )
                self.env["atm.averba.event"].create_event_mdfe(
                    document, content, cancel=True
                )
                continue
            proc_bytes = self.build_proc_evento_mdfe_v3(
                evento_assinado_bytes, soap_bytes, normalize_seq=True
            )
            content = self._post_mdfe_to_atm(proc_bytes, content_type="application/xml")
            self.env["atm.averba.event"].create_event_mdfe(
                document, content, cancel=True
            )

    def _get_mdfe_event(self, document, type_string):
        event = self.env["l10n_br_fiscal.event"].search(
            [("document_id", "=", document.id), ("type", "=", type_string)], limit=1
        )
        if not event:
            raise UserError(_("Não encontrei evento para este documento."))
        xml_file = event.file_request_id or event.file_response_id
        if not xml_file:
            raise UserError(_("Não encontrei evento para este documento."))
        return base64.b64decode(xml_file.datas).decode("utf-8")
