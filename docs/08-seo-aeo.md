# SEO-AEO — base local e critérios de publicação

Esta frente não publica o portal e não altera a VPS. A palavra-chave para retomada é **SEO-AEO**.

## Implementado

- Títulos e descrições próprios por seção, Open Graph e Twitter summary.
- Canonical absoluto somente quando uma origem pública estiver configurada; detalhes ainda não recebem canonical genérico para outra página.
- `WebSite` na home e `AboutPage` na metodologia, em JSON-LD serializado com escape de `<`. Sem dados de pessoa, votos ou valores inventados, sem promessa de rich results.
- `/metodologia`, com respostas visíveis sobre origem, coleta, lacunas, ementas e votos; link no rodapé.
- Atalho de teclado “Pular para o conteúdo” nas consultas, na metodologia e nas páginas de fontes/analytics existentes durante a implementação.
- `/robots.txt` e `/sitemap.xml`, sem datas de modificação artificiais.

## Configuração

Variáveis do servidor Next, lidas também durante a geração estática:

| Variável | Padrão | Uso |
| --- | --- | --- |
| `SITE_URL` | ausente | Origem pública HTTPS, sem caminho, query ou credenciais. Não definir com domínio provisório. |
| `SEO_INDEXING_ENABLED` | desativado | Apenas o valor literal `true`, junto de `SITE_URL`, libera páginas elegíveis. |

Sem configuração, todas as páginas permanecem `noindex` e o sitemap fica vazio. Robots permite leitura para que mecanismos vejam o `noindex`; robots não é controle de acesso nem impede consulta pública. Prévia privada exige proteção própria.

No lançamento autorizado, essas variáveis precisam estar disponíveis **durante o build** e ter os mesmos valores no servidor. O Dockerfile e o Compose locais não as encaminham: a configuração de produção deverá incluir os argumentos/variáveis no builder antes de `npm run build`. Alterar somente o ambiente do runner não atualiza HTML já gerado. Não há alteração de infraestrutura nesta frente.

## Elegibilidade atual

Com liberação explícita, `/`, `/metodologia` e `/fontes-e-privacidade` entram no sitemap. A mesma lista controla a elegibilidade nos metadados. Novas rotas herdam `noindex` até receberem configuração própria. Deputados, senadores, projetos e votações carregam os registros no navegador; governadores e partidos são placeholders. Essas seções e todos os detalhes têm `noindex` próprio, mesmo com liberação global.

## Próximas entregas

1. Renderizar os registros e estados de erro no servidor, preservando filtros interativos; usar 404 real para identificador inexistente e distinguir indisponibilidade da API.
2. Gerar metadata e canonical individual por registro existente, com proveniência e data de coleta no HTML. Reutilizar a consulta para evitar divergência entre metadata e conteúdo.
3. Expandir o sitemap com paginação e apenas registros publicados; usar `lastModified` somente com data de atualização comprovada. Não anunciar URLs de filtros ou entidades sem conteúdo.
4. Revisar explicações cívicas com fontes oficiais consultadas e registrar referências. A metodologia atual descreve o funcionamento e limites do próprio portal; não é um guia jurídico.
5. Confirmar domínio, imagem social, revisão de acessibilidade com usuários e teste de rastreamento antes de liberar indexação. Não inserir métricas, rankings, reviews ou autoria não comprovados em dados estruturados.

## Validação

Executar `npm run build` e `npm run typecheck` em `frontend/`. Após adicionar rotas/layouts, tipos antigos em `.next/dev/types` podem conflitar; o build regenera os tipos. Conferir o HTML gerado, canonical, JSON-LD, robots e sitemap tanto sem configuração quanto com a configuração pública de teste. Nenhum acesso a banco ou coleta é necessário para essas páginas estáticas.

### Evidências desta entrega

- `npm run build`: aprovado; `npm run typecheck`: aprovado após regenerar os tipos de rotas.
- `docker compose --env-file .env.example config --quiet`: aprovado.
- Conferência automatizada do HTML estático gerado: títulos das seções, `noindex`, um destino de atalho por página e um H1 na home/metodologia; robots sem sitemap anunciado e XML sem URLs no modo local.
- Verificação das funções de configuração em Node: ausência de domínio, prévia bloqueada, liberação explícita, canonical absoluto, seções incompletas bloqueadas e rejeição de origem HTTP/com caminho.
- Não houve alteração de dependências, backend, banco ou VPS. Testes Python não foram executados, pois não houve alteração no backend. A revisão com leitores de tela e a validação HTTP do build público configurado ficam para a etapa de publicação.


### Revisão de 11/11/2026

- Home com links para as consultas e indicação das seções em preparação. Metodologia e catálogo de fontes ligados entre si. A metodologia explica como citar um registro e distinguir a fonte da explicação do portal.
- Proposições e votações exibem órgão, identificador na fonte e data da coleta do registro no horário de Brasília. O elemento HTML `time` preserva o instante original. A data exibida se refere à ficha principal.
- Builds local e com origem HTTPS fictícia aprovados. Conferidos HTML, canonical, JSON-LD, robots e os três endereços do sitemap com indexação de teste. O build local final saiu com `noindex` e sitemap vazio.
- Chrome em 375 e 1280 px: foco do atalho, um H1 no conteúdo principal e largura das três páginas editoriais. Conferidos órgão, identificador, horário da coleta e link oficial em uma proposição e uma votação. O navegador recebeu dados da API local com ajuste de CORS limitado à sessão de teste.
