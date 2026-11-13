# Segurança e operação

Controles de aplicação e Docker validados localmente em 11/11/2026. Os controles de borda e de produção seguem pendentes.

## Controles implementados localmente

- A API usa hosts explícitos em `ALLOWED_HOSTS` e CORS restrito a `FRONTEND_URL`. O preflight aceita GET e, quando analytics está habilitado, POST. A única escrita HTTP aceita pelo middleware é a ingestão de analytics. As leituras administrativas mantêm autenticação por token.
- Limite por endereço de transporte, por processo: reposição de 60 tokens/minuto e capacidade de 20. CSV/PDF compartilham outro balde de 6/minuto e capacidade de 2. Retorno 429 com `Retry-After`. Testar esses números com navegação real e usuários em redes compartilhadas.
- Cada mapa guarda no máximo 10.000 clientes. Baldes ociosos já reabastecidos expiram; com o mapa cheio, novos clientes recebem 429, sem expulsar dívidas existentes. Reinícios e múltiplos workers têm contadores independentes. Não há armazenamento persistente de IP nessa proteção.
- Limite de URI de 8 KiB antes das rotas e offset máximo de 100.000 nas listas. Paginação existente continua limitada a 100 registros (50 em despesas). Analytics aceita corpo de no máximo 4 KiB, inclusive envio fragmentado, e 5 segundos para recebê-lo; as demais operações de escrita são rejeitadas.
- Consultas das sessões HTTP usam `statement_timeout` transacional de 15 segundos no PostgreSQL; aquisição de conexão espera até 5 segundos. O prazo é por comando SQL, não por resposta inteira. Coletores que abrem suas próprias sessões não herdam esse limite.
- Docker da API: usuário sem root já existente; Uvicorn agora limita concorrência a 100, keep-alive a 5 segundos, não aceita cabeçalhos de proxy, não anuncia servidor e desativa access log com URL bruta.
- API: `nosniff`, bloqueio de enquadramento, políticas de referrer/permissões, CSP sem recursos para `/api/` e `no-store` em erros. Produção inclui HSTS e mantém documentação/OpenAPI desabilitados.
- Frontend: CSP restringe conexões à própria origem e à origem de `NEXT_PUBLIC_API_URL`; bloqueia objetos, enquadramento e formulários externos. Imagens HTTPS externas continuam permitidas para fotos oficiais. Scripts inline necessários à hidratação Next e estilos inline continuam permitidos; remover essa exceção exige uma implementação com nonce e revisão de renderização/cache. `unsafe-eval` é permitido apenas no desenvolvimento.
- Produção exige frontend HTTPS, hosts explícitos e senha de banco com ao menos 24 caracteres. Gerar senha aleatória; tamanho não comprova entropia. Erros textuais de configuração ocultam valores de entrada.
- Logs da API: ID gerado no servidor, modelo da rota, status e duração. Não registrar query, corpo, credenciais, IP ou valor de exceções. Erros inesperados retornam mensagem genérica. O ID é exposto no CORS; configuração de logs de proxy e coletores precisa de revisão separada.
- Dependabot semanal para npm, pip, imagens Docker e GitHub Actions. CI executa `npm audit --audit-level=high` e `pip-audit` no lock de desenvolvimento (que inclui runtime). Atualizações Python devem regenerar e revisar ambos os locks; não aceitar atualização isolada de `pyproject.toml`. Auditoria de imagens permanece requisito de release.
- O Compose local aplica `no-new-privileges` e remove capabilities de API, frontend e scheduler. Os quatro serviços têm rotação pelo driver local, com até três arquivos de 10 MB por container como parâmetros de rotação. A API deixa de receber as chaves e opções usadas exclusivamente pelas coletas. Arquivos de backup e dumps compactados também ficam fora do Git e do contexto de build.
- Quando uma resposta já começou e ocorre uma falha, o middleware interrompe o envio e fornece ao servidor uma exceção genérica. O log mantém o ID de requisição e o tipo do erro.

## Matriz de recomendações e validação

O custo operacional considera esforço de configuração e manutenção. Custos de serviços externos dependem do plano e do volume contratados.

| Recomendação e camada | Ameaça mitigada | Impacto | Custo operacional | Risco residual | Validação |
| --- | --- | --- | --- | --- | --- |
| Aplicação: manter CORS na origem configurada e anunciar POST somente com analytics ativo. Preservar a autorização dos GET administrativos. | Acesso de navegador por origem indevida e exposição de métodos sem contrato. | O painel na origem do portal pode enviar o Bearer. Preflights para métodos fora da lista falham. | Baixo. Revisar quando origem ou métodos mudarem. | Clientes fora do navegador ignoram CORS. A origem configurada continua sendo uma relação de confiança. | Testar origem permitida e negada, GET com Authorization, POST com analytics ligado/desligado e rejeição de PUT. |
| Aplicação e navegador: manter CSP, proteção de enquadramento, nosniff, referrer e HSTS após validar HTTPS. Avaliar nonce com QA antes de alterar a renderização. | Clickjacking, interpretação indevida de conteúdo e execução de scripts injetados. | Restringe recursos do navegador. CSP com nonce pode afetar cache e renderização. | Baixo para os headers atuais. Médio para migrar CSP. | Scripts inline ainda são permitidos. | Conferir headers em HTTPS e navegar em páginas, fotos, filtros, painel e downloads. |
| Aplicação: manter cotas por IP e por exportação, limites de URI/payload/página e timeout SQL. | Esgotamento de CPU, memória, threads e banco por consultas ou exportações repetidas. | Responde com 429, 413 ou 414 conforme o limite. Consultas demoradas são canceladas. | Baixo no código. Médio para medir carga e ajustar cotas. | IPs compartilhados podem receber 429. Cotas são por processo e preflights passam pelo CORS antes do limitador. | Testar com PostgreSQL temporário, corpo fragmentado e carga controlada em homologação. Medir 429 e latência para tráfego legítimo. |
| Borda: limitar conexões, preflights, exportações, ingestão e tamanho de requisição no proxy. Proteger a origem com firewall e restringir a confiança em headers aos proxies autorizados. | Abuso distribuído, conexões lentas e tráfego direto que contorna a borda. | Reduz carga na origem e preserva a identificação do cliente para a cota. | Médio a alto. Operar regras, métricas, exceções e eventuais custos do provedor. | Tráfego distribuído ou volumétrico ainda pode degradar o serviço. Regras agressivas podem bloquear redes legítimas. | Em homologação, verificar que só a borda alcança a origem e que preflights, conexões e exportações respeitam os limites. Medir saturação e falsos positivos. |
| Rede e banco: publicar apenas a borda, restringir administração e separar papéis de leitura, coleta e migração. | Exposição direta de serviços e abuso de permissões após comprometimento. | Reduz a superfície pública e as permissões de cada credencial. | Médio. Provisionar papéis, regras de rede e acesso de recuperação. | Processos autorizados ainda podem comprometer os dados sob sua responsabilidade. | Conferir portas publicadas e testar, com cada papel, permissões permitidas e negadas em homologação. |
| Docker: manter usuário sem root, capabilities removidas, `no-new-privileges` e rotação de logs. Definir limites de recursos com carga representativa. | Escalada de privilégios e indisponibilidade por pressão de disco ou memória. | Restringe os processos e o volume de log retido. A rotação reduz o histórico local. | Baixo para os controles atuais. Médio para dimensionar limites. | Containers compartilham o kernel. Rotação não limita toda a escrita em disco. | Inspecionar UID, capabilities e `NoNewPrivs` nos containers. Conferir a configuração do driver e simular rotação em ambiente descartável. |
| Segredos: entregar a cada serviço apenas suas credenciais, separar tokens administrativos e prever rotação e revogação. | Uso de credenciais extraídas de imagem, Git, logs ou processo comprometido. | Um incidente na API deixa de expor as chaves do scheduler por herança do Compose. | Baixo localmente. Médio para gestão e rotação em produção. | O operador do Docker e o processo que usa a chave podem acessá-la. | Revisar nomes de variáveis por serviço sem imprimir valores. Validar com credenciais fictícias que a revogação invalida o token antigo. |
| Observabilidade: manter logs por rota e ID sem entrada bruta. Revisar proxy e scheduler antes de publicar. | Vazamento de tokens, parâmetros sensíveis ou dados de fontes nas exceções. | Facilita correlação de erros com menos dados para diagnóstico. | Baixo na API. Médio para configurar coleta e alertas. | O scheduler ainda pode registrar stack traces e os componentes externos têm logging próprio. | Gerar falhas com marcadores fictícios e confirmar que o identificador aparece, mas os marcadores não, inclusive após início de resposta. |
| CI e imagens: revisar auditorias de locks, imagens e ações. | Uso de componentes com vulnerabilidades conhecidas. | Ajuda a detectar versões afetadas antes da liberação. | Baixo no CI. Médio para triagem, atualização e testes de imagem. | Cobertura depende das bases consultadas e não inclui falhas desconhecidas. | Rodar `npm audit`, `pip-audit` e auditoria das imagens efetivamente implantadas. Registrar versão e resultado por release. |
| Operação: testar restauração de backup criptografado e definir resposta a incidentes. | Perda de dados, alteração indevida e recuperação lenta após falha. | Reduz o tempo para conter e recuperar o portal. | Médio. Armazenamento externo, exercícios e disponibilidade de responsáveis. | Pode haver perda desde a última cópia e recuperação mais lenta que a meta. | Restaurar em instância isolada, verificar amostras e cronometrar. Simular alerta, contenção e retorno. |

Arquivos centrais: `backend/app/core/security.py`, `config.py`, `main.py`, `db/session.py`, `frontend/next.config.ts` e `backend/tests/test_security.py`. Exemplos de variáveis ficam em `backend/.env.example`; Compose atual é exclusivamente local.

### Arquivos desta implementação

- API/configuração: `backend/app/core/security.py`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/db/session.py`, `backend/app/api/routes/parliamentarians.py`, `backend/app/api/routes/legislation.py`, `backend/.env.example`.
- Dependências: `backend/pyproject.toml`, `backend/requirements.lock`, `backend/requirements-dev.lock`. Pillow atualizado de 11.3.0 para 13.0.0 após alertas da auditoria; `pip-audit` restrito às dependências de desenvolvimento.
- Navegador/container: `frontend/next.config.ts`, `infra/docker/backend.Dockerfile`.
- Verificações: `backend/tests/test_security.py`, `backend/tests/integration/test_api_security.py`, `.github/workflows/ci.yml`, `.github/dependabot.yml`.
- Documentação: este arquivo e `infra/README.md`.

### Validação local em 03/11/2026

- `cd backend && .venv/bin/python ../scripts/test_backend.py`: migrations upgrade/check/downgrade/upgrade e suíte completa em PostgreSQL temporário, removido ao final. Inclui consulta cancelada por prazo e verificação de restauração da configuração na conexão reutilizada.
- `cd frontend && npm run typecheck && npm run build`: compilação e tipos; cabeçalhos também conferidos por HTTP no servidor de produção local.
- `cd frontend && npm audit --audit-level=high`: nenhum alerta conhecido no momento da execução.
- `cd backend && .venv/bin/python -m pip_audit --disable-pip --no-deps -r requirements-dev.lock`: nenhum alerta conhecido após a atualização. Auditorias são pontuais, sem garantia sobre descobertas futuras.
- `docker compose --env-file .env.example config --quiet`: configuração local válida.

Repositório ainda sem commit inicial; os arquivos existentes já estavam sem rastreamento, então `git diff` não oferece uma base histórica para separar trabalho simultâneo. Alterações das outras frentes foram preservadas. Nenhum deploy, push ou acesso à VPS foi executado.

### Validação local em 11/11/2026

- A suíte completa passou com 204 testes e migrations verificadas em PostgreSQL temporário. Os testes incluem preflights aceitos e recusados, corpo fragmentado, cotas e supressão de dados sensíveis quando uma resposta é interrompida.
- Typecheck e build passaram após mover cópias idênticas de arquivos gerados em `frontend/.next/types` para um diretório temporário.
- `npm audit --audit-level=high` e `pip-audit` no lock Python de desenvolvimento não reportaram vulnerabilidades conhecidas na execução.
- `docker compose --env-file .env.example config --quiet` passou. A configuração efetiva mantém API e frontend em loopback, banco e scheduler sem portas publicadas e rotação nos quatro serviços. Containers descartáveis confirmaram UID sem root, `NoNewPrivs` e capabilities efetivas zeradas em API, frontend e scheduler. A checagem de segredos verificou apenas os nomes das variáveis.
- Neste ciclo, os arquivos alterados foram `backend/app/main.py`, `backend/app/core/security.py`, `backend/tests/test_security.py`, `compose.yaml`, `.dockerignore`, `.gitignore` e este documento.

## Checklist de liberação (não executado na VPS)

- [ ] Definir domínio, origem HTTPS exata e `ALLOWED_HOSTS` incluindo apenas domínio da API e hosts de healthcheck necessários. Configurar `APP_ENV=production`; não usar os exemplos locais como segredos.
- [ ] Configurar TLS antes do HSTS, testar redirecionamento e certificados. HSTS afeta o host inteiro; não inclui subdomínios automaticamente.
- [ ] Instalar CDN/WAF e limitar conexões, requisições, tamanho de cabeçalhos/corpos e tempo de leitura no proxy; ajustar limites com carga representativa. O middleware não protege banda, handshake, conexões lentas ou ataque distribuído.
- [ ] Bloquear acesso público direto à API/origem e ao banco. Se mantiver `--no-proxy-headers`, todos os usuários atrás de proxy compartilharão o limite do endereço dele. Antes de liberar, definir proxies confiáveis e sobrescrever o comando Uvicorn com `--proxy-headers --forwarded-allow-ips=<IPs explícitos do proxy>`, preservando os demais limites. Nunca confiar em `*`; o proxy deve remover/sobrescrever cabeçalhos enviados pelo cliente.
- [ ] Implementar limites globais no proxy/borda antes de aumentar workers/réplicas; separar limite mais estrito para exportações e ingestão. Preflight CORS é respondido antes do middleware; o proxy também deve limitá-lo. O frontend/arquivos estáticos não passam pelo limitador da API.
- [ ] Conferir CSP, CORS, downloads e headers em HTTPS real no desktop/mobile; CSP depende da URL pública da API fornecida no build, e o navegador precisa alcançá-la.
- [ ] Auditar `npm audit`, locks Python com ferramenta de vulnerabilidades e imagens de containers; registrar data/resultados e resolver riscos exploráveis. Habilitar alertas de dependências e secret scanning no provedor do repositório quando disponíveis.
- [ ] Revisar logs de coletores/proxy (sem tokens, cabeçalhos, URLs com credenciais ou payloads); definir rotação, retenção e alertas. Não registrar o resultado completo de `docker compose config` com ambiente real.
- [ ] Separar usuários de leitura/coleta/migração, limitar recursos dos containers, definir contato de incidente e testar backup externo/restauração antes da troca do Sycon.

Estes controles não implementam autenticação administrativa, WAF, isolamento da origem, TLS, backups ou configuração da VPS. As regras abaixo continuam sendo requisitos operacionais propostos, cuja aplicação deve ser comprovada no lançamento.

## Objetivo e ameaças

Proteger integridade dos dados, disponibilidade do portal e acesso às contas administrativas. Não existe garantia de ausência de invasão. O plano combina prevenção, detecção, contenção e recuperação.

Ameaças prioritárias: roubo de credenciais, alteração indevida de dados políticos, exploração de dependências, abuso de consultas e negação de serviço, exposição de backups/segredos e conteúdo malicioso recebido de fontes externas.

O cenário escolhido para planejamento é substituir o Sycon Suite na VPS Hostinger. Antes da troca efetiva, preservar banco, anexos, configurações e versão da aplicação antiga em backup externo protegido, testar restauração e definir janela de parada e retorno. Não excluir volumes, reinstalar o sistema ou remover serviços durante esta etapa de documentação. O novo projeto terá banco e credenciais próprios. A eventual remoção de dados antigos seguirá uma decisão explícita de retenção.

## Regras mínimas para produção

| Área | Regra proposta | Evidência antes do lançamento |
| --- | --- | --- |
| Contas | MFA no domínio, DNS, nuvem e GitHub; usuários individuais e menor privilégio | Revisar acessos e guardar recuperação em local separado |
| Rede | HTTPS da borda à origem; validação do certificado; apenas portas necessárias | Testar TLS e exposição externa |
| Origem | Restringir acesso web à borda autorizada; acesso administrativo por VPN ou lista restrita | Testar bloqueio de acesso direto ao IP |
| SSH | Chaves, sem senha e sem login direto como root; usuário operacional limitado | Conferir configuração e acesso de recuperação |
| Banco | PostgreSQL sem porta pública; credenciais separadas para leitura, coleta e migração | Testar alcance externo e permissões efetivas |
| Segredos | Fora do Git, imagem e frontend; logs sem tokens; rotação após suspeita | Varredura de segredos e revisão de variáveis |
| Aplicação | Validação de entrada, consultas parametrizadas, limites de paginação e tempo | Testes de entradas malformadas, abuso e permissões |
| Conteúdo externo | Tratar inclusive dados oficiais como não confiáveis; escapar saída e sanitizar HTML quando necessário | Testar amostras com markup e links inseguros |
| Navegador | CSP restritiva, proteção contra enquadramento, nosniff, política de referrer e HSTS após validar TLS | Conferir cabeçalhos e funcionamento |
| Administração | Sem painel público no MVP; tarefas operacionais em acesso restrito e auditado | Conferir rotas expostas e registros de operação |
| Dependências | Lockfiles, análise de vulnerabilidades e revisão de imagens e ações de CI | Resultado registrado por release |
| Backups | Cópias consistentes, criptografadas, fora da VPS, com acesso restrito | Restauração em ambiente isolado |

CDN/WAF ajudam a filtrar ataques, mas não substituem correções no código. O [plano Free da Cloudflare](https://www.cloudflare.com/plans/) oferece uma base de proteção com limites; mapear regras efetivamente disponíveis. Implementar limites também na aplicação/proxy.

## Ataques de aplicação

- SQL injection: consultas parametrizadas e escolhas de ordenação restritas; não concatenar valores em SQL. Referência: [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html).
- XSS: escape contextual e sanitização, evitando HTML arbitrário; CSP como defesa adicional. Referência: [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html).
- SSRF nos coletores: permitir apenas fontes e esquemas aprovados, bloquear redes privadas/metadata e revalidar redirecionamentos; limitar tempo e tamanho de downloads. Referência: [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
- CORS não é autenticação. API pública de leitura continua sujeita a limites; operações de escrita não ficam abertas ao público.
- Se houver autenticação web futura: autorização no servidor por operação, cookies Secure/HttpOnly/SameSite quando usados e proteção CSRF nas operações autenticadas por cookie. Definir isso antes de abrir painel ou cadastro.
- Não aceitar uploads, URLs arbitrárias para importação ou execução de comandos enviados pelo usuário no MVP.

## Limites de consumo

Ponto de partida para homologação: até 60 consultas/minuto/IP na API, rajada de 20, máximo de 100 registros/página e prazo de execução por consulta. Ajustar com testes, considerando redes compartilhadas e acessibilidade. Não aplicar esse limite a cada arquivo estático.

Confiar em cabeçalhos de IP apenas de proxies conhecidos. Aplicar cache e restrições mais severas nas buscas caras; nenhuma exportação ilimitada. Os números são parâmetros iniciais e não garantia contra DDoS distribuído.

## Backups e recuperação

- Dump consistente do PostgreSQL diariamente, criptografado e enviado para armazenamento fora da VPS; retenção proposta de 7 diários, 4 semanais e 3 mensais, condicionada ao volume.
- Backup diário da máquina complementa o dump. Não assumir que uma imagem de disco garante consistência de aplicações.
- Cópia mensal adicional sob controle independente da conta de produção. Manter chaves de recuperação fora do servidor.
- Testar restauração mensal e antes de mudança relevante de infraestrutura. Validar tabelas, contagens e amostra de registros.
- Meta inicial de perda máxima de dados próprios (RPO): 24 horas. Meta de restauração (RTO): 8 horas após início da resposta. São objetivos a testar, não SLA; cobertura humana e fornecedor afetam o tempo real.
- Perda completa da conta/provedor pode exigir usar a cópia mensal, com recuperação pior. Reduzir esse risco exige cópia independente mais frequente e orçamento correspondente.

Reimportar fontes pode recuperar dados públicos, mas não garante reconstrução de registros removidos, correções editoriais ou histórico de coleta. Backups permanecem necessários.

## Monitoramento e rotina

Responsável operacional e canal de alerta precisam ser definidos antes da publicação. Não pressupor plantão 24 horas.

- Checagem externa de disponibilidade proposta a cada 5 minutos; escolher serviço e limites na contratação.
- Alertar por três falhas consecutivas, aumento de erros, disco acima de 70%, backup ausente há mais de 26 horas e falhas repetidas de coleta.
- Alerta de atualização: mais de 60 minutos sem sucesso para rotina de 15 minutos; mais de 36 horas para rotina diária. Indicar indisponibilidade da fonte separadamente.
- Logs estruturados com ID de requisição e tarefa, sem payloads pessoais desnecessários ou credenciais. Proposta: 30 dias de logs operacionais e 90 dias de auditoria; validar retenção e obrigações aplicáveis antes de produção.
- Revisão semanal de erros, fontes e avisos de vulnerabilidade; revisão mensal de custos, acessos, restauração e atualização do sistema.
- Vulnerabilidade crítica explorável: triagem assim que identificada, alvo de contenção em 24 horas; riscos altos, alvo de correção em 7 dias. Registrar exceções e compensações. Sem equipe de plantão, esses prazos não são garantia de atendimento.

## Resposta a incidente

| Cenário | Detecção | Contenção | Recuperação |
| --- | --- | --- | --- |
| Abuso ou indisponibilidade | Correlacionar latência, 429, 503, conexões e saturação entre borda e origem. | Ajustar cotas na borda e restringir temporariamente as rotas mais caras. | Reabrir gradualmente e comparar erros e latência com a linha de base. |
| Suspeita de credencial comprometida | Correlacionar alertas do provedor com uso inesperado da conta e IDs de requisição. | Revogar a credencial e restringir o acesso à função afetada. | Distribuir nova credencial somente aos serviços que a usam e confirmar a revogação. |
| Dados alterados ou perdidos | Comparar contagens, amostras e proveniência com cópias e fontes oficiais. | Pausar escritas da origem afetada e preservar evidências. | Restaurar em ambiente isolado, conferir integridade e só então retomar o serviço. |

1. Identificar, registrar horário e preservar evidências com acesso restrito.
2. Conter: bloquear rota ou origem afetada, pausar coletor ou colocar serviço em manutenção.
3. Revogar sessões e credenciais comprometidas; verificar contas de domínio, nuvem e repositório.
4. Corrigir a causa e restaurar de origem conhecida; comparar integridade dos dados antes de reabrir.
5. Avaliar impacto nos dados e necessidade de comunicação aos usuários e autoridades conforme obrigações aplicáveis.
6. Documentar causa, impacto e ações preventivas. Se conteúdo público tiver sido alterado indevidamente, publicar correção clara.

Definir contato de segurança, suplente e acesso de recuperação antes de lançar. Auditoria externa especializada é uma evolução recomendada antes de contas públicas, pagamentos ou maior exposição; não está incluída no orçamento básico.
