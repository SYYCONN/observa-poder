# De Olho na Política — orientação do projeto

Este repositório pertence ao portal político, não ao Sycon Suite. O Sycon só aparece no planejamento da futura substituição na VPS.

## Organização

- `frontend/`: Next.js/TypeScript, rotas em `src/app/`, UI compartilhada em `src/components/ui/`.
- `backend/app/modules/`: modelos, schemas, serviços e rotas por domínio.
- `backend/app/integrations/`: clientes e normalizadores de fontes oficiais.
- `backend/app/jobs/`: processos de coleta separados do servidor HTTP.
- `backend/app/core/` e `db/`: configuração, datas e persistência compartilhadas.
- `backend/alembic/`: novas revisões para mudanças de schema; nunca editar revisão já aplicada.
- `infra/`: infraestrutura; `scripts/`: automações reutilizáveis; `docs/`: decisões locais.

## Regras

- Conferir `git status --short --branch` e preservar alterações existentes antes de editar.
- Não criar pastas ou camadas vazias sem responsabilidade concreta. Evitar arquivos genéricos gigantes.
- Não adicionar Supabase. Banco PostgreSQL em Docker com volume persistente.
- Não publicar a porta do banco nem commitar segredos, dumps ou backups.
- Datas de negócio em America/Sao_Paulo; reutilizar `local_today()`. Dinheiro com Decimal.
- Preservar proveniência e identificadores externos; não inferir voto, culpa ou gasto a partir de dado ausente.
- Nenhuma integração deve começar a coletar automaticamente ao importar módulos ou iniciar a API.
- Não modificar a VPS ou remover o Sycon como consequência de mudanças locais.
- Dependências devem ter locks atualizados e alterações revisadas.

## Validações

- Frontend: `npm run typecheck` e `npm run build`, dentro de `frontend/`.
- Backend: `.venv/bin/python -m pytest -q`, dentro de `backend/`.
- Compose: `docker compose --env-file .env.example config --quiet`, na raiz.
- Informar limitações de ambiente sem atribuí-las automaticamente ao código.
- Responder em português com alterações, validações e pendências concretas.
