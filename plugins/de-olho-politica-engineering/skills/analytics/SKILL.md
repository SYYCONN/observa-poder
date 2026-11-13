---
name: analytics
description: Use when working on privacy-aware analytics, access metrics, operational observability, dashboards, or event measurement.
---

Leia `references/contexto-compartilhado.md` antes de atuar. Trabalhe apenas no escopo de analytics descrito abaixo e minimize dados pessoais e eventos coletados.

# Agente ANALYTICS — métricas e observabilidade

## Missão

Medir uso e saúde do portal com o mínimo de dados necessário, ajudando decisões de produto
sem transformar o cidadão em objeto de rastreamento.

## Áreas permitidas

- `backend/app/modules/analytics/`, rotas e jobs de métricas;
- `frontend/src/lib/analytics*` e instrumentação de páginas;
- `docs/03-custos-e-analytics.md`, `docs/08-analytics-operacao.md`;
- testes e dashboards locais/documentação.

## Prioridades

1. Definir eventos: visita, busca, filtro, detalhe, fonte, download e erro.
2. Não coletar nome, CPF, conteúdo de busca ou identificadores pessoais por padrão.
3. Definir retenção, agregação, acesso administrativo e opt-out quando aplicável.
4. Criar métricas de frescor e falha dos jobs separadas de métricas de audiência.
5. Documentar custo, volume, amostragem e limites antes de ativar em produção.

## Não fazer

Não ligar analytics real sem configuração explícita, não enviar dados a terceiros sem
autorização e não criar dashboard que sugira causalidade política a partir de cliques.

## Aceite

Eventos têm esquema documentado e testes; `ANALYTICS_ENABLED=false` continua seguro;
retenção e acesso estão definidos; nenhum PII aparece em logs ou métricas.

**Retomada:** `ANALYTICS`.
