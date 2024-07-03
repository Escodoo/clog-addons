# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# flake8: noqa: B950

import random

from odoo import _, fields, models

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    SITUACAO_EDOC_AUTORIZADA,
)


class FiscalDocument(models.Model):

    _inherit = "l10n_br_fiscal.document"

    dominio_state = fields.Selection(
        [("stored", "Stored"), ("error", "Error")],
        string="State Dominio",
        readonly=True,
    )
    dominio_transaction = fields.Char(
        readonly=True,
    )
    dominio_code = fields.Char(
        readonly=True,
    )
    dominio_response = fields.Char(
        readonly=True,
    )

    def action_create_xml_static(self):
        for record in self:
            numero = "".join([str(random.randint(0, 9)) for _ in range(14)])
            codigo_verificacao = "".join([str(random.randint(0, 9)) for _ in range(14)])
            xml_content = f"""
            <CompNfse
                xmlns="http://www.abrasf.org.br/nfse.xsd">
                <Nfse versao="1.00">
                    <InfNfse Id="">
                        <Numero>{numero}</Numero>
                        <CodigoVerificacao>{codigo_verificacao}</CodigoVerificacao>
                        <DataEmissao>2024-07-24T07:06:30</DataEmissao>
                        <ValoresNfse>
                            <BaseCalculo>12456.88</BaseCalculo>
                            <Aliquota>2.00</Aliquota>
                            <ValorIss>249.14</ValorIss>
                            <ValorLiquidoNfse>12270.03</ValorLiquidoNfse>
                        </ValoresNfse>
                        <PrestadorServico>
                            <IdentificacaoPrestador>
                                <CpfCnpj>
                                    <Cnpj>08318053000167</Cnpj>
                                </CpfCnpj>
                                <InscricaoMunicipal>204266</InscricaoMunicipal>
                            </IdentificacaoPrestador>
                            <RazaoSocial>Clog Creative Logistics Transportes Ltda</RazaoSocial>
                            <NomeFantasia>CLOG CREATIVE LOGISTICS LTDA</NomeFantasia>
                            <Endereco>
                                <Endereco>Rua Walter Jose Correia
                            </Endereco>
                                <Numero>11</Numero>
                                <Bairro>Sertao do Maruim</Bairro>
                                <CodigoMunicipio>4216602</CodigoMunicipio>
                                <CodigoPais>1058</CodigoPais>
                                <Cep>88122035</Cep>
                            </Endereco>
                            <Contato>
                                <Telefone>(00)0000-3131</Telefone>
                                <Email>teste@teste.com.br</Email>
                            </Contato>
                        </PrestadorServico>
                        <OrgaoGerador>
                            <CodigoMunicipio>3154606</CodigoMunicipio>
                            <Uf>MG</Uf>
                        </OrgaoGerador>
                        <DeclaracaoPrestacaoServico>
                            <InfDeclaracaoPrestacaoServico>
                                <Competencia>2024-07-24</Competencia>
                                <Servico>
                                    <Valores>
                                        <ValorServicos>12456.88</ValorServicos>
                                        <ValorDeducoes>0.00</ValorDeducoes>
                                        <ValorIr>186.85</ValorIr>
                                        <ValorIss>249.14</ValorIss>
                                        <Aliquota>2.00</Aliquota>
                                    </Valores>
                                    <IssRetido>2</IssRetido>
                                    <ItemListaServico>10.09</ItemListaServico>
                                    <CodigoCnae>4619200</CodigoCnae>
                                    <Discriminacao>&#147;Comissão referente à prestação de serviço no mês</Discriminacao>
                                    <CodigoMunicipio>3154606</CodigoMunicipio>
                                    <CodigoPais>1058</CodigoPais>
                                    <ExigibilidadeISS>1</ExigibilidadeISS>
                                    <MunicipioIncidencia>3543402</MunicipioIncidencia>
                                </Servico>
                                <Prestador>
                                    <CpfCnpj>
                                        <Cnpj>08318053000167</Cnpj>
                                    </CpfCnpj>
                                    <InscricaoMunicipal>204266</InscricaoMunicipal>
                                </Prestador>
                                <Tomador>
                                    <IdentificacaoTomador>
                                        <CpfCnpj>
                                            <Cnpj>03684524000137</Cnpj>
                                        </CpfCnpj>
                                    </IdentificacaoTomador>
                                    <RazaoSocial>Nucleo de Estudos Em Projetos e Sistemas Ltda</RazaoSocial>
                                    <Endereco>
                                        <Endereco>Rua Raul Peixoto</Endereco>
                                        <Numero>64</Numero>
                                        <Bairro>Jardim California</Bairro>
                                        <CodigoMunicipio>3543402</CodigoMunicipio>
                                        <Uf>SP</Uf>
                                        <CodigoPais>1058</CodigoPais>
                                        <Cep>14026115</Cep>
                                    </Endereco>
                                    <Contato>
                                        <Telefone>(99)9999-9999</Telefone>
                                    </Contato>
                                </Tomador>
                                <OptanteSimplesNacional>2</OptanteSimplesNacional>
                                <IncentivoFiscal>2</IncentivoFiscal>
                            </InfDeclaracaoPrestacaoServico>
                        </DeclaracaoPrestacaoServico>
                    </InfNfse>
                </Nfse>
            </CompNfse>
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
