# Contexto compartilhado dos agentes

**Projeto:** De Olho na Política  
**Atualizado em:** 11/11/2026  
**Ambiente:** desenvolvimento local; nenhuma alteração de produção foi autorizada nesta frente.

Este é o contexto mínimo que todo agente deve ler antes de trabalhar. Ele evita que um
agente trate uma tela parcial como cobertura completa, repita uma integração já pronta ou
apague uma limitação documentada.

## 1. O produto

O De Olho na Política é um portal informativo sobre política brasileira. A proposta é
organizar dados públicos oficiais para cidadãos, jornalistas e pesquisadores, sempre com
fonte, identificador, data de coleta e limites de cobertura visíveis.

O produto **não** é um site de campanha, ranking de honestidade, classificador de ideologia
ou sistema de acusação. Ausência de dado não significa zero, voto contrário, ausência,
culpa ou irregularidade.

Princípios editoriais obrigatórios:

- distinguir texto oficial de explicação cidadã;
- preservar a fonte original e o identificador externo;
- separar data do evento, competência e data da coleta;
- nunca inferir voto, autoria, gasto ou continuidade de mandato;
- separar empenhado, liquidado, pago e transferido;
- manter lacunas explícitas e corrigíveis;
- não republicar dados pessoais desnecessários presentes em documentos oficiais.

## 2. Arquitetura atual

```text
frontend/                 Next.js, React, TypeScript e Tailwind
  src/app/                páginas e rotas públicas
  src/components/         UI compartilhada e componentes de domínio
  src/lib/                clientes HTTP e utilitários
backend/                  FastAPI, SQLAlchemy, Alembic e PostgreSQL
  app/api/                rotas HTTP e health checks
  app/core/               configuração, segurança e datas
  app/db/                 sessão e modelos registrados
  app/modules/            regras e modelos por domínio
  app/integrations/       clientes/normalizadores de fontes oficiais
  app/jobs/               coletores executáveis
  alembic/                migrations versionadas
infra/docker/             imagens locais
compose.yaml              db, backend, scheduler e frontend
docs/                     decisões, operação e instruções de agentes
```

Banco: PostgreSQL 17 em Docker, sem Supabase e sem porta pública no Compose local.
Coletas: jobs separados do servidor HTTP, executados pelo `scheduler`; importar um módulo
não pode iniciar coleta externa.

Ambiente local atualmente usado neste computador:

- site: `http://localhost:3001`;
- API: `http://localhost:8001`;
- API Swagger: `http://localhost:8001/docs`;
- serviços: `db`, `backend`, `scheduler` e `frontend`.

Datas de negócio usam `America/Sao_Paulo` e `local_today()`. Valores monetários usam
Decimal no domínio. Segredos ficam em `.env` e nunca entram no Git.

## 3. O que já foi implementado

### Base e operação

- FastAPI, PostgreSQL, SQLAlchemy e Alembic;
- health checks de liveness/readiness;
- Compose local com banco isolado;
- scheduler separado da API;
- importações idempotentes e registros de `import_runs`;
- proveniência com fonte, URL, identificador, hash/normalizador e data de coleta;
- filtros e APIs paginadas com `{ items, total, limit, offset }`;
- testes de backend, typecheck/build do frontend e validações de Compose já executados em ciclos anteriores.

### Câmara dos Deputados

- lista atual de 513 deputados;
- 115 registros históricos preservados sem apagar identidade anterior;
- perfis, nascimento e eventos individuais de exercício quando publicados;
- filtros por nome/ID, UF, partido e situação;
- associação eleitoral de 2022 quando cargo, UF e nome têm correspondência segura;
- autoria, proposições, tramitação, votações e votos nominais;
- arquivos anuais de votos de 2023, 2024, 2025 e 2026 carregados localmente;
- CEAP de 2023 a 2026, com documentos, líquido e glosas;
- subsídio bruto nominal de referência;
- equipe parlamentar e remuneração por competência;
- relatório PDF de equipe parlamentar;
- emendas de autoria pelo arquivo anual aberto do Portal da Transparência;
- perfil e listagem com fallback de iniciais quando a foto oficial não responde;
- listagem em duas colunas, com até dez linhas por coluna e paginação.

### Senado Federal

- lista de senadores em exercício;
- filtro de estado e partido;
- matérias, autores, tramitação, votações e votos publicados em janela controlada;
- conversão de datas respeitando `America/Sao_Paulo` e offsets explícitos;
- fonte `senado` preservada nos contratos públicos.

### Legislativo e explicação cidadã

- páginas de projetos, detalhe de proposição e detalhe de votação;
- ementa, autores, tramitação, situação e texto oficial quando a fonte publica o link;
- separação entre ementa oficial e explicação “Em poucas palavras”;
- validação determinística e segunda verificação estruturada para explicações, quando configurada;
- nenhuma explicação aprovada pode afirmar que uma proposta virou lei sem evidência.

### Transparência, privacidade e interface

- modal legível para despesas CEAP, com filtros de ano, mês, data exata e intervalo;
- links para comprovantes oficiais sem baixar/republicar o arquivo;
- aviso de que o comprovante pode conter dados pessoais publicados pela própria fonte;
- remoção de CPF/CNPJ de fornecedor da persistência local;
- página de fontes e privacidade;
- PDFs de emendas e equipe com logo, resumo, legenda e proveniência;
- home, listas, perfis e detalhes com identidade visual consistente em revisão contínua;
- fallback visual para fotos oficiais indisponíveis.

## 4. Pendências e bloqueios conhecidos

O próximo agente deve verificar o estado real antes de assumir que uma pendência continua
igual. A documentação anterior registra estes pontos relevantes:

1. **Migrations:** há colisão documentada de revisão `0009` entre analytics e minimização
   de documentos. A cadeia precisa ser resolvida por uma única frente de base compartilhada,
   sem editar migrations já aplicadas de forma destrutiva.
2. **QA:** o último checklist marcou release bloqueado; houve falhas de formatação em
   arquivos antigos, teste de CORS, contrato de offset de data e navegação por teclado no
   filtro customizado.
3. **Deputados:** ampliar autoria histórica, substituir o backfill dependente de Firecrawl
   por fonte oficial direta, auditar seis associações eleitorais sem correspondência segura,
   revisar CEAP histórico e expor métricas de frescor por job.
4. **Senadores:** resolver migrations/CORS, distinguir snapshots atuais de históricos,
   ampliar histórico individual e revisar a janela limitada de votações.
5. **Projetos e votações:** a cobertura recente não é histórico integral; ainda não se
   guarda cópia do texto integral e o CSV anual precisa de identificação de versão/hash.
6. **Analytics:** ativação é explícita e deve ser privada; faltam decisão final de eventos,
   retenção, dashboard operacional e monitoramento de erros sem coletar PII.
7. **SEO/AEO:** páginas continuam `noindex` sem `SITE_URL` e `SEO_INDEXING_ENABLED=true`;
   falta renderização adequada de registros no servidor, canonical por entidade e revisão
   antes do lançamento público.
8. **Segurança:** faltam HTTPS/Nginx, Cloudflare ou borda equivalente, firewall, backup
   externo testado, restauração, alertas, revisão de dependências e teste de carga.
9. **Dados/privacidade:** falta responsável e canal de correções, rotina de retenção/expurgo,
   auditoria de URLs/textos livres e revisão dos vínculos feitos por nome.
10. **Produção:** não houve deploy, alteração da VPS ou remoção do Sycon Suite.

## 5. Regras de trabalho entre agentes

- Ler este arquivo e `AGENTS.md` antes de editar.
- Executar `git status --short --branch` antes de começar.
- Trabalhar somente na área designada; não fazer refatoração oportunista de outra frente.
- Não usar `git reset --hard`, `git checkout --`, remover volumes ou apagar dados.
- Não editar uma migration antiga já aplicada; criar nova revisão quando necessário.
- Não commitar `.env`, tokens, dumps, PDFs pessoais, respostas brutas ou backups.
- Não alterar VPS, DNS, proxy, produção ou Sycon sem pedido explícito.
- Não rodar coleta ampla apenas para testar uma tela; usar fixtures/mocks quando possível.
- Ao terminar, informar arquivos, decisão, testes, limitações e próximo passo.

### Integração recomendada

O chat principal coordena prioridades e integra resultados. Para mudanças de código, o
ideal é um agente escritor por conjunto de arquivos, com revisão posterior do agente QA.
Os chats podem compartilhar o mesmo checkout local, mas não devem editar o mesmo arquivo ao
mesmo tempo. Quando o trabalho crescer, usar branches/worktrees separados e integrar em
ordem, sempre com build, testes e revisão de diff.

Fluxo de cada ciclo:

1. definir problema e critério de aceite;
2. agente responsável auditar o estado atual;
3. implementar a menor mudança completa;
4. executar validações da frente;
5. QA revisar regressões e acessibilidade;
6. chat principal integrar e atualizar a documentação;
7. só então iniciar a próxima frente dependente.

## 6. Ordem recomendada para os próximos ciclos

1. Central/API + Dados/Privacidade: corrigir migrations e contratos compartilhados.
2. QA/Release: estabelecer baseline verde e checklist repetível.
3. Deputados: concluir pendências de cobertura e UX do perfil/lista.
4. Projetos/Votações: ampliar histórico e garantir fidelidade da explicação.
5. Senadores: alcançar paridade de identidade, histórico e fontes.
6. Segurança: endurecer a aplicação antes de qualquer publicação.
7. Analytics: ativar métricas apenas após política de privacidade e retenção.
8. SEO/AEO: liberar indexação somente com domínio, conteúdo renderizado e revisão final.

