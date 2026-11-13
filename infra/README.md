# Infraestrutura

`docker/` contém Dockerfiles. `compose.yaml`, na raiz, descreve apenas o ambiente local. PostgreSQL não publica portas e usa volume persistente. A configuração de produção, Nginx/TLS, limites de recursos, separação de usuários do banco e backup externo ainda serão implementados antes de qualquer deploy. Não executar este Compose como substituição direta do Sycon.

O comando Uvicorn no Dockerfile recusa headers de proxy por padrão, limita concorrência e desativa access log com URL bruta. Antes de colocar a API atrás de proxy, configurar explicitamente os IPs confiáveis e limites na borda conforme o checklist de `docs/04-seguranca-e-operacao.md`. Sem essa configuração, o rate limit agrupa todos os visitantes pelo IP do proxy. Os limites da aplicação são por processo e não constituem proteção contra DDoS volumétrico.
