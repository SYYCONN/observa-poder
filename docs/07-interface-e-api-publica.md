# Interface e API pública inicial

Implementação local: 29/10/2026.

A página inicial apresenta a cobertura disponível, busca por nome ou ID da Câmara, filtro por UF, cartões de parlamentares e link direto à fonte oficial. Cada cartão leva ao perfil interno, que mostra identificação, partido/UF observados, legislaturas registradas, data da coleta e URI oficial.

O layout atende celular e desktop, com estados de carregamento, erro e lista vazia. A interface não cria notas, rankings ou interpretações sobre os parlamentares. A página continua com `noindex` enquanto o produto estiver em validação.

O cliente usa `NEXT_PUBLIC_API_URL`, incorporado no build Docker. No ambiente local atual, o site usa `http://localhost:3001` e consulta a API em `http://localhost:8001/api/v1`. Em produção, a variável deve apontar para o domínio/proxy do projeto.

## Rotas implementadas

| Método | Rota | Função |
| --- | --- | --- |
| GET | `/api/v1/parliamentarians` | Lista paginada; `search`, `state`, `party`, `status`, `limit` e `offset` |
| GET | `/api/v1/parliamentarians/{id}` | Detalhe por UUID interno e histórico de mandatos observados |
| GET | `/api/v1/parliamentarians/{id}/financial-expenses` | Despesas CEAP normalizadas e paginadas; `year`, `month` (`YYYY-MM`), `date`, `date_from`, `date_to`, `limit` e `offset` |
| GET | `/api/v1/parliamentarians/{id}/staff` | Equipe nominal paginada da competência mais recente ou de `year` e `month` |
| GET | `/api/v1/parliamentarians/{id}/authored-propositions` | Projetos de autoria paginados |
| GET | `/api/v1/parliamentarians/{id}/votes` | Votos nominais paginados |
| GET | `/api/v1/propositions` | Lista paginada de proposições já importadas |
| GET | `/api/v1/votings` | Lista paginada de votações já importadas |

As respostas incluem origem e data de coleta. `limit` é limitado a 100, `offset` não pode ser negativo e consultas textuais têm tamanho máximo. A API libera apenas GET via CORS; não existe endpoint público de escrita.

A resposta de `/parliamentarians` tem o formato `{ items, total, limit, offset }`. `total` é o total encontrado depois dos filtros, enquanto `items` contém somente a página solicitada. A tela de deputados usa 20 registros por página, organizados em duas colunas de até 10 linhas, e a tela de senadores usa 24 registros por página. Ambas oferecem navegação anterior/próxima; assim, os 513 deputados atuais não ficam limitados aos primeiros 100.

O filtro de parlamentares seleciona o mandato de maior legislatura observado por pessoa. A situação atual vem da presença na lista oficial mais recente: ausentes de uma nova coleta não são apagados e passam a ser consultáveis como registros históricos.

## Proposições e votações

As tabelas, endpoints e importadores já existem. A carga local mantém proposições,
autores, tramitações e votações, com vínculos aos perfis quando a fonte fornece o
identificador oficial. O perfil também exibe projetos de autoria e os votos nominais
publicados para o parlamentar. Não há registros de demonstração nem inferências a
partir de notícias.

O importador usa uma janela controlada de 20 itens por endpoint e é executado pelo
scheduler Docker. A carga anual de 2026 da Câmara também está disponível pelo comando
`import_camara_votes.py`; ela usa os arquivos oficiais de votações e votos para preencher
registros individuais. Os anos de 2023 a 2026 estão carregados localmente. Suplentes e
ex-deputados identificados nesses arquivos aparecem como registros históricos. Cada etapa
mantém origem, tipo exato da relação e os limites de publicação já usados no coletor de
deputados. Anos anteriores serão adicionados em cargas controladas.

## Verificações realizadas

- TypeScript e build Next.js passaram.
- API respondeu lista, busca, detalhe e listas legislativas vazias com HTTP 200.
- CORS respondeu somente à origem local configurada.
- PostgreSQL continuou saudável e a migration permaneceu aplicada.
- Os containers foram reconstruídos com a URL da API local.

Ainda não é uma publicação de produção: faltam domínio/proxy TLS, cache, analytics, monitoramento, backup externo e revisão de acessibilidade com usuários.
