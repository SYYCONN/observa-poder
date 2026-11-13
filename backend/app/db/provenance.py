import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


class Provenance:
    source: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str] = mapped_column(String(1000))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_records.id"))
