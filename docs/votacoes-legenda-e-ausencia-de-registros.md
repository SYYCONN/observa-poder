# Votações: legenda e ausência de registros individuais

Verificação realizada em 17/11/2026.

## Evidência do registro reportado

- Identificador oficial: `2631155-2`; UUID em produção: `f6c242b5-b071-42e5-888f-9e6145279021`.
- O detalhe oficial informa resultado aprovado, descrição "Aprovado o Requerimento.", modalidade sem informação explícita e possível relação com REQ 37/2026.
- `https://dadosabertos.camara.leg.br/api/v2/votacoes/2631155-2/votos` respondeu HTTP 200 com `dados: []`.
- A API de produção retornou a mesma ausência de votos individuais e o vínculo possível com REQ 37/2026. O registro não aparecia no localhost na consulta realizada.
- Como controle, o registro nominal `2462126-22` retornou 11 posições individuais em produção. Isso confirma funcionamento desse endpoint para o exemplo de controle, sem provar cobertura completa do universo de votações.

A ausência de votos individuais no registro reportado também existe na fonte oficial
consultada. Não se pode inferir modalidade simbólica, unanimidade, ausência parlamentar
ou posições individuais apenas por essa ausência. Publicação tardia pode alterar a
fonte depois da verificação.

## Alteração de apresentação

- Guia expansível na lista e no detalhe, acessível por teclado, com modalidades, resultado, requerimento e outros registros.
- Legenda textual e por cor para Sim, Não e Outros, explicação dos eixos, indicação do partido na data do voto e tabela com os mesmos totais.
- Estado sem votos individuais não apresenta placar de zeros, gráfico, filtros ou tabela de totais vazios. Mantém o resultado geral, as relações efetivamente importadas e a fonte oficial.
- Data do evento em formato brasileiro. Modalidade desconhecida é apresentada como não informada na coleta.
- Fontes conceituais: guia de votação da Câmara e glossário legislativo do Congresso Nacional, com links públicos na interface.

## Validação

Build e typecheck do frontend em checkout isolado da versão publicada, incluindo
somente os três arquivos alterados. Navegação em browser com Playwright em desktop
1440px e celular 390px, utilizando respostas capturadas da API pública como fixtures.
O teste de interface não realiza nova coleta nem modifica bancos. Verificados:
guia por teclado, legenda, tabela acessível, estado nominal com 11 registros,
estado sem registros sem gráfico ou placar e ausência de overflow horizontal.

Não houve mudança de banco, contrato HTTP ou regras de importação. A publicação
exige atualizar somente a imagem e o container do frontend; o agendador permanece
executando. Validação final em produção deve ocorrer depois dessa atualização.
