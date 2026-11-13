from datetime import date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def local_today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()
