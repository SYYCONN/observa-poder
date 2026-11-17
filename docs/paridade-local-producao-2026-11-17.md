# Paridade entre localhost e produção em 17/11/2026

A auditoria geral está em [auditoria-geral-dados-2026-11-17.md](auditoria-geral-dados-2026-11-17.md). Ela amplia esta comparação inicial com consultas de todas as áreas do banco e análise dos endpoints.

A comparação usa contagens dos endpoints públicos e os quatro primeiros perfis em exercício de cada Casa, associados pelo identificador oficial. As contagens medem a cobertura dos catálogos no momento da consulta. Os resultados por perfil descrevem a amostra.

| Dados consultados | Localhost | Produção | Próximo passo |
| --- | --- | --- | --- |
| Equipe de AJ Albuquerque, novembro | 14 assessores e nenhuma ficha com valores | 13 assessores e nenhuma ficha com valores | Conferir a folha oficial de novembro quando publicada. Manter a data de cada fotografia da equipe. |
| Equipe de AJ Albuquerque, outubro | 14 assessores e 14 fichas com valores | Nenhuma equipe para a competência | Recuperar a fotografia de outubro registrada no ambiente local com sua proveniência. |
| Proposições da Câmara | 858 | 136 | Pelo identificador oficial, 853 só no local, 131 só em produção e 5 em ambas. Recuperar as faltantes em lotes. |
| Proposições do Senado | 636 | 91 | Pelo identificador oficial, 545 só no local e 91 em ambas. Recuperar as faltantes em lotes. |
| Votações da Câmara | 42.752 | 43.643 | Preservar a cobertura de produção e medir lacunas por identificador e ano ao definir o recorte. |
| Votações do Senado | 58 | 50 | Pelo identificador oficial, 8 só no local e 50 em ambas. Atualizar a janela oficial e conferir a recuperação. |
| Parlamentares em exercício | 513 deputados e 81 senadores | 513 deputados e 81 senadores | Manter a atualização das listas oficiais. |
| Parlamentares históricos | 115 deputados | 131 deputados | Preservar os cadastros históricos de produção. |
| Eleição, exercício e nascimento | Campos preenchidos nos quatro deputados amostrados | Campos preenchidos nos mesmos quatro deputados | Manter as cargas atuais e revisar vínculos ausentes caso a caso. |
| Remuneração do deputado | Outubro de 2026 nos quatro perfis consultados | Mesma competência nos quatro perfis | Atualizar quando houver nova folha. |
| CEAP | Disponível nos quatro deputados, com contagens diferentes | Disponível nos mesmos perfis, com contagens diferentes | Reconciliar por ano e identificador de documento. Respeitar correções da fonte e os cadastros históricos já carregados. |
| Emendas de 2026 | Mesma disponibilidade e contagens nos oito perfis consultados | Mesma disponibilidade e contagens nos oito perfis consultados | Manter a atualização pela fonte oficial. |

## Equipes e folha mensal

O banco local tem 9.294 registros nominais de equipe em outubro, dos quais 9.131 têm os três campos financeiros. A fotografia local foi coletada em 30/10/2026 no horário de Brasília. Nas duas APIs, novembro apresenta os nomes sem valores no perfil de AJ Albuquerque. Na amostra oficial, uma ficha consultada com novembro no endereço respondeu com a folha de outubro. A competência exibida dentro da ficha é a referência para gravar os valores.

A recuperação de outubro deve usar a fotografia contemporânea da equipe. A listagem pública de gabinetes retorna a equipe em exercício no momento em que é consultada. Consultar a folha de outubro para a lista atual corresponderia a outro conjunto de pessoas.

Para recuperar outubro em produção, validar o registro de origem da fotografia local e exportar exclusivamente o resumo e os campos nominais já publicados, com a competência, a data de coleta, os links oficiais e a proveniência. Associar cada gabinete pelo par de fonte e identificador oficial do parlamentar. Ensaiar a importação em PostgreSQL isolado e confrontar os totais do ensaio com os da origem. A carga deve inserir competências ausentes em uma transação e preservar competências já publicadas. Validar na API da VPS que o perfil de AJ oferece outubro e novembro após a recuperação, e que o PDF selecionado corresponde à competência.

No código, a API já oferece as competências coletadas, a tela permite escolher uma delas, e o PDF explica a cobertura de cada campo. Os totais exigem a equipe completa. A carga de outubro em produção depende da recuperação da fotografia.

## Atualização das bases legislativas

Os coletores `app.jobs.import_legislation` e `app.jobs.import_senado_legislation` atualizam janelas recentes e podem ser executados pelo serviço `scheduler` de produção. Uma execução manual atualiza as janelas atuais. A reposição de proposições antigas exige identificar os registros ausentes por Casa e identificador, consultar os detalhes oficiais e medir quantos passaram a aparecer na API.

Depois de validar as cargas, conferir os agendamentos ativos e acompanhar as últimas execuções por fonte. Usar as contagens da API para identificar mudanças de cobertura e as datas de coleta para verificar a atualização.
