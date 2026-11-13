# Dados e privacidade

Frente DADOS-PRIVACIDADE. Revisão local em 11/11/2026. Política técnica de produto;
não representa certificação jurídica nem comprovação de controles de produção.

## Entrega e limites

Página pública: `/fontes-e-privacidade`, acessível no rodapé. Descreve fontes,
datas, lacunas, documentos públicos e como preparar uma conferência. Não recebe
solicitações: canal público e responsável pelo atendimento precisam ser definidos
antes do lançamento. Não inventar endereço de email ou prometer prazo sem operação.

O importador CEAP deixa de gravar `cnpjCPF`. A migration `0009` remove a coluna
`parliamentary_expenses.supplier_document`, inclusive valores antigos, sem alterar
nome do fornecedor, valores, número do comprovante ou identificadores da despesa.
API e UI não utilizavam a coluna removida. O downgrade repõe somente a coluna vazia;
não recupera os documentos eliminados. Aplicar junto à versão compatível da API e
dos coletores, com estes parados durante a migração. Nenhuma alteração foi aplicada
ao banco da aplicação ou à VPS nesta frente.

## Catálogo operacional

Os links e escopos abaixo refletem os adaptadores existentes no repositório. Não são
uma nova auditoria online das fontes nem uma certificação de completude da base.

| Fonte / chave | Conjuntos | Identificadores e limites |
| --- | --- | --- |
| Câmara / `camara` | Deputados, proposições, tramitações, votações, CEAP, remuneração, equipes | IDs oficiais por entidade; votação pode ter ID composto. CEAP usa `idDocumento`. Remuneração/equipe exigem ano e mês. Não usar nome como chave de identidade. |
| Senado / `senado` | Senadores, matérias, tramitações e votações | Códigos oficiais do Senado, separados dos da Câmara. Verificar cobertura por endpoint; não assumir equivalência entre casas. |
| Portal / `portal_transparencia` | Emendas e resumos por exercício | Código da emenda e ano; vínculos por nome normalizado existentes exigem revisão. Homônimos e autorias coletivas não devem ser atribuídos sem evidência. |
| TSE / `tse` | Resultado eleitoral associado ao parlamentar | Ano, turno, cargo, UF e ID da candidatura. Associação entre bases usa nomes/UF e pode falhar; não é prova de continuidade no mandato. |

`(source, external_id)` identifica registros dentro de uma entidade, não de todas
as tabelas. Para evidências, incluir também `entity`. UUID interno não substitui
ID oficial. Nomes normalizados são auxiliares de busca; vínculos existentes que
usam nome não devem ser descritos como identidade oficialmente confirmada.

## Proveniência e datas

- `source`, `source_url`, `collected_at` e `source_record_id` ligam as entidades à
  origem. `SourceRecord` guarda entidade, ID externo, versão do normalizador,
  hash, primeira/última observação e última execução. `ImportRun` registra status,
  horários e contagens. A URL de uma coleta pode apontar ao arquivo ou à página,
  enquanto a URL de uma entidade pode apontar ao detalhe oficial.
- O hash de `SourceRecord` é do recorte persistido. Alguns coletores financeiros
  armazenam apenas metadados do arquivo, como nome e contagem: o hash não atesta
  integridade do arquivo oficial inteiro nem permite reconstruir todas as linhas.
  Não apresentar esses registros como snapshots integrais ou arquivo histórico.
- `collected_at` é observação pelo portal, não publicação pelo órgão. Datas de
  evento, competência e atualização oficial são conceitos distintos; atualização
  oficial desconhecida deve permanecer desconhecida. Timestamps técnicos ficam
  com fuso; datas de negócio usam `America/Sao_Paulo` e `local_today()`.
- Nenhum catálogo estático substitui consulta de última coleta bem-sucedida por
  job e recorte. Falha de coleta não deve sobrescrever a data com sucesso fictício.
  Exibição uniforme de frescor por conjunto ainda é uma pendência de integração.

Os contratos financeiros expõem separadamente fonte, URL oficial, data de coleta,
período e identificador externo para despesas e assessores. O resumo do perfil usa
datas próprias para CEAP, remuneração, equipe e emendas; não reutiliza a data
cadastral do parlamentar como se fosse frescor financeiro.

## Lacunas e correções

Ausência de registro não significa zero, ausência parlamentar, abstenção, voto
contrário ou irregularidade. Lista vazia de votos não determina modalidade.
Filiação atual não deve ser aplicada retroativamente. Empenho, liquidação e
pagamento não são somáveis como se fossem gastos independentes. Autoria de emenda
não é recebimento pessoal. Recortes anuais e mensais precisam acompanhar totais.

Associações por nome foram restringidas: remuneração e gabinete de assessores exigem
correspondência exata e única após normalização; emendas só são vinculadas quando o
nome identifica uma única pessoa entre Câmara e Senado. Aproximações e homônimos permanecem sem vínculo.
Essa decisão reduz cobertura, mas evita atribuição sem identificador oficial comum.
As regras valem para novas coletas e reprocessamentos. Registros já armazenados por
normalizadores anteriores devem ser auditados antes de qualquer correção ou remoção;
esta entrega não apagou associações históricas automaticamente.

Nos relatórios PDF, totais financeiros só são apresentados quando todas as linhas
do campo possuem valor. Uma lacuna torna o total “Não informado”; valores ausentes
não viram zero. PDFs de equipe exibem a referência oficial do assessor, competência,
data de coleta, link da Câmara e aviso de privacidade. PDFs de emendas exibem ano-base,
data de coleta e link do conjunto aberto. O CSV de emendas inclui órgão publicador,
URL do conjunto e data de coleta em cada linha.

Fluxo operacional a implantar antes do lançamento:

1. Receber URL do portal, fonte, entidade, ID externo, período e descrição objetiva
   da divergência, sem solicitar documento pessoal ou comprovação de identidade por padrão.
2. Atribuir protocolo e responsável em ambiente restrito. Conferir fonte e datas;
   distinguir mudança posterior na origem de erro de vínculo, normalização ou apresentação.
3. Em possível exposição pessoal desnecessária, restringir o conteúdo afetado
   durante a avaliação. Não copiar o dado pessoal para tickets, logs ou notas públicas.
4. Corrigir a regra ou o vínculo e reprocessar o recorte de forma controlada.
   Não editar evidência antiga para parecer que a fonte sempre publicou o dado corrigido.
5. Registrar antes/depois mínimo, razão, referência, responsável e data da decisão;
   publicar nota quando a interpretação apresentada mudar. Revalidar caches e
   exportações. Sem ferramenta de correção implementada, esse fluxo é manual.

## Minimização e retenção

Coletar campos por lista permitida. Não persistir CPF, email pessoal, endereço
residencial, assinatura ou resposta bruta por conveniência. Nomes e atribuições
de servidores/fornecedores requerem finalidade ligada à atuação pública. Links
externos e comprovantes podem conter dados adicionais; a página pública avisa
esse risco, sem replicar os documentos. Dados de fonte pública não dispensam
análise de necessidade para republicação.

Política inicial proposta, **ainda sem rotina automática de expurgo**:

| Categoria | Retenção proposta / descarte |
| --- | --- |
| Dados normalizados de atuação pública | Enquanto necessários à cobertura declarada, com revisão anual de campos e períodos; sem exclusão indiscriminada de histórico legislativo. |
| Evidências mínimas vinculadas | Enquanto sustentarem registro publicado ou correção em apuração. Não remover evidência referenciada por FK. Revisão anual; excedentes sem vínculo são candidatos a descarte após 90 dias. |
| Downloads temporários | Liberar após processamento, inclusive em erro; persistência de arquivos para diagnóstico exige acesso restrito e prazo explícito de até 7 dias. Não arquivar respostas integrais por padrão. |
| Logs operacionais | 30 dias, sem tokens, payloads ou documentos pessoais. |
| Auditoria e protocolos encerrados | 90 dias propostos, com revisão de necessidade e exceções documentadas; notas públicas de correção não devem conter dados do solicitante. |
| Backups | 7 diários, 4 semanais e 3 mensais propostos em `04-seguranca-e-operacao.md`; acesso restrito, expiração e tratamento de restauração precisam ser verificados. |

Excluir de uma tabela não elimina versões em backups. Manter registro mínimo de
expurgos para reaplicá-los após restauração e antes de reabrir a publicação. Não
repovoar campos eliminados com coletor antigo. Exceções de preservação devem ter
motivo, responsável, acesso limitado e data de revisão.

## Pendências concretas

- Definir responsável, contato público de correções/privacidade e procedimento de atendimento.
- Implementar e medir retenção, acesso a evidências, limpeza de temporários/logs e expiração de backups.
- Revisar conteúdo já coletado fora da coluna removida e arquivos locais; esta entrega não certifica ausência de dados pessoais em textos livres, URLs ou backups.
- Melhorar evidência por arquivo para distinguir versões com metadados idênticos.
- Expor a data da última coleta bem-sucedida também em listagens agregadas fora do perfil.
- Substituir vínculos restantes baseados em nome por identificadores oficiais quando a fonte oferecer chave comum.

## Validação desta entrega

- `backend/.venv/bin/python scripts/test_backend.py`: 214 testes passaram com
  PostgreSQL efêmero, upgrade/downgrade/novo upgrade e `alembic check` sem divergência.
  Nenhuma consulta às fontes oficiais é feita pelos novos testes.
- Os testes de privacidade importam um arquivo sintético com CPF ou CNPJ, repetem
  a coleta e conferem descarte de identificadores e email extra, preservando nome,
  valor, ID externo e evidência mínima. Nenhum dado pessoal real foi usado.
- Frontend: typecheck com os pacotes de tipos explícitos, build e formatação dos
  arquivos da frente passaram.
- O typecheck padrão encontrou quatro diretórios vazios duplicados em
  `node_modules/@types` (`node 2`, `react 2` e equivalentes). A validação passou
  com os tipos explícitos; o build completo passou após mover temporariamente
  esses diretórios e restaurá-los ao final, sem alterar dependências do projeto.
- Compose: `docker compose --env-file .env.example config --quiet` passou.
- Playwright: página conferida em 1440 × 1000 e 390 × 844, com um título principal,
  destino do link de salto e nenhuma rolagem horizontal no celular. Sem erro de
  console; apareceram avisos de preload da marca no servidor de desenvolvimento.
- PDFs sintéticos de equipe e emendas foram renderizados com Poppler. A primeira
  versão do relatório de equipe criava uma página vazia para o aviso de privacidade;
  o aviso foi integrado ao bloco de origem e a versão final ficou com duas páginas
  úteis, sem sobreposição ou texto cortado. O relatório sintético de emendas ficou
  em uma página e manteve valores ausentes como “Não informado”.
