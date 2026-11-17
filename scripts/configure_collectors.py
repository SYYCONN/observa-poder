"""Ativa somente opções de coleta no arquivo externo de produção, sem exibir segredos."""

import argparse
import os
import re
import tempfile
from pathlib import Path


OPTIONS = {
    "OBSERVA_COLLECT_ON_STARTUP": "true",
    "OBSERVA_COLLECT_PROFILES": "true",
    "OBSERVA_COLLECT_REMUNERATION": "true",
    "OBSERVA_COLLECT_EXPENSES": "true",
    "OBSERVA_COLLECT_STAFF": "true",
    "OBSERVA_COLLECT_AMENDMENTS": "true",
    "OBSERVA_COLLECT_VOTES": "true",
}


def configure(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("Use um arquivo regular, sem link simbólico.")
    original = path.read_text()
    lines = []
    seen = set()
    for line in original.splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Z_]+)\s*=", line)
        key = match.group(1) if match else None
        if key in OPTIONS:
            if key not in seen:
                lines.append(f"{key}={OPTIONS[key]}")
                seen.add(key)
        else:
            lines.append(line)
    lines.extend(f"{key}={value}" for key, value in OPTIONS.items() if key not in seen)
    stat = path.stat()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            os.chmod(temporary, 0o600)
            if os.geteuid() == 0:
                os.chown(temporary, stat.st_uid, stat.st_gid)
            output.write("\n".join(lines) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    configure(args.path)
    print("Coletas configuradas; demais opções preservadas. Serviços ainda não foram alterados.")
