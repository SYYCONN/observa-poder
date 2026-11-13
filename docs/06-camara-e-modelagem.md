# Câmara: validação, modelo e importação inicial

> Este documento registra o marco inicial de 29/10/2026. O estado consolidado da
> categoria, as cargas posteriores e as pendências para retomada estão em
> [Frente DEPUTADOS](deputados.md).

Implementação local em 29/10/2026. Escopo autorizado: validar fonte, modelar entidades legislativas e importar deputados. Sem telas novas, agendamento ou alteração da VPS.

## Fonte validada

- [Documentação oficial](https://dadosabertos.camara.leg.br/swagger/api.html).
- [Contrato OpenAPI](https://dadosabertos.camara.leg.br/api/v2/api-docs).
- [Lista atual de deputados](https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1&itens=100&ordem=ASC&ordenarPor=id).

Chamadas HTTPS reais sem token validaram lista, paginação, legislaturas, proposições, autores, tramitações, detalhe de votação e votos. O cliente usa certificados verificados; uma falha no trust store do Python global do Mac foi contornada utilizando o ambiente virtual com httpx/certifi, sem desabilitar TLS.

A documentação informa limite de 100 itens por página. A amostra atual retornou 513 deputados em seis páginas, na legislatura 57. Isso descreve a coleta feita, não uma constante para validar importações futuras. Sem parâmetros temporais, o endpoint retorna os deputados em exercício no momento da consulta. Para história é necessário outro recorte e endpoints complementares.

Não foi confirmado um teto oficial numérico de requisições por segundo. Adotamos uma chamada por vez, pausa de 250 ms entre páginas e até três tentativas para erros de transporte, HTTP 429, 500, 502, 503 e 504. Retry-After é respeitado até 60 segundos; espera solicitada maior encerra a execução para reprocessamento posterior. Erros permanentes, redirecionamentos e schema inválido não geram insistência automática.

## O que foi observado nos demais contratos

Autores podem ser órgãos ou outras entidades. A amostra de [autores da proposição 2620905](https://dadosabertos.camara.leg.br/api/v2/proposicoes/2620905/autores) contém uma comissão, por isso a relação com parlamentar é opcional.

O detalhe de votação possui objetos possíveis e efeitos, que não são necessariamente o objeto principal. A relação entre votações e proposições guarda o tipo do vínculo. A [votação 2620905-56](https://dadosabertos.camara.leg.br/api/v2/votacoes/2620905-56) foi examinada, mas não importada.

Votos ausentes não devem ser inventados. Lista de votos vazia não determina, sozinha, a modalidade da votação. A hora publicada sem fuso precisará de interpretação explícita em America/Sao_Paulo nos futuros normalizadores; timestamps técnicos de coleta ficam em UTC com fuso.

Uma consulta real de deputados com `idLegislatura=56` também respondeu com sucesso e confirmou o filtro histórico. A cobertura histórica exata de cada endpoint não foi exaurida. O contrato menciona consultas históricas, mas esta entrega não certifica completude de legislaturas anteriores. Uma amostra de proposição mostrou ano da identificação e data de apresentação diferentes; não inferir um a partir do outro.

## Modelo implementado

| Tabela | Responsabilidade |
| --- | --- |
| parliamentarians | Identidade por fonte e ID externo; nunca unir por nome |
| mandates | Vínculo observado com legislatura, UF e partido; datas individuais podem ser desconhecidas |
| mandate_observations | Mudanças observadas de UF/partido, ligadas à execução e à evidência |
| propositions | Identificador oficial, tipo, número, ano, ementa e apresentação |
| authorships | Autoria por proposição, inclusive institucional, ordem e condição de proponente |
| proceedings_events | Sequência, órgão, situação, despacho e relatoria documentada |
| votings | Objeto/descrição, data, órgão, resultado e modalidade quando conhecidos |
| voting_propositions | Associação muitos-para-muitos com tipo de relação |
| votes | Voto registrado e partido/UF do evento, sem usar filiação atual retroativamente |
| source_records | Evidência permitida da fonte, hash, versão do normalizador e primeira/última observação |
| import_runs | Execução, contagens, status, falha controlada e duração |

A migration `0001_legislative_schema.py` cria onze tabelas com chaves estrangeiras, restrições de unicidade e índices. Ela foi gerada e revisada antes de sua aplicação. Não há tabelas financeiras nesta etapa.

Parlamentares e mandatos são preenchidos agora. Proposições, autoria, tramitações, votações e votos estão modelados, mas seus coletores ainda não foram implementados. Os testes de migration não substituem a validação dos futuros normalizadores.

O vínculo em `mandates` não prova eleição, titularidade, início/fim do exercício ou continuidade na legislatura. Essas datas permanecem nulas. Mudanças de partido são observações a partir do início das coletas; não são uma reconstrução do histórico oficial. A URI do partido é preservada porque siglas podem ser reutilizadas.

## Proveniência e minimização

O registro de origem contém apenas ID, URI, nome parlamentar, partido/URI, UF, legislatura e URL da foto. Email, CPF e campos extras não são persistidos. Não é uma cópia integral bruta da resposta.

O hash identifica a versão desse recorte. `source_records.source_url` aponta para a página efetivamente consultada; `parliamentarians.source_url` aponta para a URI oficial do parlamentar. Conteúdo igual atualiza a última observação, sem duplicar evidência. Mudanças de partido A → B → A preservam três observações, mesmo reutilizando a evidência de conteúdo A.

## Operação

Na raiz, com o ambiente local ativo:

```bash
docker compose up -d --build backend
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.jobs.import_deputies
```

O comando retorna JSON com ID da execução, páginas, recebidos, inseridos, atualizados e inalterados. Falha retorna código de saída 1; a causa controlada fica em `import_runs`. Se o banco estiver totalmente indisponível, não é possível garantir persistência do erro nesse mesmo banco; a execução interrompida é reconciliada na tentativa seguinte.

As páginas são conferidas em memória e publicadas juntas numa transação. A coleta é limitada a 100 páginas e 2 MB por resposta. Links devem permanecer no endpoint oficial com os mesmos filtros, as páginas precisam estar completas e IDs repetidos são rejeitados. O PostgreSQL mantém um advisory lock durante toda a execução para evitar concorrência do mesmo job.

Em falha, o último conjunto válido permanece. Reexecutar reinicia pela página 1; os contadores de progresso não são checkpoint para retomar publicação parcial. Uma queda superior a 30% em relação à última coleta bem-sucedida bloqueia a publicação para investigação, sem exclusão automática.

Parlamentares ausentes numa coleta posterior não são apagados nem classificados automaticamente como afastados. Para identificar os observados no último sucesso, relacionar a evidência atual ao `last_run_id` da última execução bem-sucedida de `camara.current_deputies`. Não listar toda a tabela como se todos estivessem em exercício hoje.

## Validação reproduzível

```bash
backend/.venv/bin/python scripts/test_backend.py
```

O script cria e remove seu próprio PostgreSQL efêmero. Verifica upgrade, ausência de divergências no schema, downgrade, novo upgrade e testes automatizados. Não usa o volume do projeto nem acessa a Câmara nos testes. O CI executa o mesmo fluxo.

Cobertura: paginação, retries, limites, schema inválido, URL de paginação indevida, minimização, idempotência, homônimos, mudanças de partido, nova legislatura, transação integral, exclusão de detalhes internos dos erros, concorrência, execução interrompida e queda suspeita de registros.

## Resultado local observado

A primeira execução importou 513 parlamentares em seis páginas. A segunda retornou 0 inseridos, 0 atualizados e 513 inalterados. As tabelas de parlamentares, vínculos de legislatura, evidências e observações mantiveram 513 registros cada. Ambas as execuções constam como sucesso em `import_runs`.

Os 27 testes passaram com PostgreSQL real isolado. `alembic check` não encontrou diferença entre modelo e schema aplicado, e os endpoints de saúde continuaram respondendo HTTP 200 após a importação. A interface ainda não consulta essas tabelas.

## Próxima etapa

Expor consultas de parlamentares com paginação, filtros e proveniência; depois implementar telas. A atualização agendada e a coleta de proposições/votos permanecem fora desta entrega. Backup externo e separação de credenciais por função continuam necessários antes de produção.
