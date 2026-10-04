# NetChaos Analytics & Research Evaluation

This document details the analysis metrics implemented in **Module 10** for evaluating network resilience against chaos.

## Metrics & Definitions
We define several project-specific networking metrics:

1. **Recovery Time**: The duration (in seconds) between detecting a failure and successfully provisioning an alternative route.
2. **Connectivity Preservation**: The percentage of original reachable traffic routes that remain available after an injected failure.
3. **Recovery Effectiveness**: Measures to what degree baseline performance was restored.

## Formulas
These are the exact formulas calculated by `ResilienceAnalyticsService`:
- `Latency Degradation (%)` = `((Chaos Latency - Baseline Latency) / Baseline Latency) * 100` (Bounded using min/max normalization).
- `Impact Score`: A weighted index evaluating combined damage:
   - 30% Connectivity Loss
   - 20% Latency Degradation
   - 20% Packet Loss
   - 15% Throughput Reduction
   - 15% Recovery Interval
- `Resilience Score`: `0.4 * Avg Connectivity + 0.4 * Total Recoverability %`

## Assumptions & Limitations
- Analytics currently approximate timestamps by relying on chronological events bounded between `experiment.started_at` and `experiment.ended_at`.
- A failure is declared "Unrecoverable" strictly if no corresponding `RECOVERED` event is parsed by the Recovery Service within the lifespan of the experiment.
- *Sample Size Limitations*: The frontend dashboard will explicitly warn if too few experiments have been executed since statistical averages can be heavily skewed by one unrecoverable edge case.

## Academic Honesty & Interpretation
In our simulation experiments, the targeted topology's resilience is evaluated entirely through NetChaos-defined scoring. The Resilience Score is an internal relative index to compare the infrastructure against itself (e.g. comparing Link Failures vs Router Failures), not an industry-standard benchmark, nor a claim about real-world network performance without empirical validation. Wait for statistical maturity (>10 experiments) before finalizing findings.
