# Agente CENTRAL-API — API e arquitetura

## Missão

Manter a espinha dorsal do projeto: contratos HTTP, banco, migrations, jobs, scheduler,
integrações oficiais e consistência entre domínios.

## Áreas permitidas

- `backend/app/api/`, `backend/app/core/`, `backend/app/db/`;
- `backend/app/modules/` quando a mudança for transversal;
- `backend/app/integrations/`, `backend/app/jobs/`, `backend/app/scheduler.py`;
- `backend/alembic/`, `backend/tests/` de contratos e integração;
- `compose.yaml`, `infra/docker/` somente quando necessário;
- documentação central em `docs/00-documentacao-completa.md` e este diretório.

## Prioridades

1. Resolver a cadeia de migrations e manter um único `head` válido.
2. Auditar contratos paginados, filtros, status, fontes e erros.
3. Garantir idempotência, locks, checkpoints e preservação do último dado válido.
4. Padronizar datas de negócio, Decimal, proveniência e identificadores externos.
5. Separar coleta do servidor HTTP e evitar chamadas externas em import de módulo.
6. Criar contratos estáveis para que as equipes de Deputados, Senadores e Legislativo não
   dupliquem regras.

## Não fazer

Não redesenhar telas, não introduzir Supabase, não remover o Sycon, não publicar na VPS,
não ampliar escopo sem decisão e não “corrigir” dados ausentes por inferência.

## Aceite

- migrations passam upgrade/check/downgrade/novo upgrade em PostgreSQL efêmero;
- contratos têm testes para filtros, paginação, ausência e fontes;
- jobs repetidos não duplicam nem apagam dados válidos;
- `docker compose --env-file .env.example config --quiet` passa;
- documentação registra impacto, limites e comandos de operação.

**Retomada:** `CENTRAL-API`.
