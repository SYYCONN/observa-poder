"""Suite completa em PostgreSQL efêmero. Nunca usa o volume da aplicação."""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def main():
    name = "politica-tests-" + uuid4().hex[:12]
    password = secrets.token_hex(24)
    environment = {**os.environ, "POSTGRES_PASSWORD": password}
    created = False
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                name,
                "-e",
                "POSTGRES_PASSWORD",
                "-e",
                "POSTGRES_DB=politica_test",
                "-p",
                "127.0.0.1::5432",
                "postgres:17-alpine",
            ],
            env=environment,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        created = True
        details = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
        port = details["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        for _ in range(40):
            result = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "postgres", "-d", "politica_test"],
                capture_output=True,
            )
            if result.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("PostgreSQL de teste não iniciou.")
        env = {
            **os.environ,
            "DB_HOST": "127.0.0.1",
            "DB_PORT": port,
            "DB_NAME": "politica_test",
            "DB_USER": "postgres",
            "DB_PASSWORD": password,
            "TEST_DATABASE_URL": f"postgresql+psycopg://postgres:{password}@127.0.0.1:{port}/politica_test",
        }
        for args in [
            ["alembic", "upgrade", "head"],
            ["alembic", "check"],
            ["alembic", "downgrade", "base"],
            ["alembic", "upgrade", "head"],
            ["pytest", "-q"],
        ]:
            print("Verificando:", " ".join(args), flush=True)
            subprocess.run([sys.executable, "-m", *args], cwd=BACKEND, env=env, check=True)
    finally:
        if created:
            subprocess.run(
                ["docker", "rm", "--force", name], check=False, stdout=subprocess.DEVNULL
            )


if __name__ == "__main__":
    main()
