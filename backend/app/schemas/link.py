from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import ElementStatus
from app.models import Link


class LinkCreate(BaseModel):
    source: str = Field(description="node_id of one endpoint", examples=["node_001"])
    destination: str = Field(description="node_id of the other endpoint", examples=["node_002"])
    bandwidth: float = Field(gt=0, description="Bandwidth in Mbps (must be > 0)", examples=[100])
    latency: float = Field(ge=0, description="Latency in milliseconds (must be >= 0)", examples=[10])
    packet_loss: float = Field(default=0, ge=0, le=100, description="Packet loss in percent (0-100)")


class LinkResponse(BaseModel):
    link_id: str = Field(examples=["link_001"])
    network_id: str
    source: str
    destination: str
    bandwidth: float = Field(description="Mbps")
    latency: float = Field(description="Milliseconds")
    packet_loss: float = Field(description="Percent")
    status: ElementStatus
    created_at: datetime

    @classmethod
    def from_model(cls, link: Link) -> "LinkResponse":
        return cls(
            link_id=link.id, network_id=link.network_id, source=link.source_node_id,
            destination=link.destination_node_id, bandwidth=link.bandwidth, latency=link.latency,
            packet_loss=link.packet_loss, status=link.status, created_at=link.created_at,
        )
