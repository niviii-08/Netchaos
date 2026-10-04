from typing import List
from app.schemas.history import FailureImpact

class ImpactAnalyzer:
    @staticmethod
    def calculate_impact_score(traffic_affected: int, part_created: int, lat_pct: float, loss: float, thr_pct: float, avl_loss: float) -> float:
        # Configurable weighting parameters (as per req docs)
        tw = 1.0 # Traffic weight
        aw = 2.0 # Availability weight
        pw = 1.5 # Packet loss weight
        lw = 0.5 # Latency weight
        
        score = (tw * traffic_affected) + (aw * avl_loss) + (pw * loss) + (lw * lat_pct)
        if part_created > 0:
            score += (part_created * 50)
            
        return round(score, 2)

    def analyze(self, failures: List[dict], timeline: List[dict], snapshots: List[dict]) -> List[FailureImpact]:
        # Synthesizes impact of failures observed from timeline/snapshots
        impacts = []
        
        if not snapshots: return impacts
        b_lat = snapshots[0]["traffic"].get("average_latency", 0)
        b_loss = snapshots[0]["traffic"].get("packet_loss_percentage", 0)
        b_thr = snapshots[0]["traffic"].get("throughput", 0)
        b_avl = snapshots[0]["connectivity"].get("traffic_availability", 100)
        
        # for each failure, we measure the worst state during the experiment
        for f in failures:
            # We assume failure impact is the worst divergence in the snapshots
            w_lat = max(s["traffic"].get("average_latency", 0) for s in snapshots)
            w_loss = max(s["traffic"].get("packet_loss_percentage", 0) for s in snapshots)
            w_thr = min(s["traffic"].get("throughput", 0) for s in snapshots)
            w_avl = min(s["connectivity"].get("traffic_availability", 0) for s in snapshots)
            
            lat_change = ((w_lat - b_lat) / b_lat * 100) if b_lat > 0 else 0
            loss_change = w_loss - b_loss
            thr_change = ((b_thr - w_thr) / b_thr * 100) if b_thr > 0 else 0
            avl_change = b_avl - w_avl
            
            score = self.calculate_impact_score(
               traffic_affected=1, # Mocking per-flow granularity
               part_created=1 if w_avl == 0 else 0,
               lat_pct=lat_change,
               loss=loss_change,
               thr_pct=thr_change,
               avl_loss=avl_change
            )
            
            impacts.append(FailureImpact(
                failure_id=f.get("id", "f_01"),
                failure_type=f.get("type", "unknown"),
                affected_nodes=1 if "node" in f.get("type", "") else 0,
                affected_links=1 if "link" in f.get("type", "") else 0,
                affected_traffic=1,
                partitions_created=1 if w_avl == 0 else 0,
                packet_loss_change=loss_change,
                latency_change_percent=lat_change,
                throughput_change_percent=thr_change,
                availability_change=avl_change,
                impact_score=score
            ))
            
        return sorted(impacts, key=lambda i: i.impact_score, reverse=True)
