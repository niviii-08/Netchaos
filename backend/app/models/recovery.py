from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, ForeignKeyConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.models.network import utc_now


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["simulation_id", "network_id"], 
            ["traffic_simulations.id", "traffic_simulations.network_id"],
            ondelete="CASCADE"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    simulation_id: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_detection_id: Mapped[str | None] = mapped_column(String(32))

    original_route: Mapped[list | None] = mapped_column(JSON)
    recovered_route: Mapped[list | None] = mapped_column(JSON)
    
    original_latency: Mapped[float | None] = mapped_column(Float(53))
    recovered_latency: Mapped[float | None] = mapped_column(Float(53))
    
    original_hop_count: Mapped[int | None] = mapped_column(Integer)
    recovered_hop_count: Mapped[int | None] = mapped_column(Integer)
    
    original_bandwidth: Mapped[float | None] = mapped_column(Float(53))
    recovered_bandwidth: Mapped[float | None] = mapped_column(Float(53))

    route_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_status: Mapped[str] = mapped_column(String(32), nullable=False)

    recovery_start_time: Mapped[datetime | None] = mapped_column(DateTime)
    recovery_end_time: Mapped[datetime | None] = mapped_column(DateTime)
    recovery_duration: Mapped[float | None] = mapped_column(Float(53))

    failure_type: Mapped[str | None] = mapped_column(String(64))
    failure_description: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
