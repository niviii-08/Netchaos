from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.enums import ElementStatus
from app.models.network import utc_now


class NetworkBaseline(Base):
    __tablename__ = "network_baselines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(32), ForeignKey("networks.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    nodes = relationship("BaselineNode", cascade="all, delete-orphan", passive_deletes=True)
    links = relationship("BaselineLink", cascade="all, delete-orphan", passive_deletes=True)


class BaselineNode(Base):
    __tablename__ = "baseline_nodes"
    __table_args__ = (UniqueConstraint("baseline_id", "node_id", name="uq_baseline_nodes"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    baseline_id: Mapped[str] = mapped_column(String(32), ForeignKey("network_baselines.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class BaselineLink(Base):
    __tablename__ = "baseline_links"
    __table_args__ = (UniqueConstraint("baseline_id", "link_id", name="uq_baseline_links"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    baseline_id: Mapped[str] = mapped_column(String(32), ForeignKey("network_baselines.id", ondelete="CASCADE"), nullable=False)
    link_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    bandwidth: Mapped[float] = mapped_column(Float, nullable=False)
    latency: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss: Mapped[float] = mapped_column(Float, nullable=False)


class FailureDetection(Base):
    __tablename__ = "failure_detections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(32), ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    baseline_id: Mapped[str] = mapped_column(String(32), ForeignKey("network_baselines.id", ondelete="SET NULL"), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(16), nullable=False)

    failed_nodes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_links: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    degraded_links: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    connected_components: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    affected_simulations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unreachable_pairs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    failures = relationship("FailureRecord", cascade="all, delete-orphan", passive_deletes=True)


class FailureRecord(Base):
    __tablename__ = "failure_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(32), ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    detection_id: Mapped[str] = mapped_column(String(32), ForeignKey("failure_detections.id", ondelete="CASCADE"), nullable=False)
    
    failure_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # node, link, component, simulation, etc.
    target_id: Mapped[str] = mapped_column(String(32), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
