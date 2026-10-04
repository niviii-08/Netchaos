from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # stored as naive UTC


class Network(Base):
    __tablename__ = "networks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    # Counters make node/link ids sequential per network and never reused after a delete.
    next_node_seq: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_link_seq: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    nodes = relationship("Node", cascade="all, delete-orphan", passive_deletes=True)
    links = relationship("Link", cascade="all, delete-orphan", passive_deletes=True)
