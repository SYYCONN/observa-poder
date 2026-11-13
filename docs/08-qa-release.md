# QA-RELEASE

Auditoria local executada em 11–12/11/2026 (`America/Sao_Paulo`) com a skill
`de-olho-politica-engineering:qa-release`. **Recomendação: não liberar nem integrar o
candidato atual.** Nenhum deploy ou alteração na VPS foi realizado. Nenhuma falha de
produto foi corrigida nesta frente; apenas este relatório e evidências de QA foram gerados.

## Resumo executivo

| Área | Resultado |
| --- | --- |
| Candidato Git | **Bloqueador:** `main` não possui commits e todo o workspace aparece como não rastreado |
| Frontend typecheck | Passou |
| Frontend build | Passou no host e na imagem Docker com Node 22 |
| Frontend formatação | **Falhou** em 3 arquivos |
| Backend | 206 testes passaram |
| Migrations | Upgrade, check, downgrade até base e novo upgrade passaram em PostgreSQL efêmero |
| Compose | Configuração e build passaram |
| Saúde local | Backend, frontend e banco saudáveis; endpoints live/ready responderam 200 |
| Navegador | Fluxos principais, filtros, paginação, modais, vazio e erro exercitados |
| Responsividade | Sem overflow horizontal nas páginas principais em 390 × 844 |
| Acessibilidade | Heurísticas, skip link, teclado e foco de modais passaram; PDFs não são tagueados |
| Downloads | CSV e PDFs baixaram, mas há conflito entre o limite de exportação e os 3 links da UI |
| PDFs | Conteúdo gerado, porém com sobreposição/corte em cabeçalhos/rodapés e sem tags semânticas |
| Links oficiais | Câmara, Senado, TSE, Portal da Transparência e texto integral responderam |

## Problemas classificados

### Bloqueador

1. **Não existe candidato imutável para integração.** `git status --short --branch`
   retornou `## No commits yet on main`, seguido de todos os arquivos do repositório como
   não rastreados. Não há SHA para revisar, reproduzir, promover ou reverter. Criar e
   revisar um commit candidato, garantindo que segredos, artefatos e arquivos temporários
   não sejam incluídos, é pré-condição para release.

### Alto

1. **Os dois PDFs públicos apresentam falhas visuais de paginação.** No relatório de
   equipe, a página 2 sobrepõe/corta o rodapé e deixa o número de página incompleto. No
   relatório de emendas, há rodapés parcialmente encobertos nas páginas 1 e 3; a página 3
   também inicia a continuação da tabela cortada no topo. O conteúdo permanece em grande
   parte legível, mas a integridade visual do documento não está adequada para publicação.
2. **Os PDFs não possuem tags semânticas.** `pdfinfo` informou `Tagged: no` para equipe e
   emendas. Tabelas, cabeçalhos e ordem de leitura não ficam semanticamente disponíveis
   para tecnologia assistiva. A verificação de acessibilidade HTML não compensa essa falha
   nos artefatos baixáveis.

### Médio

1. **O limite de exportação conflita com a própria interface.** O perfil oferece três
   downloads próximos (PDF da equipe, PDF de emendas e CSV de emendas), enquanto a API usa
   `EXPORT_LIMIT_BURST=2`. Ao baixar os três em sequência, o terceiro respondeu HTTP 429,
   `Retry-After: 9` e JSON `{"detail":"Too many exports"}`. Após aguardar, o CSV baixou
   corretamente. O controle antiabuso funciona, mas interrompe um fluxo normal sem
   tratamento amigável na UI.
2. **A home exibe timestamp técnico em UTC.** O carrossel mostrou texto como
   `Apresentada em 2026-11-11T13:51:00+00:00`, em vez de uma data/hora brasileira para o
   usuário. A origem é `frontend/src/components/institutional-carousel.tsx`, que interpola
   `presented_at` diretamente.
3. **O gate de formatação não está verde.** `npm run format:check` falhou em:
   `src/app/analytics/page.tsx`, `src/app/proposicoes/[id]/page.tsx` e
   `src/app/revisao/projetos/page.tsx`.

### Baixo

1. **Formatação numérica inconsistente em votações.** O cabeçalho mostra `42.752`, mas a
   paginação mostra `42752`.
2. **Data não localizada no detalhe da votação.** Foi exibido `Votação · 2026-11-11`, em
   vez de `11/11/2026`.
3. **Título de página inconsistente.** O detalhe da votação usa `Detalhes da votação` sem
   o sufixo do portal observado nas demais páginas.
4. **Ambiente do host fora da faixa declarada.** `npm ci` funcionou, mas avisou
   `EBADENGINE`: host Node 24.22.2 contra `>=22 <23`. O build na imagem Node 22 passou,
   portanto isso é uma limitação de reprodutibilidade local, não uma falha comprovada do
   produto.

## Resultados detalhados

### Frontend, build e dependências

- `npm ci`: passou; 88 pacotes, 0 vulnerabilidades no audit; aviso de engine do host.
- `npm audit --audit-level=high`: passou, 0 vulnerabilidades conhecidas.
- `npm run typecheck`: passou.
- `npm run build`: passou; 15 rotas Next.js geradas.
- `npm run format:check`: falhou nos 3 arquivos registrados acima.
- Build do serviço `frontend` pelo Compose: passou usando Node 22.

### Backend, testes e migrations

- O script de backend criou PostgreSQL efêmero e executou `alembic upgrade head`,
  `alembic check`, `alembic downgrade base` e novo `upgrade head`: tudo passou.
- Suíte completa: **206 passed in 11.47s**.
- Recorte de migration graph, segurança e normalização legislativa: **34 passed in 0.92s**.
- `pip-audit` contra `requirements-dev.lock`: nenhuma vulnerabilidade conhecida.
- O banco local do Compose estava em `0017 (head)` após `alembic upgrade head`.
- A antiga colisão da revisão `0009` documentada neste arquivo foi resolvida no workspace
  atual e não foi reproduzida.

### Compose e HTTP

- `docker compose --env-file .env.example config --quiet`: passou.
- `docker compose --env-file .env.example build`: passou para frontend, backend e scheduler.
- Backend e frontend foram reconstruídos/recriados localmente; banco e scheduler existentes
  foram preservados. O scheduler não foi reiniciado para evitar disparar coletas externas.
- `/api/v1/health/live`: 200, `{"status":"ok"}`.
- `/api/v1/health/ready`: 200.
- Listas locais retornaram 513 deputados e 81 senadores atuais.

### Navegador, responsividade e estados

Fluxos exercitados em Chromium no desktop e em viewport 390 × 844:

- home, menu mobile e navegação principal;
- deputados e senadores, busca, filtros e paginação;
- perfil parlamentar, links oficiais, despesas, equipe e emendas;
- proposições e votações, listas e detalhes;
- modal de despesas e modal de equipe;
- estado vazio por busca impossível;
- estado de erro com resposta 500 simulada na API;
- paginação de deputados da página 1 para a página 2;
- downloads CSV/PDF e resposta 429.

Não houve overflow horizontal (`document.scrollWidth === 390`) nas 8 páginas-chave
inspecionadas em mobile. O estado vazio apresentou mensagem útil; o erro 500 apresentou
`role=alert` com `Não foi possível carregar os parlamentares.` A única mensagem de erro no
console foi a requisição 500 simulada deliberadamente.

### Acessibilidade de interface

Heurística aplicada à home, listas, perfil parlamentar e detalhes legislativos:

- `lang=pt-BR` presente;
- um `main` e um `h1` por página;
- nenhuma imagem visível sem `alt`;
- nenhum controle visível sem nome acessível na heurística utilizada;
- nenhum `id` duplicado;
- primeiro `Tab` focou `Pular para o conteúdo`; `Enter` moveu o foco ao `main#conteudo`;
- o filtro customizado de UF aceitou `ArrowDown` e `Enter`;
- `Escape` fechou os modais e o foco retornou ao botão disparador.

Isto não substitui auditoria WCAG completa com leitor de tela, contraste medido e testes em
múltiplos navegadores. A falha de tags dos PDFs está registrada separadamente como alta.

### Links oficiais

Responderam 200 com requisição de navegador:

- Dados Abertos da Câmara — deputado;
- perfil e mandatos no Senado;
- Dados Abertos do TSE — resultados 2022;
- Portal da Transparência — consulta de emendas;
- Câmara — texto integral da proposição.

O Portal da Transparência respondeu 405 ao cliente `curl` simplificado e 200 com cabeçalhos
normais de navegador, comportamento compatível com a proteção do portal, não com link
quebrado.

### CSV e PDFs

- CSV: UTF-8 com BOM, separador `;`, CRLF, 19 linhas (cabeçalho + 18 registros), números no
  formato brasileiro e URL oficial por linha.
- PDFs: PDF 1.4, 3 páginas cada, A4 paisagem, não criptografados e sem JavaScript.
- As 6 páginas foram renderizadas em PNG com Poppler e inspecionadas visualmente.

## Falhas reproduzíveis

### 1. Ausência de candidato Git

```bash
git status --short --branch
git rev-parse --verify HEAD
```

Resultado: branch sem commits; `HEAD` não pode ser resolvido.

### 2. Formatação do frontend

```bash
cd frontend
npm ci
npm run format:check
```

Resultado: os três arquivos listados em “Médio” não seguem o formatador.

### 3. Limite no terceiro download

Executar rapidamente, a partir do mesmo cliente, os três downloads expostos no perfil:

```bash
curl -OJ 'http://localhost:8001/api/v1/parliamentarians/ef4c488b-0fbe-46da-91d7-15257e57af16/staff.pdf'
curl -OJ 'http://localhost:8001/api/v1/parliamentarians/ef4c488b-0fbe-46da-91d7-15257e57af16/amendments.pdf?year=2026'
curl -OJ 'http://localhost:8001/api/v1/parliamentarians/ef4c488b-0fbe-46da-91d7-15257e57af16/amendments.csv?year=2026'
```

Resultado observado no terceiro pedido: HTTP 429 e `Retry-After: 9`.

### 4. PDFs sem tags e com artefatos visuais

```bash
pdfinfo output/pdf/qa-tabata-staff.pdf
pdfinfo output/pdf/qa-tabata-amendments-2026.pdf
pdftoppm -png -r 120 output/pdf/qa-tabata-staff.pdf tmp/pdfs/staff
pdftoppm -png -r 120 output/pdf/qa-tabata-amendments-2026.pdf tmp/pdfs/amendments
```

Resultado: `Tagged: no`; conferir equipe página 2 e emendas páginas 1 e 3.

## Comandos principais executados

```bash
git status --short --branch
node --version
npm --version
python3 --version
docker --version
docker compose version

(cd frontend && npm ci)
(cd frontend && npm audit --audit-level=high)
(cd frontend && npm run typecheck)
(cd frontend && npm run build)
(cd frontend && npm run format:check)

backend/.venv/bin/python scripts/test_backend.py
(cd backend && .venv/bin/python -m pytest -q \
  tests/test_migration_graph.py tests/test_security.py tests/test_legislation_normalization.py)
(cd backend && .venv/bin/python -m pip_audit --disable-pip --no-deps -r requirements-dev.lock)

docker compose --env-file .env.example config --quiet
docker compose --env-file .env.example build
docker compose --env-file .env build frontend
docker compose --env-file .env up -d --no-deps --force-recreate backend frontend
docker compose --env-file .env exec -T backend alembic upgrade head
docker compose --env-file .env ps

curl -fsS http://localhost:8001/api/v1/health/live
curl -fsS http://localhost:8001/api/v1/health/ready
pdfinfo output/pdf/qa-tabata-staff.pdf
pdfinfo output/pdf/qa-tabata-amendments-2026.pdf
pdftoppm -png -r 120 output/pdf/qa-tabata-staff.pdf tmp/pdfs/staff
pdftoppm -png -r 120 output/pdf/qa-tabata-amendments-2026.pdf tmp/pdfs/amendments
```

Os fluxos de navegador foram executados com o wrapper `playwright-cli` da skill Playwright,
incluindo `open`, `goto`, `snapshot`, `click`, `fill`, `press`, `eval`, `route`, `screenshot`
e `console` na sessão `qa-release-2026-11-11`.

## Evidências

- Navegador: `output/playwright/qa-release-2026-11-11/`.
- PDFs e páginas renderizadas: `output/pdf/qa-tabata-*`.
- CSV e cabeçalhos das respostas: `tmp/pdfs/`.
- Snapshots, console e capturas brutas: diretório `.playwright-cli` dentro da evidência de
  navegador.

## Recomendação de release

**NÃO LIBERAR / NÃO INTEGRAR.** Para um novo gate:

1. congelar o candidato em um commit revisável;
2. corrigir e revalidar paginação visual e acessibilidade semântica dos PDFs;
3. alinhar o limite de exportação ao conjunto de downloads da interface ou tratar 429 de
   forma amigável;
4. normalizar a data do carrossel e deixar `format:check` verde;
5. repetir typecheck, build, suíte backend, ciclo completo de migrations, Compose e os
   fluxos de navegador sobre o SHA candidato.

Os itens baixos podem ser aceitos explicitamente como dívida, mas não eliminam o bloqueador
nem os problemas altos.
