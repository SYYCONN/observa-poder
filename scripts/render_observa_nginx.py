"""Print a dedicated Observa Poder vhost for review, without touching Nginx."""

import argparse
from pathlib import Path
import re


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--certificate", required=True)
    parser.add_argument("--certificate-key", required=True)
    parser.add_argument("--api-port", type=int, default=18080)
    parser.add_argument("--web-port", type=int, default=13000)
    args = parser.parse_args()
    host = args.host
    labels = host.split(".")
    if len(labels) < 2 or len(host) > 253 or not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
    ) or labels[-1].isdigit():
        parser.error("Informe o hostname DNS canônico em minúsculas")
    for path in (args.certificate, args.certificate_key):
        if not re.fullmatch(r"/[A-Za-z0-9_./-]+", path):
            parser.error("Caminho absoluto de certificado inválido")
    ports = (args.api_port, args.web_port)
    if len(set(ports)) != 2 or not all(1024 <= port <= 65535 for port in ports):
        parser.error("Escolha duas portas locais distintas entre 1024 e 65535")
    template = Path(__file__).resolve().parents[1] / "infra/nginx/observa.conf.template"
    values = {
        "@HOST@": host, "@CERT@": args.certificate, "@KEY@": args.certificate_key,
        "@API_PORT@": str(args.api_port), "@WEB_PORT@": str(args.web_port),
    }
    result = template.read_text()
    for placeholder, value in values.items():
        result = result.replace(placeholder, value)
    print(result, end="")


if __name__ == "__main__":
    main()
