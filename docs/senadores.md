# Frente SENADORES

Palavra-chave para retomada: **SENADORES**.

## Listagem de 12/11/2026

A lista de senadores adotou o padrão de deputados. São 20 registros por página, em duas colunas no desktop e uma no celular, com busca por nome ou ID, filtros de UF, partido e situação, ação para limpar filtros, data de coleta e navegação para o perfil. O filtro enviado à API continua aplicado durante a paginação. Cada linha abre o perfil, onde está o link oficial. As consultas usam `source=senado`.

## Entrega de 11/11/2026

- A coleta usa a lista oficial em exercício como um snapshot. Após uma coleta válida, quem não aparece passa ao histórico do portal. A identidade, os mandatos observados e a data da última observação são preservados. Uma coleta rejeitada mantém a lista anterior. Uma pessoa que reaparece volta à lista em exercício com o mesmo ID.
- A página permite combinar nome ou ID, UF, partido e situação. Os estados de carregamento, erro de consulta e ausência de registros são anunciados na interface. A listagem usa os parâmetros públicos existentes `source=senado` e `status=current|historical|all`.
- O perfil identifica a legislatura observada e aponta para o histórico individual de mandatos do Senado. As datas de legislatura permanecem na proveniência do snapshot. A API publica datas individuais vazias para esta integração. O perfil oferece o portal de transparência do Senado para consultas de remuneração, cotas e gabinete.
- A vinculação de matéria a um perfil exige o código parlamentar publicado junto com tipo `SENADOR` e Casa `SF`. O detalhe da matéria preserva o autor como publicado. Vínculos legados sem essa confirmação ficam fora do perfil e do link para a pessoa até o reprocessamento do registro oficial.
- Os votos nominais vinculam-se pelo `CodigoParlamentar` do Senado. Posições ausentes e o rótulo legado `registrado` ficam fora da contagem e da lista pública. O perfil exibe o partido da época quando consta no voto. A janela de importação é de até 50 votações nominais do ano corrente por coleta, com preservação das entradas de coletas anteriores.

[API oficial do Senado](https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html) e [documentação da lista em exercício](https://www12.senado.leg.br/dados-abertos/legislativo/composicao-das-comissoes/senadores-em-exercicio/info/webservice-de-senadores-em-exercicio).

A leitura da lista oficial retornou 81 registros com IDs distintos. O navegador verificou lista, filtros combinados de UF e partido, estado vazio histórico, perfil, votação e fontes com a API local e dados reais já coletados. A origem CORS do Compose local é `http://localhost:3001` e a API está em `http://localhost:8001`. A verificação das versões em edição usou portas locais temporárias com origem explicitamente configurada.

Typecheck, build e Compose passaram. A suíte com PostgreSQL isolado validou subida, descida e consistência das migrations e executou 201 testes com sucesso. As regressões verificam histórico e retorno, rejeição de snapshot incompleto, autoria por ID da Casa correta e exclusão de voto nominal sem posição oficial.

O histórico do portal ainda se limita às pessoas e às votações já coletadas. A consulta oficial de mandatos é externa, e o reprocessamento de autorias anteriores depende de a matéria voltar à janela ou de uma importação histórica. Os testes usaram o banco existente apenas para leitura. A aplicação das mudanças aos dados locais ocorrerá após execução dos coletores com a nova versão.

Arquivos alterados neste ciclo:

- `frontend/src/app/senadores/page.tsx` e `frontend/src/app/parlamentares/[id]/page.tsx`.
- `backend/app/jobs/import_senators.py`, `backend/app/jobs/import_senado_legislation.py` e `backend/app/jobs/link_authorships.py`.
- `backend/app/modules/parlamentares/service.py`, `backend/app/api/routes/parliamentarians.py` e `backend/app/api/routes/legislation.py`.
- `backend/tests/integration/test_import_senators.py`, `backend/tests/integration/test_import_legislation.py` e este documento.

## Alterações de 03/11/2026

- Lista `/senadores`: filtro por partido consultado com `source=senado`, filtros aplicados preservados ao paginar, proteção contra respostas concorrentes, estado vazio, erro em português e fontes oficiais nos cartões.
- Coletor de senadores: data de negócio via `local_today()` e rejeição de legislaturas incompatíveis com a data da coleta, sem escolher arbitrariamente a primeira.
- Persistência: limites de legislatura não preenchem datas individuais de exercício. A próxima coleta bem-sucedida limpa essas datas inferidas nos registros processados; histórico de proveniência continua preservado.
- Importador legislativo do Senado: coleções nominais com um registro são normalizadas; timestamps sem fuso usam America/Sao_Paulo e timestamps com fuso preservam o instante original.

## Validações

Typecheck, build e configuração Compose passaram. Pytest com PostgreSQL efêmero passou (78 testes na execução conjunta do workspace). Testes adicionados cobrem data de negócio, legislatura incompatível, conversão de fuso, coleções unitárias e importação idempotente com correção das datas de mandato.

Na repetição final de pytest, com novas alterações simultâneas no workspace: 102 passaram, 17 foram pulados por falta de TEST_DATABASE_URL e 1 falhou no teste do grafo de migrations, pelo mesmo conflito de revisão 0009. Os 8 testes unitários específicos do Senado passaram.

A verificação de migrations pelo script completo encontrou revisão `0009` duplicada e múltiplos heads. O pytest foi executado separadamente no PostgreSQL efêmero, sem alterar migrations ou a base da aplicação.

Interface inspecionada em 390 e 1440 pixels. A API configurada no servidor de desenvolvimento apresentou bloqueio de CORS; o estado vazio e o filtro de partido foram conferidos com respostas locais simuladas. Essa verificação não comprova uma coleta oficial ao vivo.

## Pendências registradas em 03/11/2026

- Resolver os heads de migrations na frente responsável pela base compartilhada.
- Validar a configuração de URL/CORS da API local antes do teste integrado no navegador.
- A lista acumulada não distingue automaticamente senador afastado após deixar de aparecer na coleta. Implementar estado de exercício a partir de snapshots completos, preservando o histórico.
- Datas individuais e histórico completo de exercício exigem fonte específica; a lista atual só comprova a legislatura informada.
- O coletor legislativo mantém janela de 50 votações; totais do perfil referem-se aos registros coletados, não ao histórico integral.

Nenhuma mudança de VPS, segredos, Supabase ou deploy foi realizada.

## Arquivos desta entrega

- `frontend/src/app/senadores/page.tsx`
- `backend/app/integrations/senado/client.py`
- `backend/app/modules/parlamentares/service.py` (somente persistência de senadores)
- `backend/app/jobs/import_senado_legislation.py`
- `backend/tests/test_senado_client.py`
- `backend/tests/test_senado_legislation.py`
- `backend/tests/integration/test_import_senators.py`
- `docs/senadores.md`

Capturas locais em `output/playwright/senadores-mobile.png` e `output/playwright/senadores-desktop.png`.
