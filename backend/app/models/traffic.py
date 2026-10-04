from datetime import datetime

from sqlalchemy import (
    JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.enums import SimulationStatus
from app.models.network import utc_now as _utc_now


def utc_now() -> datetime:
    """Whole seconds: MySQL DATETIME drops fractions, and API responses should match what is stored."""
    return _utc_now().replace(microsecond=0)


class TrafficSimulation(Base):
    """One traffic simulation: its parameters, the route it used and its summary metrics.

    Deliberately has no foreign key to nodes: node ids are never reused, and deleting a node
    must not delete the history of simulations that used it.
    """
    __tablename__ = "traffic_simulations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # sim_001, numbered per network
    network_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("networks.id", ondelete="CASCADE"), primary_key=True
    )
    source_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    packet_count: Mapped[int] = mapped_column(Integer, nullable=False)
    packet_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    random_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    store_packets: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=SimulationStatus.PENDING.value, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))

    # Filled in by a run. NULL until then (and for a failed run, NULL for the metrics).
    route_available: Mapped[bool | None] = mapped_column(Boolean)
    route: Mapped[list | None] = mapped_column(JSON)  # node ids, source to destination
    delivered_packets: Mapped[int | None] = mapped_column(Integer)
    dropped_packets: Mapped[int | None] = mapped_column(Integer)
    packet_loss_percentage: Mapped[float | None] = mapped_column(Float(53))
    path_latency_ms: Mapped[float | None] = mapped_column(Float(53))
    hop_count: Mapped[int | None] = mapped_column(Integer)
    path_bandwidth_mbps: Mapped[float | None] = mapped_column(Float(53))
    throughput_mbps: Mapped[float | None] = mapped_column(Float(53))
    simulated_duration_ms: Mapped[float | None] = mapped_column(Float(53))  # model time
    execution_duration_ms: Mapped[float | None] = mapped_column(Float(53))  # real time the run took

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Packet(Base):
    """Optional packet-level record; only written when a simulation is created with store_packets."""
    __tablename__ = "packets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["simulation_id", "network_id"], ["traffic_simulations.id", "traffic_simulations.network_id"],
            ondelete="CASCADE",
        ),
    )

    simulation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sequence_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    packet_id: Mapped[str] = mapped_column(String(16), nullable=False)  # pkt_001
    source_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    packet_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    route: Mapped[list] = mapped_column(JSON, nullable=False)
    dropped_at_link_id: Mapped[str | None] = mapped_column(String(32))
    completed_at_ms: Mapped[float] = mapped_column(Float(53), nullable=False)  # simulated time of delivery/drop
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
