from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.enums import ChaosStatus
from app.models.network import utc_now as _utc_now


def utc_now() -> datetime:
    """Whole seconds: MySQL DATETIME drops fractions, and API responses should match what is stored."""
    return _utc_now().replace(microsecond=0)


class ChaosExperiment(Base):
    """One user action ("inject latency", "multi-failure ..."): a group of one or more chaos events.

    Like traffic simulations there is deliberately no foreign key to nodes/links: their ids are never
    reused, and deleting a node must not delete the history of experiments that touched it.
    """
    __tablename__ = "chaos_experiments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # chaos_001, numbered per network
    network_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("networks.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scenario_type: Mapped[str] = mapped_column(String(32), nullable=False)  # multi_failure for several events
    status: Mapped[str] = mapped_column(String(16), default=ChaosStatus.PENDING.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChaosEvent(Base):
    """One change to one node or link. Events are the layers that effective state is recomputed from.

    ``previous_state`` is the target's ORIGINAL (baseline) configuration from before any active chaos
    touched it; events layered on the same target share it. ``new_state`` is the effective state right
    after this event was applied (an audit snapshot; it is not used to restore anything).
    """
    __tablename__ = "chaos_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["experiment_id", "network_id"], ["chaos_experiments.id", "chaos_experiments.network_id"],
            ondelete="CASCADE",
        ),
        Index("ix_chaos_events_target", "network_id", "target_type", "target_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # evt_001, numbered per network; order = layer order
    network_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    previous_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    new_state: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default=ChaosStatus.PENDING.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
