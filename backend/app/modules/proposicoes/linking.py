"""Vínculos conservadores entre autoria publicada e parlamentares conhecidos."""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.parlamentares.models import Parliamentarian


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def find_parliamentarian(
    session: Session,
    source: str,
    author_name: str | None,
    author_url: str | None = None,
) -> Parliamentarian | None:
    """Retorna apenas vínculos comprováveis por ID ou nome único na fonte."""
    if author_url:
        match = re.search(r"/(?:deputados|senador(?:es)?)/([0-9]+)(?:/|$)", author_url)
        if match:
            person = session.scalar(
                select(Parliamentarian).where(
                    Parliamentarian.source == source,
                    Parliamentarian.external_id == match.group(1),
                )
            )
            if person is not None:
                return person

    normalized = normalize_name(author_name)
    if not normalized or normalized.startswith("comissao "):
        return None
    candidates = session.scalars(
        select(Parliamentarian).where(Parliamentarian.source == source)
    ).all()
    matches = [person for person in candidates if normalize_name(person.name) == normalized]
    return matches[0] if len(matches) == 1 else None
