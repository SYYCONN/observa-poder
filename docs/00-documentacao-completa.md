# De Olho na Política — documentação completa

**Atualizada em:** 29/10/2026  
**Status:** fundação local funcional, em validação de produto e design.  
**Ambiente validado:** Docker Compose local, com frontend em `localhost:3001` e API em `localhost:8001`.

Este documento reúne o estado atual do projeto. Ele diferencia o que já existe no código do que continua como planejamento, para evitar que uma tela, um dado de exemplo ou uma integração parcial seja interpretada como cobertura nacional completa.

## 1. Objetivo do produto

O **De Olho na Política** é um portal público para consultar representantes, proposições, tramitações, votações e, em fases futuras, transferências e despesas públicas. O princípio editorial é permitir que cada informação factual seja conferida na fonte oficial, com origem e data de coleta visíveis.

Públicos prioritários:

- cidadãos que querem entender decisões públicas;
- jornalistas e pesquisadores;
- organizações da sociedade civil;
- pessoas que precisam localizar uma matéria, um voto ou um representante.

O produto deve explicar o contexto de uma proposta: o que ela é, qual texto foi publicado, o que muda, quem apresentou, em que etapa está e como cada parlamentar votou quando a fonte publicar o registro nominal.

## 2. Escopo definido

### Primeira cobertura funcional

- deputados federais da Câmara dos Deputados;
- senadores em exercício do Senado Federal;
- proposições e tramitações importadas das fontes oficiais disponíveis;
- votações nominais publicadas;
- autoria, vínculo entre votação e proposição e votos individuais quando publicados;
- páginas públicas de listas e detalhes;
- indicação da fonte oficial e da data de coleta.

### Próximas expansões

- governadores;
- partidos e ocupantes de cargos por partido;
- presidente e ministros de Estado;
- emendas, transferências e despesas públicas;
- deputados estaduais, assembleias, prefeitos e vereadores;
- filtros temáticos e comparações com rastreabilidade documental.

Essas expansões ainda não significam cobertura implementada. Cada nova esfera depende de mapear a fonte, a qualidade do identificador, o histórico disponível e os limites de uso.

### Fora do escopo atual

- rankings de honestidade ou ideologia;
- classificação automática de pessoas como corruptas ou responsáveis por um gasto;
- inferência de voto em votação simbólica ou secreta;
- comentários públicos, rede social, denúncias e uploads;
- cópia integral de PDFs, vídeos e discursos;
- atribuição automática de toda despesa de um órgão a seu ministro ou governante.

## 3. Estado implementado

### Backend

Implementado em Python, FastAPI, SQLAlchemy, Alembic e PostgreSQL:

- health checks de liveness e readiness;
- consulta paginada de parlamentares;
- filtros por nome/ID, UF, partido e fonte;
- detalhe do parlamentar, eleição e mandato quando publicados pela fonte, projetos de autoria identificados e votos nominais agregados;
- consulta de proposições;
- detalhe da proposição com ementa, autores e tramitação;
- consulta de votações;
- detalhe da votação com proposições relacionadas e votos publicados;
- CORS restrito à origem configurada;
- nenhuma rota pública de escrita;
- migrations versionadas;
- histórico de coletas em `import_runs`;
- lock de execução para evitar duas coletas simultâneas do mesmo processo.

### Integrações implementadas

#### Câmara dos Deputados

Fonte principal: [Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/swagger/api.html).

O coletor de deputados consulta a lista oficial, pagina até 100 itens, normaliza identidade, legislatura, UF, partido e URL da fonte, e grava evidência da coleta. A execução é idempotente: repetir a coleta não duplica pessoas nem mandatos.

Também existe coletor inicial de proposições e votações da Câmara, com janela controlada.
Para votos nominais, os anos de 2023 a 2026 foram carregados pelos arquivos anuais oficiais
`votacoes` e `votacoesVotos`; ausências continuam sem inferência de posição. Os próprios
arquivos identificam suplentes e ex-deputados, publicados como registros históricos.

O fechamento provisório da categoria, com cobertura observada, limitações, comandos de
operação e ordem técnica de retomada, está documentado em
[Frente DEPUTADOS](deputados.md).

#### Senado Federal

Fontes principais:

- [Dados Abertos do Senado](https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html);
- [PEC 221/2019 no Senado](https://www25.senado.leg.br/web/atividade/materias/-/materia/174386).

O projeto consulta:

- senadores em exercício;
- processos legislativos recentes;
- detalhes de matérias;
- autores e iniciativa;
- tramitação;
- votações nominais e votos publicados.

Os registros mantêm `source=senado` e o endereço oficial consultado. A PEC 221/2019 é um registro real importado da fonte oficial, com ementa, autoria e eventos de tramitação. Ela não é um dado fictício.

### Coleta automática

O serviço `scheduler` é separado da API HTTP e executa os jobs sem exigir que alguém repita comandos manualmente.

Intervalos padrão:

| Job | Intervalo padrão |
| --- | ---: |
| Deputados atuais da Câmara | 1.440 minutos / 24 horas |
| Perfis e históricos individuais da Câmara | 43.200 minutos / 30 dias |
| Senadores atuais do Senado | 1.440 minutos / 24 horas |
| Legislação recente do Senado | 360 minutos / 6 horas |
| Legislação recente da Câmara | 60 minutos |
| Cota parlamentar da Câmara (CEAP) | 1.440 minutos / 24 horas |
| Votos anuais da Câmara | 10.080 minutos / 7 dias |

O scheduler pode executar uma coleta ao iniciar. As opções ficam no `.env`:

```dotenv
SCHEDULER_ENABLED=true
SCHEDULER_RUN_ON_STARTUP=true
DEPUTIES_IMPORT_INTERVAL_MINUTES=1440
DEPUTY_PROFILES_IMPORT_ENABLED=true
DEPUTY_PROFILES_IMPORT_INTERVAL_MINUTES=43200
SENATORS_IMPORT_INTERVAL_MINUTES=1440
SENATE_LEGISLATION_IMPORT_INTERVAL_MINUTES=360
LEGISLATION_IMPORT_INTERVAL_MINUTES=60
ELECTION_RESULTS_IMPORT_ENABLED=false
ELECTION_RESULTS_YEAR=2022
ELECTION_RESULTS_IMPORT_INTERVAL_MINUTES=525600
```

Falhas deixam o último dado válido disponível e são registradas nos logs e em `import_runs`. O scheduler não publica uma coleta suspeita ou incompleta sem passar pelas validações do job.

Resultados eleitorais nominais são importados do conjunto oficial do TSE por meio do job `tse.election_results`. Como o arquivo histórico é grande, o job fica desativado por padrão e pode ser executado manualmente após a aplicação das migrations:

```bash
docker compose exec backend python -m app.jobs.import_election_results --year 2022
```

O importador considera o primeiro turno, os cargos de senador e deputado federal, agrega os votos por candidato e relaciona o resultado ao parlamentar por UF e nome normalizado. Casos sem correspondência única não são publicados automaticamente.

## 4. Dados e modelo

O banco é PostgreSQL 17 em container Docker. Não há Supabase. O banco não publica a porta para o host no Compose local.

Entidades principais:

| Tabela | Uso |
| --- | --- |
| `parliamentarians` | identidade por fonte e ID externo |
| `mandates` | vínculo observado com legislatura, UF e partido |
| `mandate_observations` | alterações observadas ao longo das coletas |
| `propositions` | tipo, número, ano, ementa e apresentação |
| `authorships` | autoria institucional ou parlamentar |
| `proceedings_events` | tramitação, despacho, situação e relatoria documentada |
| `votings` | objeto, data, resultado e modalidade quando conhecida |
| `voting_propositions` | relação entre votação e proposição |
| `votes` | posição nominal com partido e UF na data do voto |
| `source_records` | URL, hash e versão do normalizador |
| `import_runs` | execução, contagens, status, falhas e duração |

Regras de interpretação:

- nome não é identificador; a união usa fonte e ID externo;
- partido atual não é aplicado retroativamente a um voto antigo;
- autoria, relatoria, orientação partidária e voto são conceitos diferentes;
- ausência de voto publicado não vira voto contrário;
- votação de urgência, emenda, destaque ou requerimento não é apresentada como voto de mérito;
- “barrou” não é um evento de dados: a interface deve informar rejeição, veto, arquivamento, adiamento ou outro evento documentado;
- valores públicos devem separar autorizado, empenhado, liquidado, pago e transferido;
- transferência não prova gasto final e pagamento não prova entrega;
- dado indisponível não vira zero.

### Quantidade observada no ambiente atual

Consulta realizada no PostgreSQL local em 05/11/2026:

- 513 parlamentares atuais da Câmara e 115 registros históricos da 57ª legislatura;
- 81 senadores;
- 96 proposições do Senado;
- 50 votações do Senado.
- 7.581 votações da Câmara no arquivo anual de 2026;
- 128.679 votos nominais da Câmara em 2023;
- 116.400 votos nominais da Câmara em 2024;
- 174.646 votos nominais da Câmara em 2025;
- 50.402 votos nominais da Câmara em 2026;
- 114.198 despesas CEAP da Câmara em 2026, ligadas a 510 deputados.

Esses números são o estado da carga local e podem mudar na próxima coleta. Não representam uma promessa de histórico completo.

## 5. API pública atual

Base local: `http://localhost:8001/api/v1`.

| Método | Endpoint | Parâmetros principais |
| --- | --- | --- |
| GET | `/health/live` | nenhum |
| GET | `/health/ready` | nenhum |
| GET | `/parliamentarians` | `search`, `state`, `party`, `source`, `status`, `limit`, `offset` |
| GET | `/parliamentarians/{id}` | UUID interno |
| GET | `/parliamentarians/{id}/authored-propositions` | autoria paginada |
| GET | `/parliamentarians/{id}/votes` | votos nominais paginados |
| GET | `/parliamentarians/{id}/staff` | equipe nominal paginada |
| GET | `/propositions` | `source`, `limit`, `offset` |
| GET | `/propositions/{id}` | UUID interno |
| GET | `/votings` | `source`, `limit`, `offset` |
| GET | `/votings/{id}` | UUID interno |

`source` aceita `camara` ou `senado`. `limit` vai de 1 a 100; `offset` não pode ser negativo. A documentação interativa está disponível em `http://localhost:8001/docs` somente no ambiente de desenvolvimento.

O endpoint de parlamentares retorna `{ items, total, limit, offset }`. `total` representa o resultado completo após os filtros, e `items` representa apenas a página solicitada. O filtro `status` separa registros `current`, `historical` e `all`; ausentes da lista oficial mais recente são preservados como históricos. O frontend usa páginas de 20 deputados, em duas colunas de até 10 linhas, e páginas de 24 senadores.

Exemplos:

```text
GET /api/v1/parliamentarians?source=camara&state=SP&party=PT
GET /api/v1/parliamentarians?source=senado&search=Simone
GET /api/v1/propositions?source=senado&limit=20
GET /api/v1/votings?source=senado&limit=20
```

## 6. Frontend e experiência atual

Frontend em Next.js, React, TypeScript e Tailwind CSS. Rotas atuais:

| Rota | Conteúdo |
| --- | --- |
| `/` | página inicial e acesso à consulta de deputados |
| `/deputados` | lista e filtros de deputados |
| `/senadores` | lista de senadores |
| `/governadores` | estrutura visual inicial, sem integração completa |
| `/partidos` | estrutura visual inicial, sem cobertura completa |
| `/projetos` | lista de proposições |
| `/proposicoes/{id}` | detalhe com ementa, autores e tramitação |
| `/votacoes` | lista de votações |
| `/votacoes/{id}` | detalhe com totais, partidos e votos publicados |
| `/parlamentares/{id}` | perfil e mandatos observados |

A página de proposição foi reorganizada para apresentar:

- título e ementa em uma hierarquia visual clara;
- tipo da matéria e fonte oficial;
- bloco “O que é”;
- bloco “Texto oficial e mudança proposta”;
- autores;
- linha do tempo de tramitação;
- estados de carregamento, erro e ausência de dados.

A página de perfil parlamentar também apresenta cards separados para:

- resumo do cargo, partido, UF, legislatura e identificador oficial;
- eleição e mandato, com votos nominais do TSE quando houver correspondência exata e única por cargo, UF e nome oficial; nascimento e períodos individuais vêm dos perfis e históricos oficiais da Câmara, sem inferir datas ausentes;
- projetos de autoria identificados e total de votos nominais publicados, sem transformar ausência em zero;
- transparência financeira, com a Cota Parlamentar da Câmara quando houver despesas publicadas, uma referência de subsídio bruto nominal para deputados da Câmara e os demais campos marcados como “não coletado” enquanto suas fontes ainda não estiverem integradas.

A primeira integração financeira importa a Cota para o Exercício da Atividade Parlamentar
(CEAP) anual da Câmara. O perfil mostra quantidade de documentos, valor líquido e glosas,
com ano e fonte. Isso não representa salário, emendas, verbas de outros órgãos ou o custo
total do mandato. Ao clicar em “Ver detalhes da fonte oficial”, o usuário comum vê um
modal com os registros normalizados em linguagem legível: data, categoria, fornecedor,
número do documento, valor líquido, glosa quando houver e link para o documento oficial
individual. Os registros são exibidos em páginas de dez itens, dentro de uma área com
rolagem indicada visualmente. O usuário pode consultar o ano inteiro, um mês, uma data
exata ou um intervalo entre duas datas; o filtro é aplicado no backend e permanece ativo
durante a paginação. Os seletores de período e ano usam o mesmo menu visual dos filtros
de partido e estado. O JSON permanece apenas como formato técnico da API.

A proveniência CEAP `ceap-v3` identifica cada versão do arquivo pelo SHA-256 do JSON
descompactado. O banco guarda o hash e os metadados do arquivo. Uma correção na fonte
gera uma nova evidência mesmo com a mesma contagem de linhas. Os registros de despesas
continuam identificados por exercício e ID do documento. Evidências anteriores permanecem
disponíveis com a versão de normalização original.

Um arquivo inválido, vazio ou com registros de outro exercício deixa a carga anterior
disponível e registra a falha em `import_runs`. Após obter o lock, a próxima execução
marca tentativas abandonadas como `interrupted`. Para reprocessar um exercício, execute
`docker compose exec -T backend python -m app.jobs.import_camara_expenses --year 2026`.

Para deputados da Câmara, o perfil também exibe o subsídio bruto nominal informado na seção
oficial de remuneração. Ele é apresentado como referência institucional, com link para a
fonte e aviso de que descontos, faltas e comparecimento podem alterar o valor efetivamente
recebido. Não é tratado como salário líquido individual nem somado à CEAP. A remuneração
individual por competência, assessores, emendas e verbas são armazenados separadamente da
CEAP.

A folha mensal da Câmara já possui coleta própria. Ela identifica os 513 deputados na lista
oficial, consulta a competência corrente e armazena o valor fixo bruto e a remuneração após
descontos obrigatórios, sempre com o link da folha individual. O agendador repete essa coleta
a cada 30 dias; uma competência sem publicação não é convertida em zero.

A consulta de recursos humanos também possui coleta própria de equipe. Ela identifica os
gabinetes oficiais, consulta os servidores em exercício da categoria “Secretário Parlamentar”
e armazena a quantidade por gabinete, competência da coleta e link oficial da consulta. O
perfil exibe o resumo e uma listagem nominal paginada da competência mais recente, além do
relatório PDF com a mesma proveniência.

A integração de emendas usa o arquivo aberto anual do Portal da Transparência, sem chave de API.
Ela consulta as emendas de autoria por exercício e separa quantidade, empenhado, liquidado e
pago. Emendas de autoria não são apresentadas como emendas recebidas.

Os comprovantes permanecem hospedados pela Câmara: o portal mantém somente o endereço da
fonte e não baixa, armazena, indexa ou reproduz o arquivo. O modal informa que o documento
oficial pode conter dados pessoais publicados pela própria fonte.

O histórico nominal da Câmara usa os arquivos anuais oficiais de votações e votos. Os anos
de 2023 a 2026 estão carregados no ambiente local, incluindo perfis históricos identificados
diretamente pelos campos oficiais dos arquivos. O
perfil mostra somente registros de votos efetivamente publicados; deputado ausente no
arquivo não recebe uma posição inventada. As quatro cargas anuais foram validadas
localmente e não alteraram a VPS.

O design ainda está em revisão. A prioridade definida é legibilidade, responsividade, contraste, espaçamento consistente e explicação clara dos dados. A validação visual deve ser feita em desktop e celular antes de considerar a interface pronta.

## 7. Arquitetura e infraestrutura

```text
frontend/                 Next.js, React, TypeScript e Tailwind
backend/                  FastAPI, SQLAlchemy, Alembic e PostgreSQL
backend/app/integrations/ adaptadores das fontes oficiais
backend/app/jobs/         coletores executáveis
backend/app/modules/      modelos, schemas e serviços por domínio
infra/docker/             Dockerfiles
compose.yaml              ambiente local
docs/                     decisões, escopo e operação
```

Serviços Docker locais:

- `db`: PostgreSQL;
- `backend`: API FastAPI;
- `scheduler`: coletas automáticas;
- `frontend`: aplicação Next.js.

Redes:

- `database`: interna, para banco e serviços que precisam dele;
- `application`: comunicação entre API, scheduler e frontend.

O banco fica isolado na rede interna. API e site são publicados em `127.0.0.1` no ambiente local.

## 8. Como executar

Requisitos:

- Docker Desktop com Compose;
- Node.js 22 apenas para desenvolvimento direto do frontend;
- Python 3.13 apenas para desenvolvimento direto do backend.

Na raiz:

```bash
cp -n .env.example .env
docker compose up -d --build
docker compose ps
```

URLs padrão:

- site: `http://localhost:3000`;
- API: `http://localhost:8000`;
- Swagger: `http://localhost:8000/docs`.

Neste ambiente, as portas usadas são `3001` e `8001` para evitar conflito:

- site: `http://localhost:3001`;
- API: `http://localhost:8001`.

Comandos operacionais:

```bash
docker compose logs -f scheduler
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_deputies
docker compose exec -T scheduler python -m app.jobs.import_senators
docker compose down
```

O comando manual serve para diagnóstico ou carga inicial. A atualização normal é feita pelo scheduler.

## 9. Formatação e validação

Frontend:

```bash
cd frontend
npm ci
npm run typecheck
npm run format:check
npm run build
```

Para formatar:

```bash
npm run format
```

Backend:

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pytest -q
.venv/bin/black --check app tests
```

Validação integrada:

```bash
python3 scripts/test_backend.py
docker compose --env-file .env.example config --quiet
```

Validação realizada nesta atualização:

- API liveness: HTTP 200;
- API readiness: HTTP 200;
- frontend: HTTP 200;
- detalhe da PEC 221/2019: HTTP 200;
- typecheck e Prettier: aprovados;
- build de produção dentro do Docker: aprovado;
- containers locais: saudáveis e ativos.

## 10. Segurança e privacidade

Medidas já aplicadas:

- segredos fora do Git, usando `.env`;
- banco sem porta pública no Compose;
- API local vinculada a `127.0.0.1`;
- CORS limitado à origem do frontend;
- rotas públicas somente de leitura;
- TLS verificado nos clientes das fontes oficiais;
- limites de página, tamanho e tentativas nas coletas;
- advisory lock contra concorrência;
- dados de origem, hash e data de coleta preservados;
- minimização de dados: não persistir CPF, email ou campos pessoais desnecessários.

Antes da produção ainda são necessários:

- Nginx com HTTPS;
- Cloudflare ou proteção de borda equivalente;
- firewall e acesso SSH por chave;
- usuários PostgreSQL separados por função;
- backup externo automático e teste de restauração;
- monitoramento e alertas;
- política de retenção e correção de dados;
- revisão de dependências e de configuração do container.

## 11. VPS Hostinger e custos

Existe uma VPS Hostinger de aproximadamente R$ 80/mês, com 1 vCPU, 4 GB de RAM, 50 GB de disco e 4 TB de banda. Ela atualmente hospeda o Sycon Suite.

O projeto foi desenhado para PostgreSQL em Docker, sem Supabase. Tecnicamente a configuração é suficiente para o MVP e volume inicial moderado, desde que o Sycon Suite seja removido ou isolado e que exista monitoramento de memória, disco e CPU.

O custo mínimo estimado do MVP é:

- VPS: aproximadamente R$ 80/mês;
- domínio: custo anual conforme registrador;
- email transacional: gratuito ou conforme volume;
- analytics: opção sem custo inicial, com privacidade configurada;
- Cloudflare: plano gratuito pode atender a primeira fase.

O custo real cresce com tráfego, armazenamento de documentos, backups, envio de emails e necessidade de separar o projeto do Sycon Suite. Não publicar na VPS antes de definir backup, HTTPS, firewall, logs e plano de recuperação.

## 12. Analytics

Analytics ainda não foi instalado. A decisão recomendada para o MVP é usar uma solução com foco em privacidade, como Plausible, Matomo ou Umami, hospedada ou contratada conforme orçamento.

Métricas úteis:

- acessos por página;
- buscas realizadas;
- filtros usados;
- cliques em fontes oficiais;
- páginas de proposição mais consultadas;
- erros de API;
- tempo de resposta.

Não coletar dados pessoais desnecessários. O analytics deve ter aviso de privacidade e ser compatível com a política do site.

## 13. Deploy futuro

O deploy na VPS ainda não foi realizado. Antes dele:

1. concluir revisão visual e responsiva;
2. validar cobertura e texto de cada fonte;
3. configurar domínio e DNS;
4. criar `.env.prod` fora do Git;
5. instalar Nginx, HTTPS e firewall;
6. configurar backup e restauração;
7. separar o projeto do Sycon Suite;
8. executar migrations e uma carga inicial controlada;
9. verificar logs, health checks e consumo de recursos;
10. só então publicar o endereço público.

## 14. Decisões editoriais obrigatórias

O portal deve:

- informar “fonte oficial” em cada registro;
- mostrar data do evento e data da coleta quando disponíveis;
- distinguir texto oficial de explicação editorial;
- dizer quando a ementa é apenas um resumo;
- manter links para o documento original;
- declarar lacunas de dados;
- preservar correções com histórico e motivo;
- evitar linguagem acusatória ou partidária;
- nunca apresentar dado de demonstração como fato real.

## 15. Próximas etapas recomendadas

### Ordem de execução acordada

1. Concluir a integração legislativa básica: parlamentares, autoria, proposições,
   tramitação e votações já publicadas pelas fontes oficiais.
2. Exibir projetos e votos nos perfis, preservando a origem, a data e a posição
   registrada — etapa concluída na interface atual.
3. Integrar despesas, subsídios, assessores, emendas e verbas, separando
   autorizado, empenhado, liquidado, pago e transferido. A CEAP anual da Câmara e a
   referência nominal de subsídio bruto, folha mensal individual e resumo da equipe em
   exercício para deputados já estão ativas. A integração de emendas usa o arquivo aberto do
   Portal da Transparência, e a equipe nominal já pode ser consultada no perfil. As demais verbas
   seguem como subetapas próprias.
4. Ampliar a cobertura histórica de votos nominais da Câmara. Os anos de 2023 a 2026
   já estão ativos; anos anteriores serão adicionados de forma controlada usando os
   arquivos oficiais `votacoes` e `votacoesVotos`, sem inferir o voto de nenhum deputado.
5. Expandir governadores, municípios, partidos e demais fontes financeiras.

### Produto e design

1. aplicar a skill de UI Design que será incorporada;
2. revisar o sistema visual completo, não apenas uma tela;
3. padronizar tipografia, espaçamento, cards, estados vazios e responsividade;
4. revisar acessibilidade com teclado, contraste e leitores de tela;
5. validar as telas com dados reais.

### Dados

1. ampliar e auditar a carga da Câmara;
2. transformar partidos, governadores e finanças em módulos reais;
3. mapear fontes oficiais estaduais e municipais;
4. definir histórico, correções e reprocessamento.

### Operação

1. instalar analytics com privacidade;
2. configurar observabilidade;
3. preparar produção na VPS separada do Sycon Suite;
4. configurar backups testados;
5. executar revisão de segurança e teste de carga.

## Documentos detalhados

- [Escopo](01-escopo.md)
- [Arquitetura e dados](02-arquitetura-e-dados.md)
- [Custos e analytics](03-custos-e-analytics.md)
- [Segurança e operação](04-seguranca-e-operacao.md)
- [Processo e decisões](05-trabalho-e-decisoes.md)
- [Câmara e modelagem](06-camara-e-modelagem.md)
- [Interface e API pública](07-interface-e-api-publica.md)
