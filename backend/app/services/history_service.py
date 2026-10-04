from pymongo.database import Database
from datetime import datetime, timezone
from typing import List

from app.errors import NotFoundError, BadRequestError
from app.schemas.history import (
    ExperimentStatus, ExperimentCreate, ExperimentResponse, EventDetail, 
    ExperimentDetailResponse
)
from app.analysis.performance_analyzer import PerformanceAnalyzer
from app.analysis.impact_analyzer import ImpactAnalyzer
from app.analysis.recovery_analyzer import RecoveryAnalyzer
from app.analysis.comparison_engine import ComparisonEngine

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

class HistoryService:
    def __init__(self, db: Database):
        self.db = db
        self.perf_analyzer = PerformanceAnalyzer()
        self.impact_analyzer = ImpactAnalyzer()
        self.recovery_analyzer = RecoveryAnalyzer()
        self.compare_engine = ComparisonEngine()

    def _next_exp_id(self, network_id: str) -> str:
        count = self.db.experiments.count_documents({"network_id": network_id})
        return f"exp_{network_id[-3:]}_{count + 1:03d}"

    def create_experiment(self, network_id: str, req: ExperimentCreate) -> ExperimentResponse:
        now = _utcnow()
        doc = {
            "id": self._next_exp_id(network_id),
            "network_id": network_id,
            "name": req.name,
            "description": req.description,
            "status": ExperimentStatus.CREATED.value,
            "started_at": now,
            "ended_at": None,
            "baseline_snapshot_id": None,
            "final_snapshot_id": None,
            "created_at": now
        }
        self.db.experiments.insert_one(doc)
        doc.pop("_id", None)
        return ExperimentResponse(**doc)
        
    def complete_experiment(self, experiment_id: str) -> ExperimentResponse:
        exp = self.db.experiments.find_one({"id": experiment_id})
        if not exp:
            raise NotFoundError(f"Experiment {experiment_id} not found")
            
        now = _utcnow()
        self.db.experiments.update_one(
            {"id": experiment_id},
            {"$set": {"status": ExperimentStatus.COMPLETED.value, "ended_at": now}}
        )
        exp["status"] = ExperimentStatus.COMPLETED.value
        exp["ended_at"] = now
        exp.pop("_id", None)
        return ExperimentResponse(**exp)

    def get_experiments(self, network_id: str, limit: int = 50) -> List[ExperimentResponse]:
        docs = self.db.experiments.find({"network_id": network_id}).sort("created_at", -1).limit(limit)
        return [ExperimentResponse(**d) for d in docs]
        
    def get_experiment_detail(self, experiment_id: str) -> ExperimentDetailResponse:
        exp = self.db.experiments.find_one({"id": experiment_id})
        if not exp:
            raise NotFoundError(f"Experiment {experiment_id} not found")
            
        nid = exp["network_id"]
        start = exp["started_at"]
        end = exp["ended_at"] or _utcnow()
        
        # 1. Gather all collections between start and end
        # Snapshots
        snaps = list(self.db.monitoring_snapshots.find({
            "network_id": nid, "timestamp": {"$gte": start, "$lte": end}
        }).sort("timestamp", 1))
        
        # Chaos
        chaos = list(self.db.chaos_experiments.find({
            "network_id": nid, "created_at": {"$gte": start, "$lte": end}
        }).sort("created_at", 1))
        
        # Recoveries
        recoveries = list(self.db.recovery_events.find({
            "network_id": nid, "created_at": {"$gte": start, "$lte": end}
        }).sort("created_at", 1))
        
        # Failures
        detections = list(self.db.failure_detections.find({
            "network_id": nid, "created_at": {"$gte": start, "$lte": end}
        }).sort("created_at", 1))

        # 2. Build Timeline
        timeline = []
        timeline.append(EventDetail(timestamp=start, event_type="EXPERIMENT_STARTED", description=f"Experiment '{exp['name']}' started", source_module="history", severity="info"))
        
        for c in chaos:
            timeline.append(EventDetail(timestamp=c["created_at"], event_type="CHAOS_INJECTED", description=f"Chaos injected: {c['chaos_type']}", source_module="chaos", severity="critical"))
            
        for d in detections:
            timeline.append(EventDetail(timestamp=d["created_at"], event_type="FAILURE_DETECTED", description=f"Failure detected: {d.get('severity')}", source_module="failure_detection", severity="high"))
            
        for r in recoveries:
            timeline.append(EventDetail(timestamp=r["created_at"], event_type="RECOVERY_STARTED", description=f"Recovery logic applied", source_module="recovery", severity="medium"))
            
        for s in snaps:
            timeline.append(EventDetail(timestamp=s["timestamp"], event_type="MONITORING_SNAPSHOT", description=f"Snapshot captured: {s['health_status']}", source_module="monitoring", severity="info"))
            
        if exp["status"] == ExperimentStatus.COMPLETED.value:
            timeline.append(EventDetail(timestamp=end, event_type="EXPERIMENT_COMPLETED", description="Experiment finished", source_module="history", severity="info"))
            
        timeline.sort(key=lambda e: e.timestamp)

        # 3. Analyze
        perf = self.perf_analyzer.analyze(snaps)
        rec = self.recovery_analyzer.analyze(recoveries)
        
        # Fake failures dict formatting based on chaos / detections
        f_list = [{"id": c["id"], "type": c["chaos_type"]} for c in chaos]
        imp = self.impact_analyzer.analyze(f_list, timeline, snaps)

        exp.pop("_id", None)
        return ExperimentDetailResponse(
            experiment=ExperimentResponse(**exp),
            timeline=timeline,
            performance_analysis=perf,
            failure_impacts=imp,
            recovery_analysis=rec
        )
        
    def compare(self, experiment_ids: List[str]) -> List[dict]:
        details = []
        for eid in experiment_ids:
            try:
                d = self.get_experiment_detail(eid)
                details.append(d.dict())
            except NotFoundError:
                pass
        return self.compare_engine.compare_experiments(details)
