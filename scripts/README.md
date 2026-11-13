# Scripts operacionais

`test_backend.py`: cria um PostgreSQL efêmero com porta local aleatória e credencial temporária, valida upgrade/check/downgrade das migrations e roda a suíte completa. Remove somente seu próprio container ao terminar. Não utiliza o volume da aplicação.

Executar da raiz:

```bash
backend/.venv/bin/python scripts/test_backend.py
```

Requer Docker ativo e dependências de desenvolvimento instaladas. O CI usa o mesmo script. Não guardar scripts temporários, dumps ou credenciais nesta pasta. Backup, restauração e deploy ainda não foram automatizados.
