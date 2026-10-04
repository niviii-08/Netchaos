from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import ElementStatus, NodeType
from app.models import Node
from app.schemas.network import Name


class NodeCreate(BaseModel):
    name: Name = Field(description="Node name, unique within the network", examples=["Router-A"])
    type: NodeType = Field(description="One of: router, host, server, client")


class NodeResponse(BaseModel):
    node_id: str = Field(examples=["node_001"])
    network_id: str
    name: str
    type: NodeType
    status: ElementStatus
    created_at: datetime

    @classmethod
    def from_model(cls, node: Node) -> "NodeResponse":
        return cls(
            node_id=node.id, network_id=node.network_id, name=node.name,
            type=node.type, status=node.status, created_at=node.created_at,
        )
