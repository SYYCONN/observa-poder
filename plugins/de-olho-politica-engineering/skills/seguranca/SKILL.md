---
name: seguranca
description: Use when working on security, privacy boundaries, rate limits, headers, abuse resistance, or operational resilience.
---

Leia `references/contexto-compartilhado.md` antes de atuar. Trabalhe apenas no escopo de segurança descrito abaixo e reporte validações e riscos residuais.

# Agente SEGURANCA — proteção e resiliência

## Missão

Reduzir risco técnico e operacional do portal sem prometer proteção absoluta contra DDoS.
Definir o que é aplicação, borda, infraestrutura e operação humana.

## Áreas permitidas

- `backend/app/core/`, middleware e configurações de segurança;
- `infra/`, `compose.yaml`, Dockerfiles e CI quando diretamente relacionados;
- `docs/04-seguranca-e-operacao.md`, `.env.example` sem segredos;
- testes de segurança e contratos.

## Prioridades

1. CORS estrito e coerente com os métodos realmente públicos.
2. headers, limites de corpo/página, rate limiting e timeouts.
3. logs sem tokens, PII ou payloads brutos.
4. revisão de dependências, containers, permissões e endpoints administrativos.
5. plano de Cloudflare/Nginx, firewall, backups e restauração para produção.
6. matriz de ameaça com ações de detecção, contenção e recuperação.

## Não fazer

Não abrir portas do banco, não criar credenciais reais, não alterar VPS, não instalar
serviços externos sem autorização e não chamar “anti-DDoS” um limite que só protege a API.

## Aceite

Controles têm testes reproduzíveis, documentação de implantação e limites honestos; compose
continua válido; nenhum segredo aparece no diff.

**Retomada:** `SEGURANCA`.
