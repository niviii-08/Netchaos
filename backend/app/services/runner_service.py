from datetime import datetime, timezone
from pymongo.database import Database
from typing import List, Dict, Any, Optional
import threading
import time

from app.errors import NotFoundError, BadRequestError
from app.schemas.runner import (
    ExperimentPlanCreate, ExperimentPlanResponse, ExperimentRunStatus
)

# Services to Orchestrate
from app.services.topology_service import TopologyService
from app.services.traffic_service import TrafficService
from app.schemas.traffic import SimulationCreate
from app.services.chaos_service import ChaosService
from app.schemas.chaos import (
    RouterFailureRequest, LinkFailureRequest, PacketLossRequest, LatencyRequest, BandwidthReductionRequest
)
from app.services.monitoring_service import MonitoringService
from app.services.history_service import HistoryService
from app.schemas.history import ExperimentCreate
from app.services.failure_detection_service import FailureDetectionService
from app.services.recovery_service import RecoveryService
from app.schemas.recovery import RoutePreviewRequest, RecoveryRequest

def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

class RunnerService:
    def __init__(self, db: Database, graphs: dict):
        self.db = db
        self.topology = TopologyService(db, graphs)
        self.traffic = TrafficService(db, graphs)
        self.chaos = ChaosService(db, graphs)
        self.history = HistoryService(db)
        self.monitoring = MonitoringService(db)
        self.failures = FailureDetectionService(db)
        self.recovery = RecoveryService(db)
        
        # Max limits
        self.MAX_RUNS = 100

    def _generate_plan_id(self, network_id: str) -> str:
        count = self.db.experiment_plans.count_documents({"network_id": network_id})
        return f"plan_{network_id[-3:]}_{count + 1:03d}"

    def create_plan(self, req: ExperimentPlanCreate) -> ExperimentPlanResponse:
        # Validate limitations
        total_runs = req.repetitions
        if req.sweep:
            total_runs *= len(req.sweep.values)
            
        if total_runs > self.MAX_RUNS:
            raise BadRequestError(f"Plan exceeds max runs allowed ({total_runs} > {self.MAX_RUNS})")
        
        if total_runs <= 0:
            raise BadRequestError("Plan must have at least 1 run")
            
        plan_id = self._generate_plan_id(req.network_id)
        now = _utc_now()
        
        # generate runs
        runs = []
        run_number = 1
        
        sweep_values = req.sweep.values if req.sweep else [None]
        for val in sweep_values:
            for rep in range(req.repetitions):
                config = {
                    "sweep_parameter": req.sweep.parameter if req.sweep else None,
                    "sweep_value": val,
                    "repetition": rep + 1
                }
                runs.append({
                    "run_id": f"{plan_id}_run{run_number:03d}",
                    "experiment_id": None,
                    "run_number": run_number,
                    "status": "PENDING",
                    "error": None,
                    "started_at": None,
                    "completed_at": None,
                    "configuration": config
                })
                run_number += 1
                
        plan_doc = {
            "id": plan_id,
            "name": req.name,
            "description": req.description,
            "network_id": req.network_id,
            "traffic": req.traffic.model_dump(),
            "chaos": req.chaos.model_dump(),
            "recovery": req.recovery.model_dump(),
            "repetitions": req.repetitions,
            "random_seed": req.random_seed,
            "sweep": req.sweep.model_dump() if req.sweep else None,
            "status": "CREATED",
            "total_runs": total_runs,
            "completed_runs": 0,
            "failed_runs": 0,
            "cancelled_runs": 0,
            "progress_percentage": 0.0,
            "runs": runs,
            "created_at": now
        }
        
        self.db.experiment_plans.insert_one(plan_doc)
        
        # Convert internal ObjectId before returning
        plan_doc.pop("_id", None)
        return ExperimentPlanResponse(
            plan_id=plan_doc["id"],
            name=plan_doc["name"],
            network_id=plan_doc["network_id"],
            status=plan_doc["status"],
            total_runs=plan_doc["total_runs"],
            completed_runs=plan_doc["completed_runs"],
            failed_runs=plan_doc["failed_runs"],
            cancelled_runs=plan_doc["cancelled_runs"],
            progress_percentage=plan_doc["progress_percentage"],
            runs=[ExperimentRunStatus(**r) for r in plan_doc["runs"]],
            created_at=plan_doc["created_at"]
        )

    def get_plan(self, plan_id: str) -> ExperimentPlanResponse:
        plan_doc = self.db.experiment_plans.find_one({"id": plan_id})
        if not plan_doc:
            raise NotFoundError(f"Plan {plan_id} not found")
            
        progress = 0.0
        if plan_doc["total_runs"] > 0:
            finished = plan_doc["completed_runs"] + plan_doc["failed_runs"] + plan_doc["cancelled_runs"]
            progress = (finished / plan_doc["total_runs"]) * 100
        plan_doc["progress_percentage"] = progress
        
        plan_doc.pop("_id", None)
        return ExperimentPlanResponse(
            plan_id=plan_doc["id"],
            name=plan_doc["name"],
            network_id=plan_doc["network_id"],
            status=plan_doc["status"],
            total_runs=plan_doc["total_runs"],
            completed_runs=plan_doc["completed_runs"],
            failed_runs=plan_doc["failed_runs"],
            cancelled_runs=plan_doc["cancelled_runs"],
            progress_percentage=plan_doc.get("progress_percentage", 0.0),
            runs=[ExperimentRunStatus(**r) for r in plan_doc.get("runs", [])],
            created_at=plan_doc["created_at"]
        )

    def run_plan_async(self, plan_id: str):
        # Fire and forget threading task
        t = threading.Thread(target=self._execute_plan_sync, args=(plan_id,))
        t.start()

    def _execute_plan_sync(self, plan_id: str):
        plan_doc = self.db.experiment_plans.find_one({"id": plan_id})
        if not plan_doc or plan_doc["status"] != "CREATED":
            return
            
        self._update_plan_status(plan_id, "RUNNING")
        
        nid = plan_doc["network_id"]
        runs = plan_doc["runs"]
        
        for i, run in enumerate(runs):
            # Check for cancellation
            cur_plan = self.db.experiment_plans.find_one({"id": plan_id})
            if cur_plan["status"] == "CANCELLED":
                self._update_run_status(plan_id, run["run_id"], "CANCELLED")
                continue
                
            try:
                self._execute_single_run(plan_doc, run, i)
                self._update_run_status(plan_id, run["run_id"], "COMPLETED")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._update_run_status(plan_id, run["run_id"], "FAILED", error=str(e))
                self.db.experiment_plans.update_one({"id": plan_id}, {"$inc": {"failed_runs": 1}})
                # Attempt absolute cleanup on crash
                self._force_cleanup(nid)
            
            # small delay between runs context resets
            time.sleep(0.5)

        # Final loop evaluation
        final_doc = self.db.experiment_plans.find_one({"id": plan_id})
        succ = final_doc["completed_runs"]
        fail = final_doc["failed_runs"]
        canc = final_doc["cancelled_runs"]
        
        if canc > 0:
            final_status = "CANCELLED"
        elif fail > 0 and succ > 0:
            final_status = "PARTIAL"
        elif fail > 0 and succ == 0:
            final_status = "FAILED"
        else:
            final_status = "COMPLETED"
            
        self._update_plan_status(plan_id, final_status)

    def _execute_single_run(self, plan_doc: dict, run: dict, run_idx: int):
        self._update_run_status(plan_doc["id"], run["run_id"], "RUNNING", started=True)
        nid = plan_doc["network_id"]
        run_cfg = run["configuration"]
        
        # 0. Prep / Apply Sweep Chaos Properties
        chaos_cfg = plan_doc["chaos"].copy()
        if run_cfg["sweep_parameter"] and chaos_cfg["parameters"] is not None:
            # We enforce exact matches. If packet_loss sweep, update it:
            if run_cfg["sweep_parameter"] in chaos_cfg["parameters"]:
                chaos_cfg["parameters"][run_cfg["sweep_parameter"]] = run_cfg["sweep_value"]
            elif run_cfg["sweep_parameter"] in chaos_cfg:
                chaos_cfg[run_cfg["sweep_parameter"]] = run_cfg["sweep_value"]
        
        try:
            # 1. Capture baseline (Create Failure baseline)
            self.failures.create_baseline(nid)
            
            # 2. Start experiment using History module
            exp_req = ExperimentCreate(name=f"{plan_doc['name']} - Run {run['run_number']}", description=plan_doc.get("description") or "Automated Run")
            exp = self.history.create_experiment(nid, exp_req)
            self.db.experiment_plans.update_one(
                {"id": plan_doc["id"], "runs.run_id": run["run_id"]},
                {"$set": {"runs.$.experiment_id": exp.id}}
            )
            
            # 3. Form traffic payload and simulate baseline flow
            t_req = SimulationCreate(
                source=plan_doc["traffic"]["source"],
                destination=plan_doc["traffic"]["destination"],
                packet_count=plan_doc["traffic"]["packet_count"],
                packet_size=plan_doc["traffic"]["packet_size"],
            )
            sim_baseline = self.traffic.create_simulation(nid, t_req)
            self.traffic.run_simulation(nid, sim_baseline["id"])
            
            # 4. Inject Chaos
            t_params = chaos_cfg.get("parameters", {})
            chaos_type = chaos_cfg.get("type", "").lower()
            
            if chaos_type == "link_failure":
                chaos_req = LinkFailureRequest(link_id=chaos_cfg["target"])
            elif chaos_type == "router_failure":
                chaos_req = RouterFailureRequest(node_id=chaos_cfg["target"])
            elif chaos_type == "packet_loss":
                chaos_req = PacketLossRequest(link_id=chaos_cfg["target"], packet_loss=t_params.get("loss_percentage", 10.0))
            elif chaos_type == "latency":
                chaos_req = LatencyRequest(link_id=chaos_cfg["target"], latency=t_params.get("additional_latency_ms", 50.0))
            elif chaos_type == "bandwidth_reduction":
                chaos_req = BandwidthReductionRequest(link_id=chaos_cfg["target"], bandwidth=t_params.get("reduction_percentage", 50.0))
            else:
                raise BadRequestError(f"Unsupported chaos type: {chaos_type}")
                
            chaos_res = self.chaos.apply(nid, chaos_req.to_experiment())
            
            # 5. Simulate chaos flow (Failed traffic)
            sim_chaos = self.traffic.create_simulation(nid, t_req)
            self.traffic.run_simulation(nid, sim_chaos["id"])
            
            # 6. Detect Failure
            self.failures.detect_failures(nid)
            
            # 7. Recovery (if enabled)
            if plan_doc["recovery"].get("enabled", True):
                strat = plan_doc["recovery"].get("strategy", "shortest_hop")
                recovery_req = RecoveryRequest(simulation_id=sim_baseline["id"], strategy=strat)
                self.recovery.apply_recovery(nid, recovery_req)
                
            # 8. Monitor snapshot state
            self.monitoring.create_snapshot(nid)
            
            # 9. Revert chaos explicitly
            self.chaos.revert(nid, chaos_res.experiment_id)
            
            # 10. Complete experiment history
            self.history.complete_experiment(exp.id)
            
        except Exception as e:
            # Force revert if anything failed and chaos was injected
            self._force_cleanup(nid)
            raise e
            
    def _force_cleanup(self, nid: str):
        # Attempt to aggressively revert all ACTIVE chaos experiments for the network
        active_chaoses = list(self.db.chaos_experiments.find({"network_id": nid, "status": "ACTIVE"}))
        for c in active_chaoses:
            try:
                self.chaos.revert(nid, c["id"])
            except Exception:
                pass
                
    def _update_plan_status(self, plan_id: str, status: str):
        self.db.experiment_plans.update_one({"id": plan_id}, {"$set": {"status": status}})
        
    def _update_run_status(self, plan_id: str, run_id: str, status: str, started=False, error=None):
        update_doc = {"runs.$.status": status}
        if started:
            update_doc["runs.$.started_at"] = _utc_now()
        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            update_doc["runs.$.completed_at"] = _utc_now()
        if error:
            update_doc["runs.$.error"] = error
            
        self.db.experiment_plans.update_one(
            {"id": plan_id, "runs.run_id": run_id},
            {"$set": update_doc}
        )
        
        if status == "COMPLETED":
            self.db.experiment_plans.update_one({"id": plan_id}, {"$inc": {"completed_runs": 1}})
        elif status == "CANCELLED":
            self.db.experiment_plans.update_one({"id": plan_id}, {"$inc": {"cancelled_runs": 1}})

    def cancel_plan(self, plan_id: str):
        plan = self.db.experiment_plans.find_one({"id": plan_id})
        if not plan:
            raise NotFoundError(f"Plan {plan_id} not found")
            
        if plan["status"] in ["COMPLETED", "FAILED", "CANCELLED", "PARTIAL"]:
            return  # Already finalized
            
        self._update_plan_status(plan_id, "CANCELLED")

    def get_plan_results(self, plan_id: str) -> dict:
        plan = self.db.experiment_plans.find_one({"id": plan_id})
        if not plan:
            raise NotFoundError(f"Plan {plan_id} not found")
            
        from app.services.resilience_analytics_service import ResilienceAnalyticsService
        analytics = ResilienceAnalyticsService(self.db)
        
        results = []
        for run in plan.get("runs", []):
            if run["status"] == "COMPLETED" and run.get("experiment_id"):
                try:
                    stats = analytics.get_experiment_analytics(run["experiment_id"])
                    results.append({
                        "run_id": run["run_id"],
                        "experiment_id": run["experiment_id"],
                        "scenario": run["configuration"],
                        "analytics": stats.model_dump()
                    })
                except Exception:
                    pass
                    
        return {
            "plan_id": plan["id"],
            "total_runs": plan["total_runs"],
            "completed_runs": plan["completed_runs"],
            "results": results
        }
