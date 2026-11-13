# Observa Poder em produção

O perfil de produção sobe um projeto isolado, com API e frontend publicados em loopback e PostgreSQL em rede interna. O proxy da VPS encaminha o novo domínio para essas portas. O scheduler requer ativação explícita e a publicação começa com as funções administrativas e analytics indisponíveis na borda.

## Preparação e troca

1. Preserve backup externo e restaurável do Sycon Suite, incluindo banco, arquivos e configuração. Registre como restabelecer o vhost e os serviços antigos. Confira a saúde do site atual e as portas livres, em IPv4 e IPv6.
2. Copie `.env.production.example` para um arquivo fora do checkout. Preencha hostname canônico, contato de privacidade atendido, referências às imagens auditadas, portas livres e endereço exato do peer de proxy visto pela API. Aceite exclusivamente o proxy local nesse endereço. Substitua o endereço reservado do exemplo. Confirme o peer com um teste controlado antes de publicar.
3. Em um diretório externo protegido, crie os arquivos `db_bootstrap`, `db_migrate`, `db_read` e `db_collect`, cada qual com uma credencial aleatória distinta de pelo menos 24 caracteres. Cada arquivo precisa ser legível pelo UID do serviço correspondente dentro do container. Restrinja o acesso ao diretório e confira a propriedade efetiva após a montagem. Com Compose, segredos originados de arquivos são montados do host. Não copie credenciais para o ambiente de build ou terminal compartilhado.
4. Revise as imagens e fixe os digests da arquitetura da VPS. Valide o Compose, suba os serviços em paralelo e confirme a migration e o healthcheck. O bootstrap de papéis roda apenas ao inicializar um volume novo. Use o fluxo de migração do projeto para bancos já existentes.
5. Aponte o registro A do domínio novo para o IPv4 público da VPS e mantenha o DNS do Sycon. Publique AAAA somente após validar o caminho IPv6. Gere o vhost com `scripts/render_observa_nginx.py`, com caminhos dos certificados e as mesmas portas do Compose. Revise a validação de domínio do certificado, incluindo o método ACME adotado. Rode `nginx -t` antes de qualquer reload autorizado.
6. Valide HTTPS, site, consulta, exportações, Trusted Hosts, bloqueios administrativos, IP real e ausência de portas públicas para banco e upstreams. Monitore os dois domínios e configure alertas de disponibilidade, certificado, latência, 429/5xx, disco, memória e backup.
7. Pare apenas os serviços do Sycon depois de aceitar o Observa Poder. Preserve dados e configuração. Em caso de regressão, retire apenas o vhost novo, restaure as referências da versão aprovada e reative o Sycon se necessário.

O Nginx aplica cotas e prazos na origem. Se houver CDN, configure a identidade do visitante por uma cadeia de proxies de confiança e restrinja a origem conforme a arquitetura efetiva. Limites locais não absorvem saturação do enlace. O firewall, emissão TLS e validação do site antigo dependem do host.

## Backup e restauração

`scripts/backup_observa.sh ARQUIVO_DE_AMBIENTE DESTINATARIO_AGE ARQUIVO.dump.age` grava um dump lógico criptografado. Guarde-o fora da VPS e retenha a identidade age em local separado. O dump não inclui papéis nem grants. Em um ensaio, provisione os papéis em um PostgreSQL isolado e vazio, restaure com o proprietário migrador, reaplique os grants por meio do serviço migrador, compare tabelas e valide a API. Registre o tempo, a data da cópia e o resultado. O backup do Sycon tem fluxo independente.

A coleta automática começa desativada na publicação. Antes de habilitar o perfil `collect`, dimensione memória, verifique o acesso às fontes e aprove a publicação de dados de despesas e equipes. O coletor autenticado e o provedor externo não recebem chaves por este perfil.
