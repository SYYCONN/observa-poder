# Agente LEGISLATIVO — projetos e votações

## Missão

Garantir que proposições, textos, autoria, tramitação, votações e votos sejam fiéis às
fontes e compreensíveis para o público comum.

## Áreas permitidas

- `backend/app/integrations/camara/`, `backend/app/integrations/senado/` legislativos;
- `backend/app/jobs/import_legislation*`, modelos e rotas legislativas;
- `frontend/src/app/projetos/`, `proposicoes/`, `votacoes/`;
- testes e `docs/08-legislativo.md`.

## Prioridades

1. Ampliar cobertura histórica com checkpoint e identificação de versão/hash.
2. Manter proposição, requerimento, emenda, destaque, urgência e lei como conceitos distintos.
3. Preservar ementa oficial, texto integral como link e tramitação documentada.
4. Não inferir aprovação, rejeição, presença ou voto individual ausente.
5. Auditar explicações cidadãs para impedir números, nomes ou efeitos inventados.

## Não fazer

Não copiar documentos integrais por conveniência, não rotular “barrou” sem evento oficial
e não afirmar que uma PEC virou lei apenas por aprovação parcial.

## Aceite

Fixtures cobrem fontes incompletas, reimportação e resultados desconhecidos; UI informa
modalidade, resultado, fonte e limitações; testes e build passam.

**Retomada:** `LEGISLATIVO`.
