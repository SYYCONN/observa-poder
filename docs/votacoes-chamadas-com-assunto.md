# Chamadas de votações com assunto e alcance da decisão

## Problema confirmado em 18/11/2026

A votação da Câmara `2654167-5` aparecia no localhost somente como "Aprovada".
O registro já possuía vínculo do tipo `object` com o relatório REL 1/2026,
proposição oficial `2654356`. A ementa trata das emendas da Comissão de Defesa
do Consumidor ao projeto de Orçamento de 2027. A apresentação anterior ignorava
esse contexto, tanto no cartão de listagem quanto no título do detalhe.

A consulta oficial foi feita em:
`https://dadosabertos.camara.leg.br/api/v2/votacoes/2654167-5`.
Na consulta realizada, o registro ainda não aparecia na pesquisa pública da
produção. As bases têm janelas e históricos independentes.

## Regra de apresentação

- API fornece `display_title`, `decision_context` e `subject_status` nas listas
  e no detalhe, usando vínculos já persistidos, sem nova coleta por acesso.
- Um objeto único confirmado permite identificar o que foi aprovado ou rejeitado.
  No caso reportado: **Aprovado relatório sobre emendas ao Orçamento de 2027**.
  O contexto informa que a decisão não representa a aprovação do Orçamento inteiro.
- A forma curta sobre orçamento exige relatório, menção explícita a emendas e um
  único ano associado ao orçamento na ementa. O ano do número de um PLN não é
  interpretado como exercício orçamentário.
- Objeto possível é apresentado como relação possível, sem afirmar sua aprovação.
  Múltiplos objetos ou assunto ausente têm limitações explícitas na chamada.
- Etapas específicas, como apreciação preliminar, urgência e destaque, conservam
  a descrição oficial em vez de declarar aprovação do projeto inteiro.
- Detalhe oferece o texto original da fonte em seção expansível. Campos oficiais
  originais não são sobrescritos pela apresentação.

## Validação e implantação

Testes de relatório e orçamento, rejeição, resultado ausente, etapas específicas,
relações possíveis, múltiplos objetos, relações de outra Casa e anos conflitantes.
Integração PostgreSQL verifica igualdade de chamada na lista e detalhe e uma única
consulta adicional em lote para 12 cartões, evitando uma consulta por cartão.
Suite isolada: 246 testes passaram, com ciclo de migrations e verificação de schema.
Frontend passou em build e typecheck.

Não há alteração de schema, inferência de votos ou publicação automática de explicação
por IA. Atualização exige reconstruir e reiniciar API e frontend. O agendador não
precisa ser reiniciado. A confirmação visual ocorre primeiro no localhost; a VPS
exige a execução dos comandos pelo operador.
