from typing import List
from app.schemas.history import RecoveryAnalysis, RouteSummary

class RecoveryAnalyzer:
    def analyze(self, recoveries: List[dict]) -> RecoveryAnalysis:
        if not recoveries:
            return RecoveryAnalysis(total_events=0, successful=0, failed=0, routes=[])
            
        success = [r for r in recoveries if r.get("recovery_status") == "RECOVERED"]
        failed = len(recoveries) - len(success)
        
        routes = []
        for r in recoveries:
            routes.append(RouteSummary(
                original_route=r.get("original_route") or [],
                recovered_route=r.get("recovered_route") or [],
                route_changed=r.get("route_changed", False),
                hop_difference=len(r.get("recovered_route") or []) - len(r.get("original_route") or []),
                latency_difference=r.get("recovered_latency", 0) - r.get("original_latency", 0),
                bandwidth_difference=r.get("recovered_bandwidth", 0) - r.get("original_bandwidth", 0)
            ))
            
        return RecoveryAnalysis(
            total_events=len(recoveries),
            successful=len(success),
            failed=failed,
            routes=routes
        )
