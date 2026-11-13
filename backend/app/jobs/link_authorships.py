"""Vincula autorias já coletadas aos parlamentares por identificador oficial."""

import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as _models  # noqa: F401 - registra todas as tabelas no metadata
from app.db.session import get_engine
from app.modules.proposicoes.linking import find_parliamentarian
from app.modules.proposicoes.models import Authorship


def link_authorships(engine):
    run_id = uuid4()
    linked = 0
    ambiguous = 0
    with Session(engine) as session, session.begin():
        rows = session.scalars(
            select(Authorship).where(
                Authorship.parliamentarian_id.is_(None),
                Authorship.source != "senado",
            )
        ).all()
        for authorship in rows:
            person = find_parliamentarian(
                session,
                authorship.source,
                authorship.author_name,
                authorship.author_url,
            )
            if person is None:
                ambiguous += 1
                continue
            authorship.parliamentarian_id = person.id
            linked += 1
    return {"run_id": str(run_id), "linked": linked, "unmatched_or_ambiguous": ambiguous}


if __name__ == "__main__":
    print(json.dumps(link_authorships(get_engine()), ensure_ascii=False))
