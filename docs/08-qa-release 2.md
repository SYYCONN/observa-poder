# QA-RELEASE

Auditoria local em 03/11/2026 (America/Sao_Paulo). **Release bloqueado** no estado
observado ao final da execução. Outras frentes alteraram arquivos durante a auditoria;
os resultados abaixo representam execuções locais, sem um commit imutável de referência.
O repositório ainda não possui commits. Nenhum deploy foi realizado.

## Validações e evidências

| Verificação | Resultado observado |
| --- | --- |
| Frontend `npm run build` | Passou; páginas estáticas e dinâmicas geradas |
| Frontend `npm run typecheck` | Passou após o build regenerar `.next/types` |
| Frontend `npm run format:check` | Falhou em `src/app/deputados/page.tsx` |
| Backend com PostgreSQL efêmero, primeira execução | 45 testes passaram; upgrade, check, downgrade e novo upgrade passaram |
| Backend com PostgreSQL efêmero, segunda execução | Interrompido no upgrade: revisão `0009` duplicada |
| Backend sem PostgreSQL de teste, última execução completa | 94 passaram, 16 pulados e 3 falharam |
| Novos contratos HTTP isolados | 26 passaram, sem consultas a fontes oficiais |
| Compose com `.env.example` | Configuração válida |
| Serviços Compose existentes | Backend e PostgreSQL saudáveis; frontend e scheduler em execução |
| HTTP local `health/live` e `health/ready` | Ambos 200 |
| Listas locais de parlamentares, proposições e votações | 200; listas de parlamentares informaram 513 deputados e 81 senadores |
| Navegador desktop | Home e navegação para deputados carregaram |
| Navegador mobile, 390 × 844 | Menu abriu/fechou; largura do documento 390, sem overflow horizontal no estado observado |

Ambiente: Node 22.18.0 e Python 3.13.7. O navegador verificou os serviços já existentes
em `localhost:3001` e `localhost:8001`; eles não foram reconstruídos nesta frente.
Build e typecheck validaram o código do workspace. Saúde dos containers não comprova
que todas as coletas do scheduler estejam atualizadas.

Os testes de integração são pulados sem `TEST_DATABASE_URL`. O script de teste completo
cria e remove seu próprio PostgreSQL, sem utilizar o volume da aplicação.

## Bloqueios reproduzidos

1. **Colisão de migration:** `0009_analytics_daily_metrics.py` e
   `0009_minimize_supplier_documents.py` declaram `revision = "0009"` e
   `down_revision = "0008"`. O Alembic não executa `upgrade head`. A coordenação das
   frentes responsáveis precisa definir a cadeia válida, respeitando migrations já
   aplicadas. Esta auditoria não alterou nenhuma migration.
2. **Normalização de datas:**
   `test_legislative_dates_use_business_timezone_and_keep_explicit_offsets[parse_date]`
   recebeu offset UTC e esperava `-03:00`. Verificar o contrato de `parse_date` com a
   frente responsável antes de alterar a implementação ou o teste: o resultado observado
   representa o mesmo instante em UTC, mas não conserva o offset exigido pelo teste.
3. **CORS:** `test_cors_only_allows_frontend_and_read_methods` esperava rejeição 400
   para preflight POST e recebeu 200. Alinhar a configuração ao contrato de métodos da
   API pública.

Pendências de interface:

- O filtro customizado em `frontend/src/components/filter-select.tsx` abre um
  `listbox`, mas ArrowDown manteve o foco no botão “Todos os estados”. Faltam navegação
  entre opções por setas e gestão de foco; o texto do rótulo também não está associado
  ao botão por `aria-labelledby`. Revalidar com teclado e leitor de tela.
- Corrigir a formatação de `frontend/src/app/deputados/page.tsx`.

Não houve auditoria completa WCAG, teste de carga, restauração de backup, validação de
produção, teste completo de downloads ou de todos os estados de falha da interface.

## Alterações desta frente

- `backend/requirements-dev.lock`: regenerado incluindo ReportLab e suas dependências,
  usando o lock de produção como constraint. As 29 dependências de produção mantêm
  versões idênticas no lock de desenvolvimento. O lock de produção foi preservado.
- `backend/tests/test_api_contracts.py`: 26 casos de validação de filtros/paginação,
  UUIDs inválidos, recursos ausentes, listas vazias e prioridade da rota de partidos.
  Usam transporte ASGI e sessão simulada; não comprovam a correção das consultas SQL.
- `backend/tests/test_migration_graph.py`: identifica revisões duplicadas, múltiplas
  heads/bases, referências ausentes e ciclos sem acessar o banco. Detectou a colisão
  atual de `0009`, incluindo os nomes dos arquivos na mensagem de falha.
- Este checklist.

## Checklist para liberar um candidato

- [ ] Resolver os bloqueios acima nas respectivas frentes.
- [ ] Congelar o candidato em um commit identificável e revisar os arquivos incluídos,
      mantendo segredos, dumps, backups e artefatos locais fora do Git.
- [ ] Instalar as dependências pelos locks e executar as validações abaixo.
- [ ] Confirmar migrations com PostgreSQL efêmero, sem skips na suíte de integração.
- [ ] Testar busca, filtros, paginação, perfis, proposições e votações em desktop/mobile.
- [ ] Revalidar teclado, foco, nomes acessíveis e estados de carregamento/erro/vazio.
- [ ] Verificar exportações CSV/PDF e preservação de fonte, data e valores ausentes.
- [ ] Antes de produção, definir e testar backup/restauração, HTTPS e plano de rollback.

Comandos na raiz, exceto os agrupados com `cd`:

```bash
(cd backend && .venv/bin/python -m pip install -r requirements-dev.lock)
(cd frontend && npm ci && npm run typecheck && npm run build && npm run format:check)
backend/.venv/bin/python scripts/test_backend.py
docker compose --env-file .env.example config --quiet
docker compose ps
```

Em um checkout sem `.next`, o typecheck utiliza os arquivos disponíveis e o build gera
os tipos de rotas. Caso existam artefatos locais duplicados em `.next`, investigar sua
origem; nesta auditoria um build os regenerou e o typecheck seguinte passou.

Para manter o lock de desenvolvimento alinhado ao de produção, em `backend/`:

```bash
.venv/bin/pip-compile --strip-extras --constraint requirements.lock --extra dev --output-file requirements-dev.lock pyproject.toml
```

Estes comandos são de validação local. Não executar deploy nem modificar a VPS/Sycon
como consequência deste checklist.
