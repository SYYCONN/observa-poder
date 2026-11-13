"""Normalização conservadora dos campos compartilhados pelas fontes legislativas."""

from datetime import datetime

from app.core.dates import BUSINESS_TIMEZONE


def legislative_datetime(value: str | None) -> datetime | None:
    """Horários sem offset pertencem ao fuso de negócio; offsets explícitos são mantidos."""
    if not value or not value.strip():
        return None
    parsed = datetime.fromisoformat(value.strip())
    return parsed.replace(tzinfo=BUSINESS_TIMEZONE) if parsed.tzinfo is None else parsed


def camara_boolean(value: object) -> bool | None:
    """Não confundir a string '0' com aprovação nem valores desconhecidos com rejeição."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        return {"1": True, "0": False}.get(value.strip())
    return None


def vote_position(*values: str | None) -> str | None:
    """Preserva o texto publicado, sem criar posição para registros incompletos."""
    return next((value.strip() for value in values if value and value.strip()), None)
