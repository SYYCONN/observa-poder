# Fontes externas

`camara/` contém o cliente e o contrato validado da lista atual de deputados. `senado/` contém o cliente XML da lista atual de senadores. Ambos solicitam apenas endpoints HTTPS oficiais, com limites de tamanho, timeout e retentativas limitadas.

Não seguir URLs arbitrárias retornadas pela fonte. Não persistir CPF, email ou campos extras: o normalizador admite apenas os campos de atuação pública necessários. Os payloads persistidos são recortes permitidos da fonte, não cópias integrais das respostas.

A coleta de projetos e votações continua concentrada na Câmara nesta etapa. O scheduler executa deputados, senadores e legislação automaticamente; a integração do Senado usa `source=senado` na API pública de parlamentares.
