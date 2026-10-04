from typing import List

class ComparisonEngine:
    def compare_experiments(self, expr_details: List[dict]) -> List[dict]:
        results = []
        for e in expr_details:
            perf = e.get("performance_analysis")
            rec = e.get("recovery_analysis")
            impacts = e.get("failure_impacts", [])
            
            p_loss = perf["packet_loss"]["worst"] if perf else 0
            lat = perf["latency"]["degradation_absolute"] if perf else 0
            throughput = perf["throughput"]["worst"] if perf else 0
            avl = perf["availability"]["worst"] if perf else 100
            
            rtype = impacts[0]["failure_type"] if impacts else "Unknown"
            
            rtime = 0.0
            reffectiveness = perf["packet_loss"]["recovery_effectiveness"] if perf else 0
            
            results.append({
                "experiment_id": e["experiment"]["id"],
                "experiment_name": e["experiment"]["name"],
                "failure_type": rtype,
                "packet_loss": p_loss,
                "latency_degradation": lat,
                "throughput": throughput,
                "availability": avl,
                "recovery_time": rtime,
                "recovery_effectiveness": reffectiveness,
                "affected_traffic": sum(i["affected_traffic"] for i in impacts)
            })
            
        return results
