"""Detecta colisões entre migrations de frentes concorrentes sem acessar banco."""

import ast
from pathlib import Path

from alembic.script import ScriptDirectory


MIGRATIONS = Path(__file__).resolve().parents[1] / "alembic"


def test_migrations_have_unique_revisions_and_one_head():
    revisions = {}
    for path in sorted((MIGRATIONS / "versions").glob("*.py")):
        module = ast.parse(path.read_text())
        for node in module.body:
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "revision" for target in targets
            ):
                continue
            revision = ast.literal_eval(node.value)
            assert revision not in revisions, (
                f"Revisão duplicada {revision}: {revisions.get(revision)} e {path.name}"
            )
            revisions[revision] = path.name

    assert revisions, "Nenhuma migration encontrada"
    scripts = ScriptDirectory(str(MIGRATIONS))
    assert len(scripts.get_heads()) == 1, "Release exige uma única head de migration"
    assert len(scripts.get_bases()) == 1, "Release exige uma única base de migration"
    # Também detecta referências ausentes e ciclos na cadeia.
    assert len(list(scripts.walk_revisions())) == len(revisions)
