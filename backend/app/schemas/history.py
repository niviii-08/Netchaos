from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ExperimentStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ExperimentCreate(BaseModel):
    name: str
    description: str

class MetricComparison(BaseModel):
    baseline: Optional[float]
    worst: Optional[float]
    recovered: Optional[float]
    final: Optional[float]
    degradation_absolute: Optional[float]
    degradation_percentage: Optional[float]
    recovery_improvement_absolute: Optional[float]
    recovery_improvement_percentage: Optional[float]
    recovery_effectiveness: Optional[float]  # 0-100%

class PerformanceAnalysis(BaseModel):
    latency: MetricComparison
    packet_loss: MetricComparison
    throughput: MetricComparison
    availability: MetricComparison

class EventDetail(BaseModel):
    timestamp: datetime
    event_type: str
    description: str
    source_module: str
    severity: str

class FailureImpact(BaseModel):
    failure_id: str
    failure_type: str
    affected_nodes: int
    affected_links: int
    affected_traffic: int
    partitions_created: int
    packet_loss_change: float
    latency_change_percent: float
    throughput_change_percent: float
    availability_change: float
    impact_score: float

class RouteSummary(BaseModel):
    original_route: List[str]
    recovered_route: List[str]
    route_changed: bool
    hop_difference: int
    latency_difference: float
    bandwidth_difference: float

class RecoveryAnalysis(BaseModel):
    total_events: int
    successful: int
    failed: int
    routes: List[RouteSummary]

class ExperimentResponse(BaseModel):
    id: str
    network_id: str
    name: str
    description: str
    status: ExperimentStatus
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    baseline_snapshot_id: Optional[str]
    final_snapshot_id: Optional[str]
    created_at: datetime
    
class ExperimentDetailResponse(BaseModel):
    experiment: ExperimentResponse
    timeline: List[EventDetail]
    performance_analysis: Optional[PerformanceAnalysis]
    failure_impacts: List[FailureImpact]
    recovery_analysis: Optional[RecoveryAnalysis]
