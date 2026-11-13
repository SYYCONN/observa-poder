---
name: senadores
description: Use when working on the Senado integration, senator listing, profiles, matters, votes, and source provenance.
---

Leia `references/contexto-compartilhado.md` antes de atuar. Trabalhe apenas no escopo de senadores descrito abaixo e reporte validações e bloqueios.

# Agente SENADORES — Senado, perfil e listagem

## Missão

Levar a área de senadores à paridade conceitual com deputados sem assumir que as fontes
das duas Casas têm o mesmo contrato ou histórico.

## Áreas permitidas

- `frontend/src/app/senadores/` e perfil compartilhado quando necessário;
- `backend/app/integrations/senado/`, jobs e persistência específica de Senado;
- testes de Senado e `docs/senadores.md`.

## Prioridades

1. Resolver CORS e integração real no navegador.
2. Distinguir snapshots atuais de históricos sem apagar registros antigos.
3. Revisar legislatura incompatível, datas individuais e fuso de eventos.
4. Documentar claramente que a janela atual de votações não é histórico integral.
5. Melhorar filtros, cards, estados vazios, acessibilidade e links oficiais.

## Não fazer

Não aplicar endpoints da Câmara ao Senado, não preencher datas pela legislatura e não
tratar ausência de voto como “Não”.

## Aceite

Coleta idempotente, fonte `senado` preservada, lista e perfil navegáveis, testes de datas
e integração passando e pendências registradas em `docs/senadores.md`.

**Retomada:** `SENADORES`.
