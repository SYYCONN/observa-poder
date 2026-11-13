# Coletas

`import_deputies.py` importa a lista atual da Câmara. Execução explícita, fora do servidor HTTP:

```bash
docker compose exec -T backend python -m app.jobs.import_deputies
```

Aplicar migrations antes. O comando retorna resumo JSON e código diferente de zero em falha ou concorrência. Resultados e falhas ficam em `import_runs`.

A coleta é completa e limitada: páginas são validadas em memória e publicadas em uma única transação. Em erro, repetir o comando reinicia da primeira página; `pages` e `received` são diagnóstico, não um checkpoint para continuar uma publicação parcial.

`import_camara_deputy_profiles.py` completa os perfis com data de nascimento e eventos
individuais de entrada e saída. A rotina usa os arquivos oficiais em lote da Câmara,
preserva registros de origem separados para perfil e histórico e só deriva datas de eventos
explicitamente descritos como “Entrada” ou “Saída”. Ausência de evento não é convertida em
data da legislatura.

```bash
docker compose exec -T backend python -m app.jobs.import_camara_deputy_profiles
```

O scheduler executa essa atualização a cada 30 dias por padrão. As opções são
`DEPUTY_PROFILES_IMPORT_ENABLED` e `DEPUTY_PROFILES_IMPORT_INTERVAL_MINUTES`.

Se um backfill controlado dos endpoints individuais já estiver disponível como arquivos
locais, ele pode complementar o lote oficial sem tornar o Firecrawl uma dependência do
runtime:

```bash
docker compose run --rm \
  -v "$PWD/.firecrawl:/firecrawl:ro" \
  backend python -m app.jobs.import_camara_deputy_profiles \
  --supplemental-history-dir /firecrawl
```

O complemento preserva a URL oficial de cada resposta e tem precedência sobre o histórico
em lote mais antigo. Os arquivos intermediários não são versionados. O estado consolidado
e as limitações da categoria estão em [`docs/deputados.md`](../../../docs/deputados.md).

Para importar uma janela inicial de proposições, autores, tramitações e votações:

```bash
docker compose exec -T backend python -m app.jobs.import_legislation
```

Essa rotina consulta 20 itens de cada endpoint, detalha os registros e mantém as relações disponíveis pela fonte. O serviço `scheduler` repete essa coleta automaticamente a cada 60 minutos por padrão.

## Atualização automática

O Compose executa o agendador em um container separado da API. Por padrão, deputados são atualizados uma vez por dia e legislação a cada 60 minutos; as coletas também são tentadas na inicialização do serviço.

Os intervalos podem ser ajustados no `.env` com `DEPUTIES_IMPORT_INTERVAL_MINUTES`, `DEPUTY_PROFILES_IMPORT_INTERVAL_MINUTES`, `LEGISLATION_IMPORT_INTERVAL_MINUTES`, `SCHEDULER_ENABLED` e `SCHEDULER_RUN_ON_STARTUP`. O lock no PostgreSQL evita execuções concorrentes. Falhas ficam registradas em `import_runs` e não interrompem o ciclo seguinte.

Todos os intervalos `*_IMPORT_INTERVAL_MINUTES` exigem ao menos um minuto; configuração
inválida interrompe a inicialização antes de abrir o banco ou consultar fontes. Com
`SCHEDULER_ENABLED=false`, o processo termina sem abrir conexão. O import dos módulos e
a criação da aplicação HTTP não iniciam coletas. Apenas o processo explícito do scheduler
aplica a política `SCHEDULER_RUN_ON_STARTUP`.

## Explicações cidadãs autônomas

Quando `CITIZEN_EXPLANATION_PROVIDER=openai`, o scheduler seleciona proposições detalhadas
da Câmara, gera uma explicação, aplica regras determinísticas, executa uma segunda verificação
por IA e publica somente quando ambas aprovam. O intervalo padrão é de 30 minutos e o lote
padrão contém 10 tentativas. Falhas e rejeições ficam em `citizen_explanation_runs` e são
tentadas novamente; uma versão pública anterior permanece disponível até a substituição segura.

Esse job não roda ao importar módulos nem ao iniciar a API. A área `/revisao/projetos` apenas
consulta a auditoria e não oferece edição ou aprovação humana.

Senadores, CEAP e resultados eleitorais usam locks distintos, permitindo execuções
independentes sem bloqueios indevidos. Ao atualizar de uma versão com a chave compartilhada,
encerre as coletas em andamento e reinicie o scheduler antes de executar novos jobs;
processos antigos e novos não devem coexistir durante essa troca de chave. Cada job mantém
sua própria exclusão mútua. A competência mensal e o ano padrão das cargas manuais usam
`America/Sao_Paulo`, inclusive quando o sistema operacional está em UTC.

Resultados eleitorais do TSE são históricos e ficam desativados no scheduler por padrão, pois cada execução baixa um arquivo oficial grande. Para importar 2022 manualmente:

```bash
docker compose exec backend python -m app.jobs.import_election_results --year 2022
```

Depois da validação inicial, o job pode ser habilitado com `ELECTION_RESULTS_IMPORT_ENABLED=true` e uma periodicidade longa, como `ELECTION_RESULTS_IMPORT_INTERVAL_MINUTES=525600`.

Para corrigir vínculos de autorias já armazenadas sem repetir a coleta das fontes:

```bash
docker compose exec -T backend python -m app.jobs.link_authorships
```

O vínculo prioriza o ID presente na URL oficial do autor e usa o nome somente quando há uma correspondência única na mesma fonte. Comissões, órgãos e nomes ambíguos permanecem sem vínculo para evitar atribuição incorreta.

Se a fonte cair mais de 30% em relação ao último sucesso, a publicação é bloqueada para investigação. Não há exclusão automática de parlamentares ausentes. O lock PostgreSQL impede execuções concorrentes; uma execução abandonada é marcada como interrompida na próxima tentativa que obtiver o lock.

## Despesas da Câmara

`import_camara_expenses.py` importa o arquivo anual oficial da Cota para o Exercício da
Atividade Parlamentar (CEAP). A carga de 2026 tem mais de 120 mil registros e relaciona
as despesas ao deputado por ID ou, quando o arquivo usa o identificador interno da Cota,
por nome único normalizado. O valor é exibido como despesa documental, nunca como salário,
emenda ou gasto total do parlamentar.

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_camara_expenses --year 2026
```

O scheduler executa essa coleta diariamente por padrão. O ano pode ser alterado com
`CAMARA_EXPENSES_YEAR`; a integração pode ser desligada com
`CAMARA_EXPENSES_IMPORT_ENABLED=false`. A fonte publica o arquivo anual em
`https://www.camara.leg.br/cotas/Ano-{ano}.json.zip`. O identificador interno de cada
documento é armazenado como `ano:idDocumento`, pois a Câmara pode reutilizar o número em
exercícios diferentes. Para cobrir um mandato histórico, execute uma vez cada ano desejado.

## Votos nominais anuais da Câmara

`import_camara_votes.py` importa os arquivos CSV oficiais `votacoes-{ano}.csv` e
`votacoesVotos-{ano}.csv`. A primeira carga ativa é 2026. Ela atualiza as votações,
preserva partido e UF registrados no momento do voto e relaciona o deputado pelo ID
oficial. Registros ausentes no arquivo são ignorados; ausência nunca é convertida em
“Não”.

O scheduler executa essa carga semanalmente por padrão (`CAMARA_VOTES_IMPORT_INTERVAL_MINUTES=10080`),
sem misturar a atualização diária dos deputados e da CEAP. Para uma carga manual ou para
reprocessar outro ano:

```bash
docker compose exec -T backend python -m app.jobs.import_camara_votes --year 2026
```

## Remuneração mensal da Câmara

`import_camara_remuneration.py` consulta a lista oficial de deputados e as folhas mensais
publicadas pela Câmara. A coleta armazena o valor fixo bruto e a remuneração após descontos
obrigatórios, sem somar esses valores à CEAP. O vínculo usa o nome institucional do gabinete
publicado na fonte; registros sem correspondência segura ficam fora da publicação.

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_camara_remuneration
```

O scheduler repete essa coleta a cada 30 dias por padrão, usando a competência corrente no
fuso de Brasília. A opção pode ser desligada com
`CAMARA_REMUNERATION_IMPORT_ENABLED=false` ou ajustada com
`CAMARA_REMUNERATION_IMPORT_INTERVAL_MINUTES`.

## Equipe parlamentar da Câmara

`import_camara_staff.py` consulta os gabinetes oficiais e importa os servidores em exercício da
categoria “Secretário Parlamentar”. Para cada assessor, a coleta registra nome, cargo, nível,
área de atuação e o link individual de remuneração mensal. A página de remuneração é consultada
na mesma competência e normalizada em remuneração bruta, valor após descontos obrigatórios e
auxílios/outros. Gabinetes sem correspondência segura não recebem uma contagem inventada.

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_camara_staff
```

O scheduler repete a coleta a cada 30 dias por padrão, usando o mês corrente no fuso de Brasília.
A opção pode ser desligada com `CAMARA_STAFF_IMPORT_ENABLED=false` ou ajustada com
`CAMARA_STAFF_IMPORT_INTERVAL_MINUTES`.

Quando há uma coleta, o perfil oferece um relatório PDF individual com a identificação do
parlamentar, competência, totais do gabinete, composição nominal da equipe, cargo/nível,
remuneração bruta, valor após descontos, auxílios e consulta oficial. Os valores são os campos
publicados pela Câmara; descontos pessoais que a fonte não divulga podem fazer o valor recebido
ser menor. A Câmara pode atualizar a equipe e as folhas depois da coleta.

## Emendas parlamentares

`import_portal_amendments_open_data.py` é a coleta principal de emendas. Ela baixa o arquivo ZIP
público do Portal da Transparência, lê o CSV principal, cruza o nome do autor com os parlamentares
da Câmara e do Senado e grava apenas o resumo anual: quantidade, valor empenhado, liquidado e pago.
O ZIP não é armazenado no banco e a chave da API não é necessária.

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_portal_amendments_open_data
```

O scheduler executa essa carga uma vez por dia quando `PORTAL_AMENDMENTS_IMPORT_ENABLED=true`.
O ano pode ser alterado com `PORTAL_AMENDMENTS_YEAR`. A origem usada é o arquivo aberto oficial
em `https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares`; o perfil mantém
um link para a consulta oficial para conferência detalhada.

O job legado `import_portal_amendments.py` consulta a API por autor e exercício, mas não é usado
pelo scheduler. Ele permanece disponível para compatibilidade e exige uma chave emitida pelo
Portal. Se a API informar bloqueio por limite, não repetir chamadas: a carga por arquivo aberto
continua sendo a alternativa pública e sem token.

Depois da coleta, o perfil oferece `Baixar emendas deste parlamentar`. Esse CSV é gerado no clique
a partir dos registros detalhados normalizados no banco; ele contém somente o parlamentar do perfil
e o ano escolhido. A consulta oficial continua disponível no perfil para conferência direta na fonte.

O mesmo perfil também oferece `Baixar relatório PDF`. O PDF é montado sob demanda com a identidade
do De Olho na Política, o parlamentar consultado, totais de emendas e valores empenhados, liquidados
e pagos, além dos registros detalhados com código, ano, tipo, destino, programa/ação e fonte oficial.
Como a base aberta informa o ano da emenda, o relatório deixa explícito que ela não fornece uma data
individual de envio para cada registro.
