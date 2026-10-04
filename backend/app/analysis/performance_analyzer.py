from typing import List, Optional
from app.schemas.history import MetricComparison, PerformanceAnalysis

class PerformanceAnalyzer:
    @staticmethod
    def _calc(baseline: float, worst: float, recovered: float, final: float, lower_is_better: bool) -> MetricComparison:
        if baseline is None: return MetricComparison()
        
        deg_abs = worst - baseline
        deg_pct = (deg_abs / baseline * 100) if baseline > 0 else 0
        
        rec_imp_abs = worst - recovered
        rec_imp_pct = (rec_imp_abs / worst * 100) if worst > 0 else 0
        
        # Effectiveness (0 to 100%)
        # If lower is better (e.g. latency): effectiveness = (worst - recovered) / (worst - baseline)
        # If higher is better (e.g. bandwidth): effectiveness = (recovered - worst) / (baseline - worst)
        eff = 0.0
        if worst != baseline:
            if lower_is_better:
                eff = (worst - recovered) / (worst - baseline) * 100
            else:
                eff = (recovered - worst) / (baseline - worst) * 100
                
            eff = max(0.0, min(100.0, eff))
        elif worst == baseline and recovered == baseline:
            eff = 100.0
            
        return MetricComparison(
            baseline=baseline,
            worst=worst,
            recovered=recovered,
            final=final,
            degradation_absolute=deg_abs,
            degradation_percentage=deg_pct,
            recovery_improvement_absolute=rec_imp_abs,
            recovery_improvement_percentage=rec_imp_pct,
            recovery_effectiveness=round(eff, 2)
        )

    def analyze(self, snapshots: List[dict], baseline_id: str = None) -> Optional[PerformanceAnalysis]:
        if not snapshots:
            return None
            
        # Extrapolate Phase Snapshots based on timing (simplistic min/max tracking from the bounds)
        # Latency (lower is better)
        lats = [s["traffic"].get("average_latency", 0) for s in snapshots]
        b_lat = lats[0]
        w_lat = max(lats)
        r_lat = lats[-2] if len(lats) > 1 else lats[-1]
        f_lat = lats[-1]
        
        lat_metric = self._calc(b_lat, w_lat, r_lat, f_lat, lower_is_better=True)
        
        # Packet Loss (lower is better)
        pls = [s["traffic"].get("packet_loss_percentage", 0) for s in snapshots]
        pl_metric = self._calc(pls[0], max(pls), pls[-2] if len(pls) > 1 else pls[-1], pls[-1], lower_is_better=True)
        
        # Throughput (higher is better)
        thrs = [s["traffic"].get("throughput", 0) for s in snapshots]
        thrs_filtered = [t for t in thrs if t > 0]
        b_thr = thrs[0]
        w_thr = min(thrs) if thrs else 0
        r_thr = thrs[-2] if len(thrs) > 1 else thrs[-1]
        thr_metric = self._calc(b_thr, w_thr, r_thr, thrs[-1], lower_is_better=False)
        
        # Availability (higher is better)
        avls = [s["connectivity"].get("traffic_availability", 0) for s in snapshots]
        avl_metric = self._calc(avls[0], min(avls), avls[-2] if len(avls) > 1 else avls[-1], avls[-1], lower_is_better=False)
        
        return PerformanceAnalysis(
            latency=lat_metric,
            packet_loss=pl_metric,
            throughput=thr_metric,
            availability=avl_metric
        )
