from datetime import datetime

from pydantic import BaseModel, Field

from app.config import MAX_PACKET_COUNT, MAX_PACKET_SIZE
from app.enums import PacketStatus, SimulationStatus
from app.models import Packet, TrafficSimulation


class SimulationCreate(BaseModel):
    source: str = Field(description="node_id the packets start from", examples=["node_001"])
    destination: str = Field(description="node_id the packets are sent to", examples=["node_006"])
    packet_count: int = Field(gt=0, le=MAX_PACKET_COUNT, description="Number of packets to send", examples=[100])
    packet_size: int = Field(gt=0, le=MAX_PACKET_SIZE, description="Size of every packet in bytes", examples=[1024])
    random_seed: int | None = Field(
        default=None, ge=0, le=2**32 - 1,
        description="Seed for packet-loss decisions. Omit it and one is generated and stored, "
        "so the run can still be reproduced.",
        examples=[42],
    )
    store_packets: bool = Field(
        default=False,
        description="Also save one database row per packet (only allowed for small simulations).",
    )


class SimulationResponse(BaseModel):
    simulation_id: str = Field(examples=["sim_001"])
    network_id: str
    source: str
    destination: str
    packet_count: int
    packet_size: int
    random_seed: int
    store_packets: bool
    status: SimulationStatus
    failure_reason: str | None = None
    route_available: bool | None = None
    route: list[str] | None = None
    delivered_packets: int | None = None
    dropped_packets: int | None = None
    packet_loss_percentage: float | None = None
    path_latency_ms: float | None = None
    hop_count: int | None = None
    path_bandwidth_mbps: float | None = None
    throughput_mbps: float | None = None
    simulated_duration_ms: float | None = Field(default=None, description="Simulated (model) time")
    execution_duration_ms: float | None = Field(default=None, description="Real time the run took")
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_model(cls, sim: TrafficSimulation) -> "SimulationResponse":
        return cls(
            simulation_id=sim.id, network_id=sim.network_id, source=sim.source_node_id,
            destination=sim.destination_node_id, packet_count=sim.packet_count, packet_size=sim.packet_size,
            random_seed=sim.random_seed, store_packets=sim.store_packets, status=sim.status,
            failure_reason=sim.failure_reason, route_available=sim.route_available, route=sim.route,
            delivered_packets=sim.delivered_packets, dropped_packets=sim.dropped_packets,
            packet_loss_percentage=sim.packet_loss_percentage, path_latency_ms=sim.path_latency_ms,
            hop_count=sim.hop_count, path_bandwidth_mbps=sim.path_bandwidth_mbps,
            throughput_mbps=sim.throughput_mbps, simulated_duration_ms=sim.simulated_duration_ms,
            execution_duration_ms=sim.execution_duration_ms, created_at=sim.created_at,
            started_at=sim.started_at, completed_at=sim.completed_at,
        )


class MetricsResponse(BaseModel):
    """Metrics of a finished simulation. For a failed one, route_available is false and metrics are null."""
    simulation_id: str
    network_id: str
    source: str
    destination: str
    status: SimulationStatus
    failure_reason: str | None = None
    route_available: bool | None = None
    route: list[str] | None = None
    packet_count: int
    packet_size: int
    random_seed: int
    delivered_packets: int | None = None
    dropped_packets: int | None = None
    packet_loss_percentage: float | None = None
    total_data_transferred_bytes: int | None = Field(default=None, description="delivered_packets * packet_size")
    path_latency_ms: float | None = None
    hop_count: int | None = None
    path_bandwidth_mbps: float | None = None
    throughput_mbps: float | None = None
    simulated_duration_ms: float | None = Field(default=None, description="Simulated (model) time")
    execution_duration_ms: float | None = Field(default=None, description="Real time the run took")

    @classmethod
    def from_model(cls, sim: TrafficSimulation) -> "MetricsResponse":
        delivered = sim.delivered_packets
        return cls(
            simulation_id=sim.id, network_id=sim.network_id, source=sim.source_node_id,
            destination=sim.destination_node_id, status=sim.status, failure_reason=sim.failure_reason,
            route_available=sim.route_available, route=sim.route, packet_count=sim.packet_count,
            packet_size=sim.packet_size, random_seed=sim.random_seed, delivered_packets=delivered,
            dropped_packets=sim.dropped_packets, packet_loss_percentage=sim.packet_loss_percentage,
            total_data_transferred_bytes=None if delivered is None else delivered * sim.packet_size,
            path_latency_ms=sim.path_latency_ms, hop_count=sim.hop_count,
            path_bandwidth_mbps=sim.path_bandwidth_mbps, throughput_mbps=sim.throughput_mbps,
            simulated_duration_ms=sim.simulated_duration_ms, execution_duration_ms=sim.execution_duration_ms,
        )


class PacketResponse(BaseModel):
    packet_id: str = Field(examples=["pkt_001"])
    simulation_id: str
    sequence_number: int
    source: str
    destination: str
    packet_size: int
    status: PacketStatus
    route: list[str]
    dropped_at_link_id: str | None = None
    completed_at_ms: float = Field(description="Simulated time the packet was delivered or dropped")
    created_at: datetime

    @classmethod
    def from_model(cls, packet: Packet) -> "PacketResponse":
        return cls(
            packet_id=packet.packet_id, simulation_id=packet.simulation_id,
            sequence_number=packet.sequence_number, source=packet.source_node_id,
            destination=packet.destination_node_id, packet_size=packet.packet_size, status=packet.status,
            route=packet.route, dropped_at_link_id=packet.dropped_at_link_id,
            completed_at_ms=packet.completed_at_ms, created_at=packet.created_at,
        )


class PacketPage(BaseModel):
    total: int = Field(description="Packets stored for this simulation (0 unless store_packets was set)")
    limit: int
    offset: int
    packets: list[PacketResponse]
