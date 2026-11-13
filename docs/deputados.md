# Frente DEPUTADOS

Palavra-chave para retomada: **DEPUTADOS**.

Estado em **06/11/2026**: desenvolvimento pausado após o fechamento do ciclo de
perfil parlamentar. As coletas automáticas já habilitadas continuam operando; a pausa
não desliga o scheduler nem altera dados publicados.

## Resultado entregue

### Identidade, situação e histórico

- A lista separa deputados em exercício de registros históricos por meio de
  `is_current`. Uma nova lista oficial completa marca como atuais somente os nomes
  presentes nela, sem apagar quem deixou de aparecer.
- O perfil informa visualmente quando o registro é histórico.
- Data de nascimento e períodos individuais de exercício vêm dos perfis e eventos
  oficiais da Câmara. Datas ausentes não são substituídas pelos limites da legislatura.
- O histórico preserva uma evidência própria, separada da evidência do perfil. Uma
  atualização posterior do arquivo em lote não sobrescreve um histórico individual
  mais específico.
- O importador só interpreta eventos explicitamente descritos como `Entrada - ...` ou
  `Saída - ...`. Ausência de saída não significa permanência no cargo.

### Eleição e mandato

- O resultado nominal de 2022 foi importado do conjunto oficial do TSE.
- A associação exige cargo, UF e nome oficial ou civil com correspondência exata e
  única. Não há associação aproximada silenciosa.
- O perfil diferencia corretamente “Não associado com segurança” de zero votos.
- Status eleitoral, total de votos e ano só aparecem quando publicados e associados
  com segurança.

### Atuação legislativa

- Projetos de autoria e votos nominais possuem paginação completa na API e no perfil.
- Os arquivos anuais oficiais de votações e votos de 2023, 2024, 2025 e 2026 foram
  carregados.
- Os votos preservam partido e UF informados no momento do evento. Ausência no arquivo
  nunca é convertida em voto “Não”.
- Parlamentares encontrados apenas nesses arquivos são preservados como registros
  históricos, com o ID oficial da Câmara.

### Transparência financeira e equipe

- A CEAP foi carregada para 2023, 2024, 2025 e 2026. O perfil informa o intervalo real
  dos dados, quantidade de documentos, valor líquido e glosas.
- O identificador de documento da CEAP passou a ser `ano:idDocumento`, porque a Câmara
  reutiliza `idDocumento` em exercícios diferentes. A migration `0013` corrige os
  registros anteriores.
- O detalhamento de despesas tem filtros de ano e período, paginação e acesso por
  teclado.
- Equipe parlamentar e remuneração permanecem vinculadas à competência e à fonte
  oficial. Para registro histórico sem gabinete atual, a interface mostra “Não
  aplicável ao registro histórico”, em vez de “Não coletado”.
- CEAP, remuneração, equipe e emendas permanecem conceitos separados; nenhum deles é
  apresentado como custo total do mandato.

### Interface e acessibilidade

- Lista e perfil identificam visualmente registros atuais e históricos.
- Filtros customizados podem ser operados por teclado.
- A paginação preserva os filtros ativos.
- Estados ausentes usam linguagem que distingue dado não publicado, dado não associado
  e valor zero.

## Cobertura local no encerramento

Estes números descrevem o PostgreSQL local após as cargas de 06/11/2026. Eles podem
mudar em coletas futuras e não são uma promessa de completude da fonte.

| Cobertura                                       |  Resultado observado |
| ----------------------------------------------- | -------------------: |
| Perfis da Câmara                                |                  628 |
| Deputados atuais                                |                  513 |
| Registros históricos                            |                  115 |
| Datas de nascimento                             |            628 / 628 |
| Inícios individuais explícitos                  |            614 / 628 |
| Fins individuais explícitos                     |            147 / 628 |
| Históricos individuais coletados no complemento | 115 / 115 históricos |
| Resultado eleitoral de 2022 associado           |            622 / 628 |
| Registros históricos com CEAP em 2023–2026      |            114 / 115 |
| Votos nominais importados em 2023–2026          |              470.127 |

Distribuição dos votos nominais importados: 128.679 em 2023, 116.400 em 2024,
174.646 em 2025 e 50.402 em 2026.

### Resíduos conhecidos, sem inferência

- Nove registros históricos não possuem evento explícito de saída nem no histórico
  individual consultado. As datas continuam nulas.
- Seis perfis não receberam associação eleitoral por falta de correspondência exata e
  única: Emanuel Pinheiro Neto, Guilherme Uchoa, Paulo Folletto, Augusto Puppio,
  Luiz Antônio Corrêa e Michele Collins.
- Michele Collins não possui documento CEAP associado no recorte de 2023 a 2026.
- Esses casos não devem ser resolvidos com correspondência aproximada. Uma associação
  futura exige um identificador oficial estável ou outra evidência inequívoca.

## Fontes e proveniência

Fontes oficiais utilizadas:

- [API de Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/swagger/api.html);
- [arquivo de deputados](https://dadosabertos.camara.leg.br/arquivos/deputados/json/deputados.json);
- [arquivo de histórico de deputados](https://dadosabertos.camara.leg.br/arquivos/deputadosHistorico/json/deputadosHistorico.json);
- histórico individual em `https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/historico`;
- arquivos anuais `votacoes-{ano}.csv` e `votacoesVotos-{ano}.csv` dos
  [arquivos da Câmara](https://dadosabertos.camara.leg.br/swagger/api.html);
- CEAP anual em `https://www.camara.leg.br/cotas/Ano-{ano}.json.zip`;
- [Resultados eleitorais de 2022 do TSE](https://dadosabertos.tse.jus.br/dataset/resultados-2022).

O arquivo em lote de histórico disponível durante a implementação estava defasado em
relação aos endpoints individuais. Por isso, foi feito um complemento local, controlado,
dos 115 registros históricos. O Firecrawl foi usado somente para obter as respostas
oficiais durante esse backfill; ele não faz parte do runtime, do scheduler ou da API.
Os arquivos intermediários ficam fora do versionamento. O importador aceita um diretório
suplementar com `--supplemental-history-dir` e mantém a URL oficial de cada resposta como
proveniência.

## Operação reproduzível

Aplicar migrations e atualizar a lista atual:

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_deputies
```

Atualizar perfis e históricos pelo lote oficial:

```bash
docker compose exec -T backend python -m app.jobs.import_camara_deputy_profiles
```

Reaplicar um complemento individual já capturado localmente:

```bash
docker compose run --rm \
  -v "$PWD/.firecrawl:/firecrawl:ro" \
  backend python -m app.jobs.import_camara_deputy_profiles \
  --supplemental-history-dir /firecrawl
```

Importar resultados eleitorais, votos e CEAP:

```bash
docker compose exec -T backend python -m app.jobs.import_election_results --year 2022
docker compose exec -T backend python -m app.jobs.import_camara_votes --year 2023
docker compose exec -T backend python -m app.jobs.import_camara_expenses --year 2023
```

Para votos e CEAP, repetir o comando para cada ano necessário. As cargas são
idempotentes. Perfis são atualizados mensalmente, a lista atual e a CEAP diariamente e
os votos anuais semanalmente, conforme as opções do scheduler.

## Validações do fechamento

- Backend completo: **171 testes passaram**.
- Migrations: upgrade, verificação de divergência, downgrade e novo upgrade passaram em
  PostgreSQL efêmero.
- Frontend: `npm run typecheck` e `npm run build` passaram.
- Compose: `docker compose --env-file .env.example config --quiet` passou.
- O arquivo alterado do perfil passou na verificação direcionada do Prettier.
- Perfil validado no navegador com paginação, filtros e estados atual/histórico. A
  captura local de referência está em
  `output/playwright/deltan-perfil-completo.png`.

A verificação global de formatação do frontend ainda aponta arquivos antigos e não
relacionados a esta frente: `src/app/metodologia/page.tsx`, `src/app/page.tsx` e
`src/app/votacoes/[id]/page.tsx`.

## Ordem técnica sugerida para uma retomada

1. Ampliar a coleta de projetos de autoria para além da janela recente, com checkpoint
   por ano ou legislatura e métricas de completude.
2. Criar uma fila própria, com cache e retomada, para atualizar históricos individuais
   diretamente da API oficial sem depender do Firecrawl. Ela deve continuar separada do
   servidor HTTP.
3. Procurar identificadores oficiais entre Câmara e TSE para auditar os seis resultados
   não associados, sem usar similaridade de nome como decisão final.
4. Auditar os documentos CEAP ignorados e o único registro histórico sem associação,
   preservando como ausente qualquer caso sem evidência inequívoca.
5. Investigar se existe fonte oficial arquivada para equipe e remuneração de gabinetes
   históricos. Se não existir, manter “Não aplicável” e documentar a limitação.
6. Adicionar testes de ponta a ponta para: registro atual, registro histórico, resultado
   eleitoral não associado, saída sem data explícita e CEAP multianual.
7. Expor métricas operacionais de atraso, queda de cobertura e último sucesso por job,
   com alerta sem apagar o último dado válido.

## Sugestão para a sequência do produto

Com DEPUTADOS em pausa, a próxima frente pode ser **SENADORES**, buscando paridade nos
mesmos conceitos de identidade, situação atual/histórica, atuação legislativa,
transparência, proveniência e estados de ausência. Depois, **GOVERNADORES** pode avançar
somente após a validação das fontes oficiais e do modelo específico do Executivo.

Nenhum deploy, alteração da VPS, remoção do Sycon, segredo ou Supabase fez parte deste
fechamento.
