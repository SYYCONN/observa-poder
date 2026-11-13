# Frente LEGISLATIVO

Palavra-chave para retomada: **LEGISLATIVO**.

## Escopo

Proposições da Câmara e do Senado, autoria, tramitação, ementa, vínculos com votações e votos nominais. Os coletores permanecem separados da API; importar módulos não inicia consultas externas.

## Revisão de fidelidade dos dados

- O coletor da Câmara usa o detalhe da proposição para apresentação, ementa, resumo detalhado, palavras-chave, situação e endereço do texto integral, preservando o conteúdo no registro de proveniência. A resposta de listagem pode omitir campos do detalhe.
- As autorias da Câmara são atualizadas pelo detalhe oficial e ligadas ao parlamentar local quando há correspondência segura. Uma janela limitada de proposições antigas é enriquecida a cada execução para não sobrecarregar a fonte.
- Flags da Câmara aceitam booleanos e os valores `0`/`1`, inclusive strings. Outros valores permanecem desconhecidos; a string `0` não representa aprovação ou proponente.
- O coletor do Senado distingue aprovação (`A`), rejeição (`R`) e código desconhecido (`null`). Não calcula resultado com base nos votos importados.
- Votos sem posição explícita são ignorados, sem criar a posição artificial “registrado”. Não se deduz presença, ausência ou voto de parlamentares que não tenham registro importado.
- Listas de votações e votos do Senado aceitam tanto arrays quanto um único objeto.
- Horários legislativos sem offset usam `America/Sao_Paulo`; offsets explícitos mantêm o instante informado. Timestamps técnicos de coleta continuam em UTC. O ano padrão do arquivo anual de votos usa `local_today()`.
- As telas distinguem dados ainda não importados de dados não publicados pela fonte. A data da proposição é exibida no fuso de São Paulo.
- A modalidade `nominal` somente é registrada quando existe voto individual explícito. Ausência desse dado permanece como modalidade não identificada.

## Experiência de consulta

- Projetos: busca textual, filtros por ano e tipo, ordenação, paginação e estados de carregamento, erro e consulta vazia.
- Votações: busca textual, filtros por ano, resultado e modalidade, ordenação e paginação.
- Detalhe da proposição: resumo oficial, exemplo didático identificado como exemplo, autoria, tramitação, situação e acesso ao texto integral quando publicado.
- A seção "Entenda em 1 minuto" separa a explicação cidadã da ementa oficial. Apenas resultados aprovados pela esteira automática são publicados pela API.
- "Em poucas palavras" nunca reutiliza a ementa como tradução. Sem resultado seguro, a página informa que a automação ainda não publicou e preserva o acesso à fonte oficial.
- O scheduler gera a explicação com dados oficiais importados, executa validações determinísticas e solicita uma segunda verificação estruturada por IA. A publicação é atômica e não possui aprovação humana.
- As regras locais bloqueiam cópia da ementa, números ausentes da fonte, apresentação da proposta como lei vigente, julgamento político, promessa de efeito e resumo sem estrutura mínima.
- A segunda verificação reprova afirmações sem base, nomes ou números inventados, viés, confusão de vigência e linguagem pouco clara. A IA verificadora não publica diretamente: ela apenas produz um resultado estruturado que ainda precisa ser consistente.
- Falhas e reprovações não removem uma explicação pública anterior. O scheduler tenta novamente em ciclos posteriores; quando a fonte oficial muda, o hash muda e uma nova versão é produzida.
- Cada tentativa registra fonte, hash, provedor, modelos de geração e verificação, versão do prompt, resultados das duas validações, horários e código de erro. Não são armazenados segredos nem mensagens internas do provedor.
- A área restrita `/revisao/projetos` é somente um monitor técnico. Não contém campos de edição, responsáveis, aprovação, reprovação, publicação ou retirada manual.
- O monitor usa `CONTENT_ADMIN_TOKEN`. Sem essa variável, a rota responde como inexistente; o token digitado fica apenas na memória da página.
- O job atua somente sobre proposições da Câmara nesta etapa. A integração legislativa do Senado permanece fora desta automação.
- A automação não baixa nem interpreta o arquivo apontado pelo link de texto integral. Ela recebe ementa, resumo detalhado, situação, palavras-chave e endereços oficiais, com instrução explícita de não afirmar que leu o documento vinculado.
- A tramitação recebe uma explicação curta por tipo de evento, mantendo o texto oficial disponível em cada etapa.
- Votações relacionadas aparecem dentro do projeto com tipo de vínculo, resultado daquela etapa e aviso de que aprovação parcial não equivale a lei em vigor.
- Impactos, benefícios, custos e análise aparecem com estado transparente enquanto não houver fonte oficial suficiente; a interface não fabrica estimativas.
- Detalhe da votação: explica a modalidade, permite pesquisar e filtrar votos individuais e liga cada registro ao parlamentar quando identificado.
- As rotas antigas de listagem continuam compatíveis. As consultas paginadas usam `/propositions/search` e `/votings/search`.

## Validação

`backend/tests/test_legislation_normalization.py` verifica datas, retentativas, flags e posições ausentes. `backend/tests/integration/test_import_legislation.py` usa HTTP simulado e PostgreSQL isolado para verificar reimportação sem duplicatas, proveniência, detalhe da proposição, autoria, registros individuais e resultados desconhecidos. `backend/tests/test_api_contracts.py` cobre os contratos paginados e seus filtros. Os testes automatizados não coletam dados reais.

## Pendências e limites

- A janela recente não equivale à cobertura histórica completa. Não apresentar totais locais como todos os registros da Casa.
- O texto integral continua hospedado e consultado na fonte oficial; a aplicação guarda o endereço oficial, sem copiar o documento.
- O enriquecimento histórico da Câmara é gradual. Proposições ainda não revisitadas continuam exibindo o estado de dado pendente.
- O importador anual da Câmara ainda identifica a proveniência pelo endereço/ano/versão, sem hash do conteúdo do arquivo CSV. Uma revisão futura deve preservar a identificação de cada conteúdo coletado.
- A integração e os coletores do Senado não foram alterados nesta revisão de interface.
- Sem provedor e modelos configurados, a automação permanece desativada e nenhuma chamada externa é feita. A implantação precisa fornecer essas variáveis para cumprir a operação autônoma.

Nenhuma alteração de VPS ou deploy faz parte desta revisão.

## Resultado das verificações

- Runner completo `scripts/test_backend.py`, incluindo PostgreSQL limpo e migrations até `0017`: **197 passaram**.
- Suíte local sem banco de integração: **173 passaram e 24 foram ignorados**.
- Frontend: `npm run typecheck` e `npm run build` passaram.
- Black nos arquivos Python desta frente: passou.
- Compose: `docker compose --env-file .env.example config --quiet` passou.
- Fluxo real no navegador validado em desktop e em viewport móvel, sem erros ou avisos no console.

## Operação autônoma da explicação cidadã

Os endpoints restritos em `/api/v1/content-admin/citizen-explanations` são somente leitura. O token não deve ser commitado nem colocado em variáveis públicas do frontend.

Para habilitar a esteira no scheduler:

```env
CITIZEN_EXPLANATION_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_CITIZEN_GENERATION_MODEL=...
OPENAI_CITIZEN_VERIFICATION_MODEL=...
CITIZEN_EXPLANATION_INTERVAL_MINUTES=30
CITIZEN_EXPLANATION_BATCH_SIZE=10
```

Os dois modelos são escolhas explícitas de ambiente e não têm valor implícito no código. Se a configuração estiver ausente, o job retorna `disabled` e não publica. A chave nunca deve usar prefixo `NEXT_PUBLIC_`.

## Arquivos desta revisão

- `backend/app/integrations/legislation.py`
- `backend/app/jobs/import_legislation.py`
- `backend/app/jobs/import_camara_votes.py`
- `backend/app/api/routes/legislation.py`
- `backend/app/api/routes/citizen_content.py`
- `backend/app/modules/proposicoes/models.py`
- `backend/app/services/citizen_drafts.py`
- `backend/app/services/citizen_validation.py`
- `backend/app/jobs/generate_citizen_explanations.py`
- `backend/app/modules/proposicoes/schemas.py`
- `backend/app/modules/votacoes/schemas.py`
- `backend/alembic/versions/0014_proposition_context.py`
- `backend/alembic/versions/0015_citizen_explanations.py`
- `backend/alembic/versions/0016_citizen_explanation_audit.py`
- `backend/alembic/versions/0017_autonomous_citizen_explanations.py`
- `backend/tests/test_legislation_normalization.py`
- `backend/tests/integration/test_import_legislation.py`
- `backend/tests/integration/test_import_camara_votes.py`
- `backend/tests/test_api_contracts.py`
- `backend/tests/test_citizen_drafts.py`
- `frontend/src/app/projetos/page.tsx`
- `frontend/src/app/votacoes/page.tsx`
- `frontend/src/app/proposicoes/[id]/page.tsx`
- `frontend/src/app/votacoes/[id]/page.tsx`
- `frontend/src/app/revisao/projetos/layout.tsx`
- `frontend/src/app/revisao/projetos/page.tsx`
- `frontend/src/components/legislation-pagination.tsx`
- `frontend/src/lib/api.ts`
- `docs/08-legislativo.md`
- `docs/09-teste-leitura-cidada.md`
