# Agente DEPUTADOS — Câmara, perfil e listagem

## Missão

Concluir a experiência e o domínio dos deputados federais, do dado oficial ao perfil
legível: lista, filtros, mandato, eleição, projetos, votos, finanças, emendas e equipe.

## Áreas permitidas

- `frontend/src/app/deputados/` e `frontend/src/app/parlamentares/`;
- componentes diretamente usados por essas telas;
- `backend/app/modules/parlamentares/`, integrações/jobs da Câmara e rotas de perfil;
- testes e `docs/deputados.md`.

## Prioridades

1. Preservar a distinção atual/histórico e não inferir datas de exercício.
2. Ampliar autoria e votos com paginação, janela e frescor explícitos.
3. Auditar seis associações eleitorais não seguras sem usar similaridade silenciosa.
4. Revisar CEAP, remuneração, emendas e assessores como blocos separados.
5. Corrigir UX da lista: alinhamento, foco, filtros, responsividade e fallback de foto.
6. Adicionar testes para histórico, ausência, paginação, fonte e estados de erro.

## Não fazer

Não alterar o contrato de Senado, não transformar CEAP em salário, não somar etapas
financeiras e não preencher campos ausentes com zero.

## Aceite

Desktop e mobile sem sobreposição; teclado funcional; API e tela preservam filtros;
perfil mostra origem/data/limites; typecheck, build e testes direcionados passam.

**Retomada:** `DEPUTADOS`.
