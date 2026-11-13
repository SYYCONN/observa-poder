# Forma de trabalho e decisões

Status: processo proposto. Data: 29/10/2026.

## Decisão confirmada

O usuário autorizou iniciar a programação pela estrutura profissional do projeto. A primeira entrega implementa a base local com a stack recomendada. Contratação, publicação e substituição do Sycon na VPS permanecem fora desta etapa.

## Registro de decisões

| ID | Tema | Recomendação | Estado |
| --- | --- | --- | --- |
| D01 | Etapa atual | Implementar estrutura técnica local | Autorizado pelo usuário após o planejamento |
| D02 | Primeira integração | Câmara: validar API, modelar e importar deputados | Autorizado pelo usuário; expansão do lançamento ainda a definir |
| D03 | Atualização | Coleta por API com revisão de exceções | Importador executável implementado; agendamento pendente |
| D04 | Stack | Next.js/TypeScript + FastAPI + PostgreSQL | Adotado na base inicial conforme recomendação apresentada |
| D04a | Hospedagem do banco | Banco em Docker na VPS, sem Supabase; PostgreSQL proposto | Docker e ausência de Supabase confirmados pelo usuário |
| D05 | Hospedagem | Dedicar a Hostinger KVM 1 ao projeto, substituindo o Sycon Suite | Intenção confirmada pelo usuário; transição e capacidade ainda não validadas |
| D06 | Orçamento | R$ 80/mês existentes; reserva proposta de R$ 100–150/mês total com domínio e backup | Custo da VPS informado; teto, renovação e backup pendentes |
| D07 | Audiência | Cloudflare Web Analytics sem cadastro público | Proposto |
| D08 | Segurança | Política do documento 04 como critério de lançamento | Proposto |
| D09 | Conteúdo | Fontes oficiais, sem rankings opinativos ou IA editorial inicial | Proposto |
| D10 | Cobertura histórica | Ano do lançamento e proposições relacionadas | Proposto |
| D11 | Operação | Responsável, suplente, alertas e manutenção | Pessoas e disponibilidade a definir |
| D12 | Identidade | Nome provisório De Olho na Política | Marca, domínio e titularidade a definir |
| D13 | Ministros e municípios | Ministros de Estado; piloto regional posterior | Confirmar tribunais, prefeitos e territórios |

Registrar escolha, data, motivo e alternativas descartadas quando uma decisão for confirmada. Não converter recomendação em aprovação por ausência de resposta.

## Etapas de trabalho

1. **Planejamento atual:** revisar estes documentos, escolher o recorte, teto de custo e prioridades. Saída: baseline aprovada com pendências não bloqueantes explicitadas.
2. **Após autorização para implementar, prova técnica:** validar chamadas reais, credenciais, amostra de votos, paginação, volume e duração de atualização. Saída: relatório de viabilidade e eventuais ajustes na arquitetura.
3. **Desenho da experiência:** mapa de navegação, wireframes e identidade visual, com revisão em celular e desktop. Saída: telas e estados de carregamento, erro e dados ausentes definidos.
4. **Primeiro fluxo completo:** fonte oficial → banco → API → busca/perfil/proposição/votação. Saída: entrega utilizável com dados reais e testes relevantes.
5. **Preparação de lançamento:** segurança, restauração, analytics, privacidade, monitoramento, revisão editorial e carga. Saída: checklist e riscos conhecidos.
6. **Publicação planejada:** escolher contas e domínio, disponibilizar release validada, verificar serviço e recuperação. Contratação e publicação ficam para instrução específica posterior.
7. **Operação:** medir audiência, qualidade e custos; priorizar a próxima fonte a partir desses resultados.

Prazos serão estimados após escolher escopo e validar as fontes. Não prometer data de lançamento sem conhecer disponibilidade de trabalho, dados e critérios de aprovação.

## Organização do desenvolvimento futuro

- Repositório independente do Sycon Suite, com documentação, frontend, backend e infraestrutura separados.
- Backlog simples: a definir, pronto para desenvolver, em andamento, em revisão e concluído.
- Cada tarefa descreve problema, entrega, critérios de aceite, dados envolvidos e forma de validação.
- Mudanças pequenas em branches; revisão de diff e verificações antes de integrar à main. Commits curtos e descritivos.
- Ambiente local e homologação isolados de produção. Homologação local inicialmente; serviço permanente acrescenta custo.
- Nenhum segredo, dump, backup ou dado pessoal desnecessário no repositório.
- Novas migrations versionadas; backup antes de mudanças destrutivas e plano de retorno. Reverter aplicação pode não reverter banco; avaliar compatibilidade antes do deploy.
- Atualizar documentação junto com mudanças de escopo, dados, custos ou controles.

## O que significa “concluído”

Funcionalidade atende aos critérios de aceite, dados foram conferidos, validações relevantes passaram e limitações estão documentadas. Cada entrega informa o que mudou, testes executados, testes não executados e motivos. Segurança e acessibilidade fazem parte do aceite.

Testes prioritários: normalização, idempotência, associação correta de votos/projetos, datas, valores monetários, permissões, falha de fonte e navegação principal. Testes não devem apenas repetir a implementação.

Antes do lançamento: executar build, testes, verificação de segredos/dependências, checagem de portas, teste de restauração e ensaio de carga do cenário definido. A base inicial já possui build, checagem de tipos e testes de saúde da API; validações de produção continuam pendentes. Consultar README para comandos e limites.

## Como tomaremos decisões juntos

O usuário define prioridades de produto, orçamento, cobertura e publicação. A implementação apresenta recomendações técnicas e impactos para essas escolhas. Decisões rotineiras dentro do escopo aprovado seguem sem interrupções constantes; mudanças materiais de custo, exposição de dados ou escopo voltam para revisão.

Revisões em marcos de entrega, com resultados demonstráveis e lista curta de pendências. Mudança de escopo deve indicar benefício, impacto no prazo/custo e o que sai ou é adiado.

## Próximas escolhas

Para fechar a base: escolher primeiro lançamento e faixa mensal. Depois confirmar stack, janela histórica, responsáveis por operação e sentido de “ministros”. Antes da contratação: domínio, fornecedor, titularidade das contas e política de privacidade. Antes do lançamento: evidências de segurança, recuperação e qualidade.
