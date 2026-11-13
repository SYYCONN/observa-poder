# Observa Poder

Portal independente e sem fins lucrativos para acompanhar o poder público brasileiro. O Observa Poder organiza registros oficiais de representantes, projetos, votações e recursos públicos, preservando a fonte, o período de referência e a data de coleta.

O projeto não substitui os portais governamentais: ele oferece uma camada pública de contexto e navegação para facilitar a consulta e a conferência dos dados nas fontes oficiais.

Documentação consolidada e estado atual: [docs/00-documentacao-completa.md](docs/00-documentacao-completa.md).

Coordenação profissional das frentes de agentes: [contexto compartilhado e instruções](docs/agentes/00-contexto-compartilhado.md).

## Estrutura

```text
frontend/                 Next.js, React, TypeScript e Tailwind
  src/app/                Rotas, layouts e estilos globais
  src/components/ui/      Componentes visuais compartilhados
  src/lib/                Clientes e utilitários compartilhados
backend/                  FastAPI, SQLAlchemy e PostgreSQL
  app/api/                Composição das rotas HTTP e saúde
  app/core/               Configuração e datas de negócio
  app/db/                 Conexão e base dos modelos
  app/modules/            Regras e modelos organizados por domínio
  app/integrations/       Adaptadores das fontes oficiais
  app/jobs/               Entradas das rotinas de coleta
  alembic/                Migrações versionadas
  tests/                  Testes do backend
infra/docker/             Dockerfiles da aplicação
scripts/                  Automações operacionais reutilizáveis
.github/workflows/        Verificações de integração contínua
compose.yaml              Ambiente Docker local
.env.example              Modelo de configuração local, sem segredos reais
docs/                     Planejamento e decisões
```

Domínios legislativos possuem modelos, migration, coletores e páginas públicas de consulta. O serviço `scheduler` atualiza os dados automaticamente, sem exigir comandos manuais.

## Executar localmente com Docker

Requer Docker com Compose e o serviço Docker ativo. Na raiz do projeto:

```bash
cp -n .env.example .env
```

Edite `POSTGRES_PASSWORD` no `.env`, substituindo o exemplo por uma senha local. `FRONTEND_PORT` e `BACKEND_PORT` permitem escolher portas livres sem parar outros projetos. Em seguida:

```bash
docker compose up -d --build
docker compose ps
```

- Site: [localhost:3000](http://localhost:3000)
- Documentação da API local: [localhost:8000/docs](http://localhost:8000/docs)
- Processo da API: [health/live](http://localhost:8000/api/v1/health/live)
- Conexão com banco: [health/ready](http://localhost:8000/api/v1/health/ready)
- Atualizador automático: `docker compose logs -f scheduler`

Os links acima usam as portas padrão. Neste computador, o `.env` local usa site em `http://localhost:3001` e API em `http://localhost:8001` para evitar conflito com serviços existentes.

O frontend inicial é estático e não depende da API. `ready` só retorna sucesso com conexão ao banco. O banco não publica porta no host. As portas do site e da API estão restritas a `127.0.0.1`.

Para consultar o banco dentro do container, usando os nomes padrão:

```bash
docker compose exec db psql -U politica -d politica
```

Se mudar usuário ou nome do banco no `.env`, ajuste o comando. Credenciais de inicialização do PostgreSQL só se aplicam a um volume novo; editar o `.env` não troca a senha de uma base já existente.

Para encerrar sem remover dados:

```bash
docker compose down
```

O volume persiste entre recriações. Remover o volume apaga o banco. Backups externos ainda não foram automatizados; não usar este ambiente como produção.

## Desenvolvimento e validações

Node.js 22 e Python 3.13. Dependências do frontend são fixadas no `package-lock.json`; o backend usa `requirements.lock` e `requirements-dev.lock` gerados a partir de `pyproject.toml`.

Frontend, a partir de `frontend/`:

```bash
npm ci
npm run dev
```

Se o frontend Docker já ocupar a porta 3000, pare somente esse serviço antes de iniciar o modo de desenvolvimento. Para verificar:

```bash
npm run typecheck
npm run build
npm run format:check
```

Para formatar o frontend após editar TypeScript, TSX ou CSS:

```bash
npm run format
```

Backend, a partir de `backend/`:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pytest -q
```

O backend segue Black com limite de 100 colunas. Para conferir a formatação Python:

```bash
.venv/bin/black --check app tests
```

Para a suíte completa com PostgreSQL isolado e validação das migrations, execute `backend/.venv/bin/python scripts/test_backend.py` na raiz. O comando pytest isolado pula testes de integração quando `TEST_DATABASE_URL` não está definido. Para executar a API no host, use o modelo `backend/.env.example` e disponibilize uma conexão local protegida com o PostgreSQL. O caminho recomendado nesta base é manter API e banco no Compose.

Verificação estática do Compose, sem criar containers nem exigir `.env` real:

```bash
docker compose --env-file .env.example config --quiet
```

Após instalar dependências de desenvolvimento, para atualizar locks do backend, a partir de `backend/`:

```bash
.venv/bin/python -m pip install pip-tools==7.6.2
.venv/bin/pip-compile --strip-extras --output-file requirements.lock pyproject.toml
.venv/bin/pip-compile --strip-extras --extra dev --output-file requirements-dev.lock pyproject.toml
```

Revisar diff dos locks e executar testes antes de aceitar atualizações. Os locks foram resolvidos com Python 3.13; a execução Linux também é verificada pelo CI.

## Migrações

Alembic possui a revisão `0001_legislative_schema`, com entidades legislativas e rastreabilidade de coleta. Aplique com `docker compose exec -T backend alembic upgrade head`. Não criar tabelas automaticamente na inicialização da API. Quando um domínio for implementado, importar seus modelos no ambiente do Alembic e criar uma nova revisão. Não alterar migrations já aplicadas.

## Validação local com Docker

Build das duas imagens e execução dos três serviços concluídos neste computador. Site, documentação da API, liveness e readiness responderam HTTP 200. Alembic executou `upgrade head` com PostgreSQL real (validação inicial; posteriormente a migration legislativa foi adicionada).

A persistência foi verificada gravando um registro de teste, recriando somente o container do banco e consultando o mesmo registro. A tabela e o schema de teste foram removidos ao final. O volume permaneceu e nenhuma porta do PostgreSQL foi publicada. Esse teste não substitui backup nem validação de restauração.

## Limites desta entrega

Esta é uma fundação local, não uma configuração pronta para publicar. Ainda faltam demais coletores, autenticação administrativa se necessária, usuários de banco separados por função em produção, backups, proxy HTTPS e testes de carga. O Compose local usa o usuário de inicialização do banco por simplicidade; essa credencial não é o desenho de privilégios de produção.

Nenhum deploy ou alteração da VPS/Sycon foi realizado. A interface local consulta os parlamentares importados e permanece marcada para não indexação.

## Importar deputados da Câmara

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_deputies
```

Repetir o comando atualiza registros sem duplicar identidades. Uma coleta incompleta não publica alterações; execuções e falhas ficam em `import_runs`. O serviço `scheduler` executa as coletas automaticamente e a API permanece separada do processo de atualização. Detalhes em [Câmara e modelagem](docs/06-camara-e-modelagem.md).

## Importar senadores do Senado

Para executar uma coleta manual fora do scheduler:

```bash
docker compose exec scheduler python -m app.jobs.import_senators
```

A lista oficial é consultada diariamente por padrão. A página `/senadores` usa `GET /api/v1/parliamentarians?source=senado`; a página `/deputados` mantém `source=camara`.

## Legislação do Senado

O scheduler também consulta processos em tramitação e votações nominais do Senado. A API permite separar as fontes com `source=senado`:

```text
GET /api/v1/propositions?source=senado
GET /api/v1/votings?source=senado
```

Por segurança operacional, cada coleta publica uma janela limitada dos registros mais recentes, preserva a origem oficial e registra a execução em `import_runs`.

Para carregar uma janela inicial de proposições, autores, tramitações e votações:

```bash
docker compose exec -T backend python -m app.jobs.import_legislation
```

## Planejamento

1. [Escopo](docs/01-escopo.md)
2. [Arquitetura e dados](docs/02-arquitetura-e-dados.md)
3. [Custos e analytics](docs/03-custos-e-analytics.md)
4. [Segurança e operação](docs/04-seguranca-e-operacao.md)
5. [Processo e decisões](docs/05-trabalho-e-decisoes.md)
6. [Câmara, modelo e importação](docs/06-camara-e-modelagem.md)
7. [Interface e API pública inicial](docs/07-interface-e-api-publica.md)
8. [Frente DEPUTADOS — estado, cobertura e retomada](docs/deputados.md)
9. [Frente SENADORES](docs/senadores.md)

## Agentes e frentes de trabalho

- [Contexto compartilhado](docs/agentes/00-contexto-compartilhado.md)
- [CENTRAL-API](docs/agentes/01-central-api.md)
- [DEPUTADOS](docs/agentes/02-deputados.md)
- [SENADORES](docs/agentes/03-senadores.md)
- [SEGURANCA](docs/agentes/04-seguranca.md)
- [LEGISLATIVO](docs/agentes/05-legislativo.md)
- [ANALYTICS](docs/agentes/06-analytics.md)
- [SEO-AEO](docs/agentes/07-seo-aeo.md)
- [QA-RELEASE](docs/agentes/08-qa-release.md)
- [DADOS-PRIVACIDADE](docs/agentes/09-dados-privacidade.md)

Os documentos em `docs/` fazem parte da documentação versionável do projeto.

## Plugin de skills

As nove frentes acima também estão empacotadas no plugin privado [De Olho na Política — Engenharia](https://chatgpt.com/plugins/plugins_6af4b29878ac8191a093db3ff4f0f4ec). O plugin inclui o contexto compartilhado e as skills `central-api`, `deputados`, `senadores`, `seguranca`, `legislativo`, `analytics`, `seo-aeo`, `qa-release` e `dados-privacidade`.

O plugin fornece instruções reutilizáveis; ele não cria agentes autônomos nem inicia alterações em segundo plano. A coordenação continua sendo feita pelo chat principal, com uma frente por conversa e uma única frente editando cada área de código por vez.
