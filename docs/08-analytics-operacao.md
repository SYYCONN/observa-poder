# ANALYTICS — métricas próprias e operação

Implementação local, desativada por padrão. Não houve acesso à VPS, contratação ou integração com Cloudflare/GA4. Complementa a proposta de audiência em `03-custos-e-analytics.md`: os eventos próprios abaixo passam a ter implementação opcional; ferramentas externas continuam sem configuração.

## Dados e limites

A tabela `analytics_daily_metrics` guarda exclusivamente dia em America/Sao_Paulo, categoria, template de rota, resultado, contador e soma das durações em milissegundos. Incremento atômico por chave composta, compartilhado entre workers. Sem registros individuais, IP, cookies, identificadores de sessão/visitante, origem de tráfego, user-agent, URL completa, IDs de políticos, termos livres ou valores de filtros.

- `pageview`: montagem inicial e navegação entre páginas instrumentadas pelo cliente; rotas de detalhe são reduzidas a `[id]`. Sem cookies ou armazenamento local. Respeita DNT e GPC. `/analytics` não é instrumentada.
- `api_request`: chamadas às rotas públicas de parlamentares, proposições e votações, com código HTTP e duração média da resposta completa. Health, analytics, URLs desconhecidas e demais rotas são excluídas. Inclui chamadas técnicas e robôs.
- `search_request` / `filter_request`: respostas GET bem-sucedidas cuja query contém os nomes dos parâmetros reconhecidos. Buscas usam `search` ou `q`. Filtros usam `state`, `party`, `source`, `status`, `year`, `month`, `date`, `date_from`, `date_to`, `kind`, `result` ou `mode`. Não lê nem grava valores. Pode incluir paginação, carregamento inicial, filtros vazios e chamadas diretas; não é contagem exata de ações humanas.
- `download`: GET bem-sucedido de endpoint PDF. Não comprova que a pessoa salvou o arquivo. Falhas aparecem nos contadores HTTP.

## Catálogo de medição

As categorias usam a data local, um template de rota e um contador. `api_request` acrescenta o código HTTP e a soma das durações. Retenção de 90 dias por padrão, configurável e aplicada pelo job de descarte. As justificativas abaixo descrevem a finalidade operacional de cada medição. A definição da base legal e do aviso público depende da configuração adotada no lançamento.

| Nome | Finalidade e justificativa | Propriedades específicas | Visualização | Custo por ocorrência |
| --- | --- | --- | --- | --- |
| `pageview` | Medir o uso das áreas públicas e orientar melhorias de navegação | Template fixo da página, inclusive detalhes sem ID | Total de visualizações e detalhe diário por página | Um POST e um incremento. Sujeito a DNT/GPC |
| `search_request` | Medir demanda por busca e orientar melhorias na consulta | Presença de `search` ou `q` em GET bem-sucedido | Total e detalhe diário por endpoint | Um incremento adicional |
| `filter_request` | Medir demanda por filtragem e orientar melhorias nos filtros | Presença de parâmetro de filtro reconhecido em GET bem-sucedido | Total e detalhe diário por endpoint | Um incremento adicional mesmo com vários filtros |
| `download` | Medir demanda pelos PDFs gerados pelo portal | Template do endpoint PDF em GET bem-sucedido | Total e detalhe diário por tipo de PDF | Um incremento adicional |
| `api_request` | Detectar falhas HTTP e acompanhar o desempenho da API pública | Template, código HTTP e duração da resposta em ms | Volume, 5xx e média em ms por dia, rota e código | Um incremento por requisição instrumentada |

A contagem usa todos os eventos elegíveis, sem amostragem. Um pedido pode incrementar mais de uma categoria. O volume de escritas cresce com o tráfego, enquanto o espaço cresce com as combinações de data, categoria, rota e resultado. Acesso às páginas é medido por `pageview`. Medição por sessão e abertura de fontes externas ficam adiadas até haver uma finalidade que justifique eventos adicionais.

| Indicador operacional | Finalidade e justificativa | Propriedades | Retenção e visualização | Custo |
| --- | --- | --- | --- | --- |
| `integration_health` | Identificar coletas com falhas ou sem atualização recente | Nome fixo do job, estado e início da última tentativa, último sucesso concluído, total de falhas/interrupções encerradas nos últimos 7 dias | Consulta privada ao histórico existente de `import_runs`. Exibe um resumo por job, sem cópia ou nova retenção | Uma consulta SQL adicional por carregamento do painel, sem escrita nem chamada à fonte |

O painel usa os registros existentes dos coletores. O estado descreve a última tentativa registrada e o último sucesso permite avaliar frescor conforme a cadência de cada job. Um sucesso indica conclusão do coletor e pode cobrir apenas a janela consultada. Uma integração sem registros aparece explicitamente como tal.

Não mede visitas, pessoas únicas, preferência política, percentis de latência ou disponibilidade externa. Bloqueadores e JavaScript desativado reduzem pageviews. Clientes podem forjar eventos; validação de Origin reduz submissões acidentais entre sites, mas não autentica pessoas nem bloqueia bots. Antes de exposição pública, definir limite de requisições e tamanho de corpo no proxy. Não há contador de erro JavaScript: mensagens, stacks e URLs do browser não são enviados.

Métricas técnicas da API continuam agregadas mesmo com DNT/GPC; esses sinais impedem eventos de audiência. Desligar `ANALYTICS_ENABLED` interrompe toda instrumentação no backend no próximo restart.

## Ativação explícita

1. Aplicar `alembic upgrade head` no backend, com backup e revisão do destino conforme rotina do ambiente. Nova revisão: `0010`, após a revisão `0009` de minimização de documentos.
2. Configurar `ANALYTICS_ENABLED=true`, `ANALYTICS_ADMIN_TOKEN` com token aleatório forte e `ANALYTICS_RETENTION_DAYS=90` (aceita 1–366). Token nunca deve usar prefixo `NEXT_PUBLIC`.
3. Para audiência, configurar também `NEXT_PUBLIC_ANALYTICS_ENABLED=true` **no build** do frontend. Definir `NEXT_PUBLIC_API_URL` e `FRONTEND_URL` com origens reais compatíveis; Compose já encaminha essas opções. Sem essa flag, só métricas técnicas da API são coletadas.
4. Reiniciar backend e reconstruir frontend. Abrir `/analytics`, informar token no campo de senha e consultar. O token fica somente em memória; ao sair, usar “Limpar acesso” ou fechar a aba. Usar HTTPS no ambiente público. Não colocar token em URL.
5. O painel consome `GET /api/v1/analytics/summary?days=30` com Bearer. Relatório retorna datas inclusivas, buckets diários e `Cache-Control: no-store`. Período máximo acompanha retenção. Falta de token/configuração oculta os dados; não existe token padrão. Um resultado vazio não prova ausência de tráfego: conferir flags, migration e escrita no banco.

A tela administrativa é pública como formulário, mas todos os dados dependem de autenticação no backend. Acesso deve ficar limitado aos responsáveis; rotacionar token quando necessário. Não há contas individuais ou auditoria de operadores nesta etapa.

## Retenção e monitoramento

Executar diariamente no ambiente do backend, pelo agendador operacional escolhido:

```bash
python -m app.jobs.purge_analytics
```

Remove buckets anteriores à janela configurada, incluindo hoje no cálculo. O comando não roda ao importar módulos ou iniciar a API e **ainda não está agendado automaticamente**. Sem execução periódica, buckets antigos permanecem no banco. Os relatórios filtram a janela pedida. Aplicar também política de expiração aos backups conforme plano operacional.

Falha de persistência de métricas gera aviso fixo `analytics_write_failed`, sem detalhe do banco, e não substitui a resposta pública. Monitorar esse aviso e o próprio job de descarte: falhas de escrita não podem ser contadas no mesmo banco indisponível. Existe custo de escrita síncrona após a resposta ASGI; não há fila ou garantia de entrega. Testar carga antes de ativar em produção.

Health existente: `/api/v1/health/live` verifica processo; `/api/v1/health/ready` verifica acesso ao banco. O painel de integrações consulta apenas os campos operacionais necessários e exclui mensagens de erro, payloads e IDs das execuções. Alertas externos e metas de disponibilidade continuam pendentes. Logs de proxy e Uvicorn têm ciclo de vida separado e precisam de revisão de retenção/redação de queries.

## Pendências de lançamento

- Revisar aviso público de privacidade conforme configuração efetivamente ativada, responsável e canal de contato; a implementação não decide bases legais ou necessidade de consentimento.
- Definir proteção de borda, política de logs, agendamento do descarte e monitoramento externo.
- Validar carga na infraestrutura escolhida. A suíte local com PostgreSQL efêmero validou migrations (upgrade, check e downgrade) e 40 incrementos concorrentes sem perda de contagem. Testes rápidos de agregação/retenção usam SQLite.
- Cloudflare, visitantes/visitas mensais, origens, Web Vitals, alertas de coleta e exportações automáticas continuam fora desta entrega.

## Arquivos desta frente

Novos:
- `backend/app/modules/analytics/{__init__,models,service,middleware}.py`: persistência agregada e instrumentação técnica.
- `backend/app/api/routes/analytics.py`: ingestão restrita a templates e relatório autenticado.
- `backend/alembic/versions/0010_analytics_daily_metrics.py`: tabela agregada.
- `backend/app/jobs/purge_analytics.py`: descarte explícito.
- `backend/tests/test_analytics.py` e `backend/tests/integration/test_analytics_postgres.py`: proteção, privacidade, retenção, falhas e concorrência.
- `frontend/src/components/analytics-pageview.tsx`: visualizações sem IDs.
- `frontend/src/app/analytics/{page,layout}.tsx`: painel e exclusão de indexação.
- `docs/08-analytics-operacao.md`: operação, limites e pendências.

Integrações pontuais em arquivos existentes:
- `backend/app/{main.py,core/config.py,api/router.py,db/models.py}`.
- `frontend/src/app/layout.tsx`.
- `.env.example`, `backend/.env.example`, `compose.yaml`, `infra/docker/frontend.Dockerfile`.

Validação: `backend/.venv/bin/python scripts/test_backend.py` passou com **124 testes**, Alembic upgrade/check/downgrade/upgrade em PostgreSQL descartável; frontend build e typecheck passaram; Compose config passou. Painel conferido em 1440×900 e 390×844, com dados simulados no browser e sem overflow horizontal da página. Capturas locais em `output/playwright/analytics-{desktop,mobile}.png` (números apenas ilustrativos). Nenhuma dependência adicionada e nenhuma alteração na VPS.
