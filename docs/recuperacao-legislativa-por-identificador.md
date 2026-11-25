# Recuperação legislativa por identificador e período

## Escopo

O job `app.jobs.backfill_legislation` complementa a coleta recente. Não substitui
os registros exclusivos de produção, não copia bancos e não inicia coleta ao ser
importado. Câmara: proposições e votações por identificador, além de descoberta
paginada por período de até 31 dias. Senado: matérias por código oficial e votações
nominais por identificador e ano, ou descoberta de todas as votações da lista anual,
sem o corte das últimas 50 utilizado na coleta recente.

Cada votação também enfileira seus documentos relacionados. A recuperação de uma
proposição da Câmara consulta detalhe, autoria e tramitação. As funções de escrita
das votações foram extraídas dos coletores existentes para evitar normalizadores
duplicados. Relações `object`, `possible_object` e `affected` conservam a distinção
da fonte. A descrição detalhada da votação tem preferência sobre a lista resumida.

## Limites e retomada

- Até 100 itens por execução; padrão 10. Descoberta de até cinco páginas por tipo
  e execução; padrão uma. Cada página tem no máximo 100 registros.
- Checkpoint contém somente plano, identificadores, estados, tentativas e contagens
  de cobertura. Não contém credenciais, nomes ou cópias de payloads oficiais.
- Checkpoint é gravado atomicamente, com modo 0600, em diretório persistente. Um
  arquivo pertence a um plano exato; outros identificadores/períodos exigem outro
  arquivo. Não edite nem apague o checkpoint para uma retomada normal.
- Cada item tem transação própria. O checkpoint só marca sucesso após o commit.
  Uma interrupção entre commit e checkpoint permite repetição idempotente.
- Itens falhos têm até três tentativas entre execuções. HTTP 404 é registrado como
  indisponível, sem apagar o último dado válido. `--retry-errors` reabre erros e
  indisponíveis somente por decisão explícita do operador.
- O job usa os locks das coletas legislativas; na Câmara também bloqueia concorrência
  com a carga anual de votos. Não execute um segundo coletor para tentar contornar
  uma mensagem de carga em andamento.
- Respostas HTTP têm limite de 64 MiB, timeout e ritmo mínimo de 0,25 segundo entre
  chamadas iniciadas pelo cliente. As consultas usam os hosts fixos das fontes.
  Links `next` só indicam existência de outra página: seu endereço não é seguido.

`coverage_complete` significa que **o plano selecionado** terminou sem itens
pendentes, falhos ou indisponíveis. Não comprova histórico integral da Casa. Uma
busca por período sem resultados não prova inexistência de votações: o exemplo
`2654167-5` respondeu pelo identificador enquanto não apareceu na consulta por
data testada. Manifestos de identificadores conhecidos continuam necessários para
confrontar as lacunas entre ambientes e os índices da própria fonte.

Votos publicados sem parlamentar correspondente ou com posição não reconhecida
mantêm o item como falho/incompleto. O checkpoint informa a contagem, sem inventar
identidades nem posições. Votação cuja fonte publica lista vazia não recebe votos
inventados nem modalidade presumida. Os contadores de `import_runs` registram a
tentativa do lote; a cobertura detalhada fica no checkpoint e na saída JSON.

### Identidades históricas do Senado

A recuperação explícita permite cadastrar uma identidade histórica quando o
arquivo oficial informa simultaneamente código numérico, nome e URL do perfil
`www25.senado.leg.br/web/senadores/senador/-/perfil/CODIGO`, com o mesmo código.
Credenciais na URL, outro host, código divergente, porta, query ou fragmento são
rejeitados. URLs legadas HTTP são normalizadas para HTTPS no mesmo perfil oficial.

O registro conserva a proveniência da votação, é marcado como cadastro histórico
e não recebe mandato, datas, partido, UF ou foto inferidos desse evento. Cadastros
existentes não têm nome nem indicação de exercício atual sobrescritos. O status de
exercício atual continua sob responsabilidade da lista oficial de senadores atuais.
Essa criação é habilitada somente no backfill; a coleta recente mantém sua política.
O lock de cadastro dos senadores atuais também é adquirido para impedir concorrência.

Na investigação de 25/11/2026, os primeiros 25 registros anuais incluíam oito códigos
oficiais ausentes da listagem pública de produção. O ensaio local com a correção
processou esses 25 registros com sucesso, deixando 73 itens pendentes para os lotes
seguintes. Isso não declara o plano anual completo. A execução da correção na VPS
deve reutilizar `/state/senado-2026.json`, preservando o checkpoint já existente.

## Implantação e primeiro plano na VPS

Depois de atualizar o repositório e construir a imagem do scheduler, prepare um
diretório dedicado. O usuário 10001 é o usuário sem root da imagem:

```bash
install -d -m 0700 -o 10001 -g 10001 /etc/observa-poder/collect-state
docker compose --env-file /etc/observa-poder/production.env \
  -f compose.production.yaml run --rm --no-deps -T \
  -v /etc/observa-poder/collect-state:/state \
  scheduler python -m app.jobs.backfill_legislation \
  --source camara --voting-id 2654167-5 \
  --checkpoint /state/camara-2654167-5.json --max-items 10
```

Repita exatamente o comando para retomar. Se estiver completo, a repetição deve
mostrar `processed: 0`. O agendador já em execução continua com sua imagem até uma
recriação; esta recuperação usa um container pontual da imagem recém-construída.
Nenhuma porta pública ou migration nova é necessária.

Para um período da Câmara, use outro checkpoint e substitua o identificador por
`--from-date 2026-11-18 --to-date 2026-11-18`. Repita até `discovery_complete: true`
e ausência de pendentes. Para votações do Senado, use `--source senado --year 2026
--discover-votings`, com checkpoint próprio e lotes de até 100. Matérias do Senado
usam `--proposition-id CODIGO_DA_MATERIA`, sem confundir com código do processo.

## Validação realizada

262 testes passaram em release isolada com PostgreSQL temporário, incluindo ciclo
de migrations, retomada, idempotência, rollback por item, checkpoint após falha de
disco, locks, limite de período, bloqueio de URLs externas e lista anual de Senado
com mais de 50 votações. Nenhum frontend foi alterado nesta etapa.

O ensaio local recuperou a votação `2654167-5` e seus dois documentos relacionados
com três sucessos. A reexecução do mesmo plano confirmou `processed: 0`, sem itens
processados novamente. A execução e a conferência da cobertura na VPS ainda dependem
do operador. O checkpoint do ensaio local não deve ser enviado para o destino:
estados concluídos em um banco não comprovam importação em outro banco.

## Riscos e operação

| Controle | Ameaça mitigada | Impacto | Custo | Risco residual | Validação |
| --- | --- | --- | --- | --- | --- |
| Checkpoint e transação por item | Perda do lote ou repetição após interrupção | Retomada com dados preservados | Baixo; arquivos e execuções administrativas | Perda do checkpoint exige repetição idempotente | Interromper entre commit e checkpoint e repetir |
| Locks e lotes limitados | Concorrência de escrita e sobrecarga | Trabalho gradual | Médio; fontes grandes precisam de vários lotes | I/O e indisponibilidade da fonte ainda afetam a coleta | Locks, recursos da VPS e histórico de execuções |
| Contagem de votos não associados | Declarar cobertura completa com votos faltantes | Lacunas explícitas | Médio; pode exigir cadastro histórico oficial | Fonte pode continuar ambígua ou indisponível | Confrontar publicados, associados e posições reconhecidas |
| URLs fixas, limites e tentativas finitas | SSRF, excesso de resposta e abuso de consultas | Consultas controladas | Baixo; timeout e novas tentativas administrativas | Limites do cliente não protegem toda a infraestrutura | Testes de identificadores, link externo e resposta comprimida |
