# Coletas automáticas em produção

O agendador é um processo separado da API, executa uma coleta por vez e mantém os
locks existentes no PostgreSQL. A ativação exige o perfil `collect` do Compose.
Nenhuma porta é publicada pelo agendador. Ele utiliza o usuário de coleta, sem root,
com filesystem somente de leitura, limite de 1 GB de RAM e 0,75 CPU.

## Frequência configurada

| Coleta | Intervalo após terminar a execução anterior |
| --- | --- |
| Deputados e senadores atuais | 24 horas |
| Legislação recente da Câmara | 1 hora |
| Legislação recente do Senado | 6 horas |
| Despesas e emendas | 24 horas |
| Perfis individuais, votos anuais, equipe e remuneração | 7 dias |

A remuneração parlamentar consulta o último mês encerrado e exige que o mês e ano
declarados no HTML correspondam ao solicitado. Competência sem valores não é sucesso
financeiro nem remuneração zero. Equipe é uma fotografia do mês corrente; sua folha
só é incorporada quando a competência publicada corresponde à fotografia.
Assim, ainda pode haver remuneração indisponível no mês corrente. A coleta não cria
fotografias históricas de equipe que não foram registradas anteriormente.

O ano das despesas, emendas e votos usa `0` como seleção automática no agendador e
é calculado em cada execução, inclusive na virada do ano. Anos anteriores permanecem
preservados e sua reconciliação excepcional é manual. O TSE de 2022 já carregado não
é baixado repetidamente; nova eleição exige configuração e validação explícitas.
Legislação recente mantém a janela já existente, sem prometer histórico integral.

As páginas HTML de equipe e remuneração têm intervalo mínimo de um segundo entre
requisições iniciadas pelo cliente e até duas novas tentativas de conexão pelo
transporte HTTP. Não há desvio de bloqueio da fonte, CAPTCHA ou alteração de DNS.
Respostas HTTP de erro encerram a coleta ou preservam a lacuna individual conforme
o importador; a próxima tentativa é no intervalo do agendador. Falha é registrada
sem payload ou mensagem potencialmente sensível e não impede o próximo job.

## Ativação na VPS

Após atualizar o código, construir a imagem da API e validar a configuração:

```bash
python3 scripts/configure_collectors.py /etc/observa-poder/production.env
docker compose --env-file /etc/observa-poder/production.env -f compose.production.yaml config --quiet
docker compose --env-file /etc/observa-poder/production.env -f compose.production.yaml --profile collect up -d --no-deps scheduler
docker compose --env-file /etc/observa-poder/production.env -f compose.production.yaml logs --tail=80 scheduler
```

O script preserva opções alheias às sete flags de coleta, grava atomicamente e não
imprime os demais valores do arquivo. Com execução na inicialização habilitada,
as coletas começam em sequência e também são reexecutadas depois de um reinício.
O primeiro ciclo de equipe pode levar horas: não é necessário manter o SSH aberto.
O site continua sendo servido pelos processos independentes.

## Validação e limites operacionais

| Ação | Ameaça mitigada | Impacto | Custo operacional | Risco residual | Validação |
| --- | --- | --- | --- | --- | --- |
| Ativação explícita e gravação restrita das flags | Coleta desativada ou modificação acidental de segredos | Atualização periódica | Uma operação de ativação | Falha da fonte pode manter dado antigo | Plano nos logs, estado do container e `import_runs` |
| Execução sequencial e limites de recursos | Saturação da VPS e abuso da fonte | Coletas pesadas atrasam as seguintes | Primeiros ciclos demorados | Limite de CPU/memória não elimina carga de disco e banco | Testes do agendador, `docker stats --no-stream` e observação do site |
| Ritmo HTTP, timeout e tentativas limitadas | Rajadas e conexões transitórias | Menos requisições por segundo | Coleta de equipe pode levar horas | Indisponibilidade e bloqueio externo permanecem possíveis | Teste de espaçamento, logs e execução real |
| Validação da competência e virada de ano | Divulgação de valores no período incorreto | Conserva ausência explícita quando a fonte atrasa | Nova tentativa semanal | Publicação atrasada e cobertura parcial da fonte | Testes de período divergente, dezembro/janeiro e consulta pública |
| `restart: unless-stopped` e logs com rotação | Parada após reboot e crescimento de logs | Retomada automática do processo | Consulta operacional dos logs | Processo vivo não prova que todos os jobs tiveram sucesso | Verificar execuções concluídas e falhas por job no banco |

Logs no Docker são evidência operacional, não alertas enviados a um responsável.
Alertas externos, backups e proteção de borda pertencem a verificações próprias;
esta ativação não promete proteção absoluta contra DDoS.

Para interromper somente a automação, sem parar o portal ou apagar dados:

```bash
docker compose --env-file /etc/observa-poder/production.env -f compose.production.yaml stop scheduler
```
