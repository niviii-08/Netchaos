import uuid
import datetime
from typing import List, Dict, Any, Optional
from pymongo.database import Database

from app.schemas.dataset import (
    DatasetManifest, DatasetRecord, DatasetFilter, DatasetResponse, DatasetStatistics, DatasetCreate
)
from app.errors import NotFoundError, BadRequestError
from app.services.resilience_analytics_service import ResilienceAnalyticsService
from app.services.history_service import HistoryService
from app.services.runner_service import RunnerService

class DatasetService:
    def __init__(self, db: Database, graph_manager=None):
        self.db = db
        self.analytics = ResilienceAnalyticsService(db)
        self.history = HistoryService(db)
        self.runner = RunnerService(db, graph_manager) if graph_manager else None

    def get_datasets(self) -> List[DatasetManifest]:
        docs = list(self.db.datasets.find().sort("created_at", -1))
        return [DatasetManifest(**doc) for doc in docs]

    def get_dataset(self, dataset_id: str) -> DatasetResponse:
        doc = self.db.datasets.find_one({"dataset_id": dataset_id})
        if not doc:
            raise NotFoundError(f"Dataset {dataset_id} not found")
            
        records = list(self.db.dataset_records.find({"dataset_id": dataset_id}))
        return DatasetResponse(
            dataset_id=dataset_id,
            metadata=DatasetManifest(**doc),
            records=[DatasetRecord(**r) for r in records]
        )
        
    def _matches_filters(self, record: dict, filters: Optional[DatasetFilter]) -> bool:
        if not filters:
            return True
        if filters.failure_types and record.get("chaos_type") not in filters.failure_types:
            return False
        if filters.topologies and record.get("topology_type") not in filters.topologies:
            return False
        if filters.recovery_outcomes and record.get("recovery_outcome") not in filters.recovery_outcomes:
            return False
        if filters.require_runner_only and not record.get("plan_id"):
            return False
        return True

    def create_dataset(self, req: DatasetCreate) -> DatasetManifest:
        dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
        
        # We process all plans and stand-alone experiments to build records.
        # But for scaling, we'll iterate experiments from history since that's the ultimate source of truth.
        experiments = list(self.db.experiments.find({"status": "COMPLETED"}))
        
        # map plan run -> experiment
        exp_to_plan_run = {}
        for plan in self.db.experiment_plans.find({"status": {"$in": ["COMPLETED", "PARTIAL", "FAILED"]}}):
            for run in plan.get("runs", []):
                if run.get("experiment_id"):
                    exp_to_plan_run[run["experiment_id"]] = {
                        "plan_id": plan["plan_id"],
                        "run_id": run.get("run_id")
                    }
                    
        records_to_insert = []
        source_exps = []
        
        for exp in experiments:
            exp_id = exp["id"]
            nid = exp["network_id"]
            
            # Extract Analytics if available
            try:
                analytics = self.analytics.analyze_experiment(exp_id)
            except Exception: # In case there's missing data for analytics
                analytics = None
                
            # Network stats
            net = self.db.networks.find_one({"id": nid})
            topology_type = net.get("topology", "unknown") if net else "unknown"
            node_count = self.db.nodes.count_documents({"network_id": nid})
            link_count = self.db.links.count_documents({"network_id": nid})
            
            # Baseline, Chaos, Recovery states from experiment document
            # The experiment document has baseline_state, chaos_events, failure_events, recovery_events
            chaos_events = exp.get("chaos_events", [])
            recovery_events = exp.get("recovery_events", [])
            
            chaos_type = None
            chaos_target = None
            chaos_severity = None
            p_loss = None
            lat = None
            bw = None
            
            if chaos_events:
                ce = chaos_events[0]
                chaos_type = ce.get("type", "unknown")
                chaos_target = ce.get("target")
                params = ce.get("parameters", {})
                if chaos_type == "packet_loss":
                    p_loss = params.get("loss_percentage")
                    chaos_severity = str(p_loss)
                elif chaos_type == "latency":
                    lat = params.get("additional_latency_ms")
                    chaos_severity = str(lat)
                elif chaos_type == "bandwidth_reduction":
                    bw = params.get("bandwidth")
                    chaos_severity = str(bw)
            
            # Traffic
            traffic = None
            t_sims = exp.get("simulations", [])
            dt_sims = list(self.db.traffic_simulations.find({"id": {"$in": t_sims}}).sort("started_at", 1))
            
            src = None
            dest = None
            p_count = None
            p_size = None
            delivered = None
            dropped = None
            base_lat = None
            chaos_lat = None
            rec_lat = None
            
            if dt_sims:
                first_sim = dt_sims[0]
                src = first_sim.get("source")
                dest = first_sim.get("destination")
                p_count = first_sim.get("packet_count")
                p_size = first_sim.get("packet_size")
                if first_sim.get("status") == "COMPLETED":
                    res = first_sim.get("result", {})
                    delivered = res.get("delivered", 0)
                    dropped = res.get("dropped", 0)
                    base_lat = res.get("average_latency")
                
                if len(dt_sims) > 1:
                    c_sim = dt_sims[1]
                    if c_sim.get("status") == "COMPLETED":
                        c_res = c_sim.get("result", {})
                        chaos_lat = c_res.get("average_latency")
                
                if len(dt_sims) > 2:
                    r_sim = dt_sims[2]
                    if r_sim.get("status") == "COMPLETED":
                        r_res = r_sim.get("result", {})
                        rec_lat = r_res.get("average_latency")
            
            # Recovery
            rec_attempted = len(recovery_events) > 0
            rec_outcome = "NOT_ATTEMPTED"
            orig_len = None
            rec_len = None
            route_changed = None
            rec_time = None
            
            if rec_attempted:
                re = recovery_events[0]
                rec_outcome = re.get("status", "NOT_ATTEMPTED") # e.g. RECOVERED, UNRECOVERABLE
                if rec_outcome == "SUCCESS":
                    rec_outcome = "RECOVERED"
                if rec_outcome == "FAILED":
                    rec_outcome = "UNRECOVERABLE"
                    
                path = re.get("recovery_path", [])
                if path:
                    rec_len = len(path)
                
                # Fetch baseline topology or path
                orig_len = None # Difficult to pull directly without path trace, check Analytics
                
                # Time
                start_re = re.get("started_at")
                end_re = re.get("ended_at")
                if start_re and end_re:
                    if isinstance(start_re, str):
                        start_re = datetime.datetime.fromisoformat(start_re.replace("Z", "+00:00"))
                    if isinstance(end_re, str):
                        end_re = datetime.datetime.fromisoformat(end_re.replace("Z", "+00:00"))
                    rec_time = (end_re - start_re).total_seconds()
            
            # Build Record dictionary
            rec_dict = {
                "dataset_version": req.version,
                "experiment_id": exp_id,
                "network_id": nid,
                
                "topology_type": topology_type,
                "node_count": node_count,
                "link_count": link_count,
                
                "source_node": src,
                "destination_node": dest,
                "packet_count": p_count,
                "packet_size": p_size,
                "delivered_packets": delivered,
                "dropped_packets": dropped,
                
                "baseline_latency": base_lat,
                "chaos_latency": chaos_lat,
                "recovered_latency": rec_lat,
                
                "chaos_type": chaos_type,
                "chaos_target": chaos_target,
                "chaos_severity": str(chaos_severity) if chaos_severity else None,
                "packet_loss_injected": p_loss,
                "latency_injected": lat,
                "bandwidth_reduction": bw,
                "multiple_failure_count": len(chaos_events) if chaos_events else 0,
                
                "failure_detected": len(exp.get("failure_events", [])) > 0,
                
                "recovery_attempted": rec_attempted,
                "recovery_outcome": rec_outcome,
                "recovered_route_length": rec_len,
                "recovery_time": rec_time,
                
                # Default empty
                "data_quality": "VALID",
                "validation_warnings": []
            }
            
            pl_loss_pct = None
            if delivered is not None and dropped is not None:
                tot = delivered + dropped
                if tot > 0:
                    pl_loss_pct = (dropped / tot) * 100
            rec_dict["packet_loss_percentage"] = pl_loss_pct
            
            if analytics:
                rec_dict["latency_degradation_percentage"] = analytics.latency_degradation
                rec_dict["packet_loss_degradation_percentage"] = analytics.packet_loss_degradation
                rec_dict["throughput_degradation_percentage"] = analytics.throughput_degradation
                
                if analytics.resilience:
                    rm = analytics.resilience
                    rec_dict["connectivity_preservation"] = rm.connectivity_preservation
                    rec_dict["performance_preservation"] = rm.performance_preservation
                    rec_dict["recovery_effectiveness"] = rm.recovery_effectiveness
                    rec_dict["resilience_score"] = rm.resilience_score
                    rec_dict["impact_score"] = rm.impact_score
                    
            if exp_id in exp_to_plan_run:
                rec_dict["plan_id"] = exp_to_plan_run[exp_id]["plan_id"]
                rec_dict["run_id"] = exp_to_plan_run[exp_id]["run_id"]
                
            # Filter
            if self._matches_filters(rec_dict, req.filters):
                
                # Validation
                warnings = []
                data_quality = "VALID"
                
                if rec_dict.get("packet_count") is not None and delivered is not None and dropped is not None:
                    if rec_dict["packet_count"] != (delivered + dropped):
                        warnings.append("packet_count != delivered + dropped")
                        data_quality = "INVALID"
                
                if rec_dict.get("recovery_time") is not None and rec_dict["recovery_time"] < 0:
                    warnings.append("Negative recovery time")
                    data_quality = "INVALID"
                    
                if not rec_dict.get("source_node") or not rec_dict.get("chaos_type"):
                    warnings.append("Missing critical features (source or chaos type)")
                    data_quality = "PARTIAL" if data_quality == "VALID" else data_quality
                    
                rec_dict["validation_warnings"] = warnings
                rec_dict["data_quality"] = data_quality
                
                rec_obj = DatasetRecord(**rec_dict)
                records_to_insert.append(rec_obj.model_dump())
                source_exps.append(exp_id)
                
        # Save records & manifest
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            name=req.name,
            description=req.description,
            version=req.version,
            record_count=len(records_to_insert),
            source_experiments=source_exps,
            filters=req.filters
        )
        
        self.db.datasets.insert_one(manifest.model_dump(by_alias=True))
        
        if records_to_insert:
            # tag with dataset_id
            for ri in records_to_insert:
                ri["dataset_id"] = dataset_id
            self.db.dataset_records.insert_many(records_to_insert)
            
        return manifest
        
    def get_dataset_statistics(self, dataset_id: str) -> DatasetStatistics:
        doc = self.get_dataset(dataset_id)
        
        quality_counts = {"VALID": 0, "PARTIAL": 0, "INVALID": 0}
        failure_dist = {}
        recovery_dist = {}
        
        res_scores = []
        imp_scores = []
        rec_times = []
        
        for rec in doc.records:
            quality_counts[rec.data_quality] += 1
            
            ct = rec.chaos_type or "unknown"
            failure_dist[ct] = failure_dist.get(ct, 0) + 1
            
            ro = rec.recovery_outcome
            recovery_dist[ro] = recovery_dist.get(ro, 0) + 1
            
            if rec.resilience_score is not None:
                res_scores.append(rec.resilience_score)
            if rec.impact_score is not None:
                imp_scores.append(rec.impact_score)
            if rec.recovery_time is not None:
                rec_times.append(rec.recovery_time)
                
        def stats(arr):
            if not arr: return None
            return {
                "count": len(arr),
                "mean": sum(arr)/len(arr),
                "min": min(arr),
                "max": max(arr)
            }
            
        return DatasetStatistics(
            total_records=len(doc.records),
            data_quality_report=quality_counts,
            failure_distribution=failure_dist,
            recovery_distribution=recovery_dist,
            metrics={
                "resilience_score": stats(res_scores),
                "impact_score": stats(imp_scores),
                "recovery_time": stats(rec_times)
            }
        )
