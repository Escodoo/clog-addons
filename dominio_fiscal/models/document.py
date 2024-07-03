# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    SITUACAO_EDOC_AUTORIZADA,
)


class FiscalDocument(models.Model):

    _inherit = "l10n_br_fiscal.document"

    state_dominio = fields.Selection(
        [("stored", "Stored"), ("duplicated", "Duplicated"), ("error", "Error")],
        string="State Dominio",
        readonly=True,
    )

    def action_create_xml_static(self):
        for record in self:
            xml_content = """
            <CFe>
            <infCFe versao="0.07"
                        versaoDadosEnt="0.07"
                        versaoSB="010000">
                <ide>
                <CNPJ>12345678000123</CNPJ>
                <signAC>AssinaturaAC123</signAC>
                <numeroCaixa>001</numeroCaixa>
                <dataEmissao>2023-05-26T10:00:00-03:00</dataEmissao>
                </ide>
                <emit>
                <CNPJ>08318053000167</CNPJ>
                <IE>123456789</IE>
                <IM>1234567</IM>
                <cRegTrib>0</cRegTrib>
                <indRatISSQN>N</indRatISSQN>
                </emit>
                <dest>
                <CPF>12345678901</CPF>
                <xNome>Cliente Teste</xNome>
                </dest>
                <det nItem="1">
                <!-- Informações sobre o item do CF-e -->
                <prod>
                    <cProd>0001</cProd>
                    <xProd>Produto Teste</xProd>
                    <NCM>12345678</NCM>
                    <CFOP>5102</CFOP>
                    <uCom>UN</uCom>
                    <qCom>1.0000</qCom>
                    <vUnCom>10.00</vUnCom>
                    <vProd>10.00</vProd>
                    <indRegra>A</indRegra>
                </prod>
                </det>
                <total>
                <vCFe>10.00</vCFe>
                <vDesc>0.00</vDesc>
                <vPIS>0.00</vPIS>
                <vCOFINS>0.00</vCOFINS>
                <vOutro>0.00</vOutro>
                <vNF>10.00</vNF>
                <vTroco>0.00</vTroco>
                </total>
                <pgto>
                <MP>
                    <cMP>01</cMP>
                    <vMP>10.00</vMP>
                </MP>
                </pgto>
                <infAdic>
                <infCpl>Informações adicionais do CF-e</infCpl>
                </infAdic>
            </infCFe>
            </CFe>
            """

            event_id = record.event_ids.create_event_save_xml(
                company_id=self.company_id,
                environment=(
                    EVENT_ENV_PROD if record.nfse_environment == "1" else EVENT_ENV_HML
                ),
                event_type="0",
                xml_file="",
                document_id=record,
            )
            record.authorization_event_id = event_id

            record.authorization_event_id.set_done(
                status_code=4,
                response=_("Processado com Sucesso"),
                protocol_date=record.authorization_date,
                protocol_number=record.authorization_protocol,
                file_response_xml=xml_content,
            )
            record._change_state(SITUACAO_EDOC_AUTORIZADA)
        return
