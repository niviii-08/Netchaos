from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.enums import ElementStatus
from app.models.network import utc_now


class Node(Base):
    __tablename__ = "nodes"
    # Ids are unique within a network (node_001 exists in every network), hence the composite key.
    __table_args__ = (UniqueConstraint("network_id", "name", name="uq_nodes_network_name"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    network_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("networks.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=ElementStatus.ACTIVE.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
