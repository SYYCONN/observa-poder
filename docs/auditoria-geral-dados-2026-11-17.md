# Auditoria geral de dados entre localhost e produção

Data de referência: 17/11/2026, America/Sao_Paulo.

## Escopo e evidências

Esta auditoria compara os domínios de dados de todo o projeto. As contagens locais vieram de transações SQL somente de leitura no PostgreSQL local. As contagens de produção e as últimas execuções foram obtidas por consultas somente de leitura executadas pelo operador na VPS e devolvidas neste chat. Os catálogos públicos foram confrontados por fonte e identificador externo. Os perfis são comparados pelo identificador oficial, porque os UUIDs internos diferem entre ambientes.

O catálogo de produção contém 725 perfis, sendo 644 da Câmara e 81 do Senado. O local contém 709, sendo 628 da Câmara e 81 do Senado. Todos os identificadores locais aparecem no catálogo de produção. Existem 16 identificadores adicionais da Câmara em produção.

Foram lidos os 725 perfis públicos, sem falhas HTTP ao fim das tentativas, e comparados os 709 perfis compartilhados com o ambiente local. As contagens SQL abrangem 41 combinações de área, fonte e período. A verificação HTTP abrangeu 25 rotas ou instâncias equivalentes nos dois ambientes.

As contagens são retratos tomados durante a auditoria. Cargas e alterações concorrentes podem mudar os resultados. As diferenças de volume em despesas e emendas pedem confronto por identificador e competência antes da reposição.

## Inventário de todas as áreas

| Área | Localhost | Produção | Diagnóstico |
| --- | ---: | ---: | --- |
| Deputados em exercício | 513 | 513 | Mesmo conjunto de identificadores. |
| Deputados históricos | 115 | 131 | Produção possui 16 perfis adicionais. |
| Senadores em exercício | 81 | 81 | Mesmo conjunto de identificadores. |
| Resultados eleitorais de 2022 | 643 | 659 | Produção possui maior cobertura total após a carga do TSE. |
| Mandatos com data de início, Câmara | 614 | 565 | Confrontar datas individuais e fonte dos eventos de cada mandato. |
| Proposições da Câmara | 858 | 136 | 853 identificadores só no local, 131 só em produção, 5 compartilhados. |
| Autorias da Câmara | 530 | 20 | Cobertura reduzida afeta as fichas e os projetos de cada deputado. |
| Tramitações da Câmara | 523 | 25 | Cobertura reduzida afeta o histórico das propostas. |
| Proposições do Senado | 636 | 91 | 545 identificadores só no local, 91 compartilhados. |
| Autorias do Senado | 1.149 | 195 | Cobertura reduzida em produção. |
| Tramitações do Senado | 2.012 | 395 | Cobertura reduzida em produção. |
| Votações da Câmara | 42.752 | 43.643 | Produção tem 891 registros adicionais em 2026. |
| Votos individuais da Câmara | 470.127 | 472.436 | Produção tem 2.309 registros adicionais no total. |
| Votações do Senado | 58 | 50 | Oito identificadores só no local, 50 compartilhados. |
| Votos individuais do Senado | 4.524 | 3.900 | Diferença de 624 registros. |
| Equipes de outubro de 2026 | 511 gabinetes | 0 | Competência inteira ausente em produção. |
| Assessores de outubro de 2026 | 9.294 | 0 | Fotografia histórica nominal ausente em produção. |
| Assessores com bruto, líquido e auxílios em outubro | 9.131 em cada campo | 0 | Lacuna financeira confirmada para toda a competência. |
| Equipes de novembro de 2026 | 513 gabinetes | 513 gabinetes | Mesmo volume de gabinetes. |
| Assessores de novembro de 2026 | 9.281 | 9.291 | Fotografias coletadas em datas diferentes. |
| Assessores com valores em novembro | 0 | 0 | As duas bases apresentam a lacuna financeira nesta competência. |
| Folhas de deputados em outubro de 2026 | 513 | 512 | Uma ficha a conferir por identificador e competência. |
| Emendas detalhadas de 2026 | 5.702 | 5.689 | Diferença líquida de 13 registros. Confrontar por identificador. |
| Resumos anuais de emendas de 2026 | 585 parlamentares | 585 parlamentares | Mesmo volume de resumos. |
| Explicações cidadãs persistidas | 0 | 0 | As consultas não retornaram registros nesta tabela em nenhum ambiente. |

### Censo dos campos de perfis

| Campo da Câmara | Localhost, 628 perfis | Produção, 644 perfis | Resultado do confronto por identidade |
| --- | ---: | ---: | --- |
| Nascimento preenchido | 628 | 644 | Sem ausência ou divergência nos 628 perfis compartilhados. |
| Referência de foto preenchida | 628 | 644 | Sem ausência de referência nos perfis compartilhados. A disponibilidade de cada imagem externa não foi testada. |
| Eleição de 2022 associada | 622 | 638 | Todos os vínculos e totais de votos preenchidos no local aparecem com os mesmos valores em produção. |
| Data de início individual | 614 | 565 | 49 datas presentes só no local. |
| Data de fim individual | 147 | 57 | 90 datas presentes só no local e nove divergentes entre valores preenchidos. |
| Remuneração fixa e após descontos, outubro | 513 | 512 | Leonardo Gadelha, ID oficial 122195, tem folha só no local. Os valores dos outros 512 coincidem. |
| Quantidade da equipe mais recente | 513 | 513 | 103 gabinetes com quantidades diferentes nas fotografias de novembro. |
| Resumo de emendas | 510 | 510 | Mesmos perfis com resumo, com diferenças de valores e de quantidade detalhadas na lista de divergências. |
| Algum projeto exibido como autoria | 135 | 8 | A disponibilidade no perfil depende dos registros e dos filtros de identidade da API. |

Nos 81 senadores, as duas APIs têm 21 vínculos eleitorais de 2022 com votos idênticos para os mesmos perfis, 81 referências de foto e 75 resumos de emendas. Ambas deixam nascimento e datas individuais de exercício sem preenchimento neste contrato. O local exibe projetos de autoria para zero senadores, enquanto a produção os exibe para 27. Essa diferença foi investigada no filtro e no formato das chaves de autoria.

Os resumos de emendas têm quantidade diferente em 11 dos 585 perfis com dados nos dois ambientes, valor empenhado diferente em 65, liquidado em 133 e pago em 335. São divergências a reconciliar com a data e a versão da fonte. O resumo da CEAP tem quantidade de documentos diferente em 552 perfis e total líquido diferente em 553. As listas de divergências identificam cada perfil e campo.

### Despesas da CEAP por ano

| Ano | Localhost | Produção | Diferença de produção em relação ao local |
| --- | ---: | ---: | ---: |
| 2023 | 202.392 | 207.514 | +5.122 |
| 2024 | 205.021 | 212.320 | +7.299 |
| 2025 | 188.031 | 192.855 | +4.824 |
| 2026 | 121.131 | 118.480 | −2.651 |

Os números representam documentos persistidos. Os contadores de uma importação também incluem atualizações e linhas repetidas do arquivo de origem, portanto precisam ser interpretados em conjunto com as consultas ao banco.

### Qualidade de projetos e vínculos

A Câmara tem 596 proposições com ano 0 no local e 124 em produção. Esses registros precisam de enriquecimento pela fonte oficial. O ano 0 funciona como sentinela de dado ausente no código e não identifica o exercício real da proposta.

No local, 471 proposições da Câmara possuem data de coleta do detalhe oficial e link para o texto integral. Há 464 com situação preenchida. As 636 proposições do Senado locais não têm situação, texto integral ou data de detalhe oficial preenchidos. Essa lacuna local também precisa entrar na avaliação da integração.

O banco local possui 401 autorias da Câmara vinculadas a perfis entre 530 registros, e 361 do Senado entre 1.149. Os vínculos exigem identidade sustentada pela fonte. As autorias institucionais e as correspondências ambíguas devem conservar seu estado explícito.

Há também uma incompatibilidade entre os registros históricos locais do Senado e o filtro atual da API. Nenhuma das 1.149 autorias locais tem a chave começando por senador:, exigida pelo filtro de identidade e proveniência. Assim, a existência de 361 vínculos no banco não garante que o perfil público apresente esses projetos. A reposição precisa usar o normalizador atual e validar o resultado no endpoint de autoria, além de conferir as tabelas.

## Equipes e folha mensal

A equipe de outubro no local é uma fotografia coletada em 30/10/2026 no horário de Brasília. A lista nominal atual consultada na Câmara representa outro instante. A recuperação histórica deve preservar a fotografia e a data de coleta original.

No exemplo de AJ Albuquerque, o local tem 14 assessores em outubro, todos com valores, e 14 em novembro sem valores. A produção tem 13 em novembro, sem valores, e nenhuma equipe de outubro. O PDF público escolhe a competência mais recente por padrão.

Uma consulta oficial com novembro no endereço retornou HTTP 200 com outubro no cabeçalho da ficha. A correção local preparada valida a competência dentro da resposta. A seleção de competência e o PDF do mês escolhido também estão preparados no workspace, acompanhados de cobertura dos campos e totais condicionados à equipe completa.

## APIs e páginas

Os testes HTTP tiveram os seguintes resultados. As rotas de pessoa foram verificadas com um identificador da Câmara e um do Senado para validar o contrato de acesso.

| Rotas | Localhost | Produção | Interpretação |
| --- | --- | --- | --- |
| /api/v1/parliamentarians, fontes Câmara e Senado | 200 | 200 | Catálogos acessíveis. |
| /api/v1/parliamentarians/parties, fontes Câmara e Senado | 200 | 200 | Filtros de partido acessíveis. |
| /api/v1/parliamentarians/{id} | 200 | 200 | Perfil acessível. Campos dependem da cobertura das cargas. |
| /api/v1/parliamentarians/{id}/financial-expenses | 200 | 200 | Consulta de CEAP acessível. |
| /api/v1/parliamentarians/{id}/staff | 200 | 200 | Consulta nominal acessível. |
| /api/v1/parliamentarians/{id}/authored-propositions | 200 | 200 | Consulta de autoria acessível. |
| /api/v1/parliamentarians/{id}/votes | 200 | 200 | Consulta de votos acessível. |
| /api/v1/propositions e /propositions/search | 200 | 200 | Catálogos legislativos acessíveis. |
| /api/v1/votings e /votings/search | 200 | 200 | Catálogos de votações acessíveis. |
| /docs e /openapi.json | 200 | 404 | A configuração de produção bloqueia a documentação pública. |
| /api/v1/health/live e /health/ready | 200 | 404 | A borda reserva os health checks para o ambiente interno. |
| /api/v1/analytics/summary e /content-admin/citizen-explanations | 404 sem credencial | 404 | Recursos administrativos dependem de habilitação e acesso restrito. |

A navegação pública confirmou a página inicial, as listagens de projetos e votações e uma ficha de proposição. O catálogo público exibe as mesmas contagens das consultas. A pesquisa usa os catálogos de parlamentares, proposições e votações, herdando a cobertura de cada fonte.

Governadores e a página geral de partidos exibem uma consulta em preparação. Os arquivos locais dessas páginas usam SectionPlaceholder. O filtro de partido das listas de parlamentares possui endpoint próprio e funciona em ambos os ambientes.

As integrações atuais de CEAP, equipes e remuneração nominal deste inventário são da Câmara. Os campos correspondentes de senadores permanecem vazios no local e na produção. O modelo e a API atuais também deixam sem nascimento os senadores e não apresentam suas datas individuais de exercício neste cartão.

As explicações cidadãs de projetos têm campos para resumo, impactos, benefícios, custos e análise, mas os bancos consultados não possuem explicações persistidas. As mensagens exibidas no portal vêm dos estados de preparação e dos textos de interface. O workspace contém alterações em andamento nessa frente que precisam passar pela entrega própria.

### Artefatos para a recuperação

As listas completas por identificador estão no diretório output/auditoria-geral-2026-11-17, nos arquivos registros-exclusivos-por-identificador.csv e campos-presentes-local-ausentes-producao.csv. O arquivo campos-com-valores-diferentes.csv identifica as divergências entre valores preenchidos. As contagens por fonte e período estão em contagens-por-fonte-e-periodo.csv. O arquivo cobertura-perfis.json apresenta o censo dos campos públicos por fonte. Os valores locais listados são candidatos a conferência de proveniência antes da reposição.

O censo de perfis verifica os campos disponibilizados pela API. A consulta de disponibilidade verifica cada família de endpoints públicos, com instâncias de detalhe para testar o contrato. As contagens SQL cobrem as tabelas indicadas no inventário. Uma conferência financeira por identificador de cada documento de CEAP e emenda continua necessária para determinar o conjunto exato de inclusões e alterações. A comparação de contagens dessas duas áreas não resolve essa identidade.

## Atualização operacional

Em produção, a última coleta de deputados e senadores ocorreu em 13/11. A legislação recente da Câmara e do Senado também teve a última execução registrada em 13/11. Perfis da Câmara e eleição foram carregados em 17/11, e remuneração em 16/11. O histórico confirma essas execuções pontuais. O estado atual do processo do scheduler e seus sinalizadores precisa ser consultado na VPS para confirmar a rotina futura.

No local, o coletor legislativo da Câmara falhou nas últimas execuções ao consultar a proposição oficial 2649576, que retornou HTTP 404. Essa falha interfere no ciclo de atualização e deve ser tratada antes de usar o job como solução para toda a reposição histórica.

## Plano de solução e prioridades

1. P1 — Recuperar outubro das equipes a partir da fotografia histórica local, conservando fonte, identificador de parlamentar, competência, data de coleta e links oficiais. Ensaiar em PostgreSQL isolado. Inserir a competência ausente em uma transação com contagens verificadas.
2. P1 — Publicar o seletor de competência, o PDF correspondente e a validação da competência recebida da Câmara. Validar outubro e novembro separadamente e conferir a cobertura dos totais.
3. P1 — Adicionar ao coletor legislativo reposição por identificadores oficiais com lotes, tentativas limitadas, backoff, checkpoint e estado explícito para itens indisponíveis na fonte. Preservar o último registro válido em falha. Repor proposições, autores, tramitações e vínculos com votações como uma unidade verificável.
4. P1 — Repor os oito registros de votação do Senado e conferir os votos por identificador de votação e parlamentar. Os 624 votos são a diferença de contagem a investigar.
5. P1 — Reconciliar as 49 datas de início e 90 de fim ausentes, além das nove datas de fim divergentes, pela proveniência dos eventos. Usar eventos individuais de entrada e saída sustentados pela fonte, com referências para cada correção.
6. P2 — Reconciliar CEAP de 2026, emendas e a folha individual de outubro por identificador. Conferir versões e datas das fontes para determinar quais diferenças decorrem de atualização, vínculo e carga incompleta.
7. P1 — Depois das reposições, verificar processo e sinalizadores do scheduler na VPS. Habilitar atualização sequencial de fontes com limites de recursos e alertas para falha, dados antigos e cobertura financeira.
8. P2 — Executar novamente o inventário completo e confrontar os perfis públicos, competências e relatórios exportados com o resultado do ensaio e da carga.

### Critérios e riscos operacionais

| Ação | Ameaça ou falha mitigada | Impacto | Custo operacional | Risco residual | Validação |
| --- | --- | --- | --- | --- | --- |
| Recuperar fotografia histórica com campos explícitos | Perda de contexto temporal e atribuição de valores à equipe errada | Outubro passa a ser consultável com fonte e data | Médio, por ensaio e conferência | A fonte histórica pode ter correções posteriores | Conferir identificadores, competência, quantidades e datas antes e depois |
| Repor legislação por identificador | Catálogos e vínculos incompletos e falha de todo o ciclo por um 404 | Amplia projetos, autoria, tramitação e relações | Médio, por desenvolvimento e consultas oficiais | Registros oficiais podem continuar indisponíveis | Contar incluídos, atualizados, pendentes e falhos por lote e conferir idempotência |
| Validar competência dentro da folha | Associação incorreta entre mês e valores | Publica valores sustentados pelo cabeçalho oficial | Baixo | Meses novos podem continuar sem valores | Simular resposta 200 de outro mês e conferir rejeição dos valores nessa competência |
| Conferir atualização e alertas por coletor | Defasagem silenciosa e sobrecarga da VPS | Mantém a base atualizada com recursos limitados | Médio | Indisponibilidade externa ainda interrompe fontes | Conferir execução, coleta válida, recursos e acionamento do alerta |
| Reconciliar registros por identidade oficial | Duplicação e perda dos registros exclusivos de produção | Preserva a cobertura de ambos os ambientes | Médio | Identidades ausentes ou ambíguas exigem revisão | Conferir chaves naturais, proveniência e campos afetados em ambiente isolado |
