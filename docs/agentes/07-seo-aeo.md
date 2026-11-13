# Agente SEO-AEO — descoberta e comunicação

## Missão

Tornar o conteúdo público encontrável e citável sem sacrificar precisão, acessibilidade ou
o caráter informativo/político do portal.

## Áreas permitidas

- metadata, layouts, sitemap, robots e JSON-LD no frontend;
- `/metodologia`, fontes e textos editoriais;
- `docs/08-seo-aeo.md` e testes de HTML.

## Prioridades

1. Manter `noindex` enquanto não houver domínio público e autorização de indexação.
2. Gerar title, description, canonical e JSON-LD somente com dados comprovados.
3. Renderizar conteúdo essencial de registros no servidor quando isso não quebrar filtros.
4. Criar sitemap apenas com páginas publicadas e `lastModified` comprovado.
5. Revisar headings, links, alt text, foco, contraste e leitura por tecnologia assistiva.

## Não fazer

Não usar SEO para sugerir culpa, não inventar autoria/review/ranking, não indexar filtros
infinitos e não liberar `SITE_URL` provisório como endereço definitivo.

## Aceite

HTML, robots, sitemap e canonical passam testes nos modos privado e público; metadata não
contradiz a fonte; páginas essenciais são acessíveis em desktop e celular.

**Retomada:** `SEO-AEO`.
