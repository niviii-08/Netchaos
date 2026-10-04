from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.enums import ElementStatus
from app.models.network import utc_now


class Link(Base):
    __tablename__ = "links"
    # Composite foreign keys guarantee a link can only join two nodes of its own network,
    # and deleting a node removes its links at the database level too.
    # Column order must match the nodes primary key (id, network_id): MySQL/InnoDB rejects it otherwise.
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_node_id", "network_id"], ["nodes.id", "nodes.network_id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["destination_node_id", "network_id"], ["nodes.id", "nodes.network_id"], ondelete="CASCADE"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("networks.id", ondelete="CASCADE"), primary_key=True
    )
    source_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    bandwidth: Mapped[float] = mapped_column(Float, nullable=False)  # Mbps
    latency: Mapped[float] = mapped_column(Float, nullable=False)  # milliseconds
    packet_loss: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # percent
    status: Mapped[str] = mapped_column(String(16), default=ElementStatus.ACTIVE.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
