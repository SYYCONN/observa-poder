# De Olho na Política — proposta inicial

> Histórico da primeira conversa. O planejamento detalhado e o estado das decisões estão no [índice do projeto](../README.md). O usuário posteriormente autorizou a implementação da base local; consulte o índice para o estado atual.

Portal para consultar a atuação política e acompanhar o dinheiro público, com rastreabilidade até os registros oficiais. Documento de planejamento; não representa integrações implementadas.

## Experiência

- Busca por pessoa, cargo, partido, estado, município, projeto e tema.
- Perfil por pessoa e mandato: autoria, relatorias, votações registradas e despesas disponíveis.
- Página de proposição: texto e versões, autores, tramitação, agenda, decisões e votações contextualizadas.
- Painel financeiro: emendas, transferências e despesas por período, território, órgão e finalidade.
- Página de metodologia: cobertura, fontes, atualização e correções.

## Cobertura incremental

1. Câmara dos Deputados: deputados federais, proposições, tramitação e votos nominais. Primeira entrega funcional com busca, perfil e página de projeto.
2. Senado e finanças federais: normalizar dados de senadores, integrar emendas e transferências. Validar autenticação, limites e possibilidade de cruzamento dos registros financeiros.
3. Executivo federal: presidente e ministros de Estado, atos oficiais, vetos e execução por órgão. Não atribuir automaticamente a uma pessoa toda despesa do órgão.
4. Piloto estadual e municipal: selecionar um estado e municípios, mapear assembleia, câmara e portais locais antes de ampliar. Deputados estaduais, governadores e vereadores dependem dessa cobertura.

Ministros de tribunais, caso desejados, precisam de um módulo próprio para decisões judiciais. Não se confundem com ministros de Estado.

## Regras de interpretação

- Registrar o objeto exato da votação. Voto sobre urgência, destaque ou emenda não equivale necessariamente ao voto sobre o mérito do projeto.
- Separar votos favoráveis, contrários, abstenção, ausência, obstrução e indisponibilidade conforme a fonte. Ausência de registro não é voto contrário.
- Mostrar votos individuais somente quando publicados. Não inferir voto em votação simbólica ou secreta.
- Substituir o rótulo genérico “barrou” pelo evento documentado: rejeição, veto, retirada, adiamento, parecer, arquivamento ou outra decisão, com responsável apenas quando identificado na fonte.
- Separar autoria, relatoria, orientação partidária e voto individual.
- Separar previsão orçamentária, empenho, liquidação, pagamento e transferência. Transferência não comprova execução final; pagamento não comprova entrega do objeto.
- Não somar etapas do mesmo gasto. Preservar identificadores para evitar dupla contagem.
- Cruzar emenda, transferência, contrato e pagamento somente quando houver vínculo documental. Exibir lacunas de rastreabilidade.
- Mostrar fonte, data do evento, data da coleta e cobertura em cada registro. Dado indisponível não deve aparecer como zero.
- Manter valores monetários em decimal e datas de negócio em America/Sao_Paulo.

## Arquitetura sugerida

React para interface, FastAPI para consultas, PostgreSQL para dados normalizados e processos agendados para ingestão. Validar hospedagem após uma prova de conceito de coleta, volume e atualização.

Coletores separados por fonte, paginação, retentativas com limite, atualização incremental, armazenamento de registros originais e normalização idempotente. A interface consulta a API própria para reduzir dependência da disponibilidade dos portais oficiais.

Entidades principais: pessoa, mandato, órgão, território, proposição, autoria, evento de tramitação, votação, voto, emenda, transferência, documento de despesa e registro de origem. Preservar histórico de partido e cargo na data do evento.

## Critérios da primeira entrega

- Consultar dados reais da Câmara com origem verificável.
- Encontrar deputado e proposição; navegar entre perfil, autoria e votação.
- Tratar paginação, ausência de dados e falhas da fonte sem inventar registros.
- Exibir descrição da votação junto dos votos.
- Verificar interface em desktop e celular.
- Testar normalização e reingestão sem duplicação, além de conferir uma amostra contra a fonte.

## Fontes oficiais verificadas na pesquisa inicial

- Câmara, documentação da API: https://dadosabertos.camara.leg.br/swagger/api.html
- Senado, documentação da API: https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html
- Senado, votos do senador: https://www12.senado.leg.br/dados-abertos/legislativo/parlamentares/senadores-em-exercicio/info/webservice-de-votacoes-do-senador
- Portal da Transparência, documentação da API: https://api.portaldatransparencia.gov.br/

A presença de endpoints na documentação não equivale a uma integração validada. Ainda faltam chamadas de prova, análise de cobertura histórica, autenticação e limites operacionais.
