from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyMetric(Base):
    __tablename__ = "analytics_daily_metrics"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    category: Mapped[str] = mapped_column(String(24), primary_key=True)
    route: Mapped[str] = mapped_column(String(200), primary_key=True)
    outcome: Mapped[str] = mapped_column(String(8), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
