import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { ActiveChaosPanel, ChaosHistory, ChaosPanel } from "./components/Chaos.jsx";
import { DetailsPanel, LinkForm, NetworkPanel, NodeForm, TemplatePanel } from "./components/Panels.jsx";
import TopologyCanvas from "./components/TopologyCanvas.jsx";
import { TrafficPanel, TrafficResults } from "./components/Traffic.jsx";
import Failures from "./components/Failures.jsx";
import RecoveryPanel from "./components/Recovery.jsx";

const EMPTY_TOPOLOGY = { nodes: [], links: [], summary: { nodes: 0, links: 0, active_nodes: 0, active_links: 0 } };

export default function App() {
  const [networks, setNetworks] = useState([]);
  const [networkId, setNetworkId] = useState(null);
  const [loadedTopology, setLoadedTopology] = useState(EMPTY_TOPOLOGY);
  const [selection, setSelection] = useState(null);
  const [error, setError] = useState(null);
  const [simulations, setSimulations] = useState([]);
  const [selectedSimId, setSelectedSimId] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [chaosActive, setChaosActive] = useState([]);
  const [chaosHistory, setChaosHistory] = useState([]);

  const refreshTopology = useCallback(async (id) => {
    setLoadedTopology(id ? await api.getTopology(id) : EMPTY_TOPOLOGY);
  }, []);

  // Runs an API action, shows any error, and reports whether it succeeded.
  const run = useCallback(async (action) => {
    setError(null);
    try {
      await action();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  useEffect(() => {
    run(async () => {
      const list = await api.listNetworks();
      setNetworks(list);
      if (list.length > 0) setNetworkId(list[list.length - 1].network_id);
    });
  }, [run]);

  useEffect(() => {
    setSelection(null);
    run(() => refreshTopology(networkId));
  }, [networkId, refreshTopology, run]);

  // Simulation history is kept on the server, so it is reloaded whenever a network is opened.
  useEffect(() => {
    let cancelled = false;
    setSimulations([]);
    setSelectedSimId(null);
    if (!networkId) return undefined;
    run(async () => {
      const list = await api.listSimulations(networkId);
      if (cancelled) return;
      setSimulations(list);
      setSelectedSimId(list[0]?.simulation_id ?? null); // newest first
    });
    return () => { cancelled = true; };
  }, [networkId, run]);

  const refreshChaos = useCallback(async (id) => {
    const [active, history] = await Promise.all([api.getActiveChaos(id), api.getChaosHistory(id)]);
    setChaosActive(active.active_experiments);
    setChaosHistory(history.experiments);
  }, []);

  // Chaos state lives on the server too, so it is reloaded whenever a network is opened.
  useEffect(() => {
    let cancelled = false;
    setChaosActive([]);
    setChaosHistory([]);
    if (!networkId) return undefined;
    run(async () => {
      const [active, history] = await Promise.all([api.getActiveChaos(networkId), api.getChaosHistory(networkId)]);
      if (cancelled) return;
      setChaosActive(active.active_experiments);
      setChaosHistory(history.experiments);
    });
    return () => { cancelled = true; };
  }, [networkId, run]);

  const selectedSim = simulations.find((s) => s.simulation_id === selectedSimId) ?? null;
  const selectedStatus = selectedSim?.status;

  // Full metrics come from the metrics endpoint once a simulation has finished.
  useEffect(() => {
    let cancelled = false;
    setMetrics(null);
    if (networkId && selectedSimId && (selectedStatus === "completed" || selectedStatus === "failed")) {
      api.getMetrics(networkId, selectedSimId).then((m) => !cancelled && setMetrics(m)).catch(() => {});
    }
    return () => { cancelled = true; };
  }, [networkId, selectedSimId, selectedStatus]);

  const createSimulation = (params) =>
    run(async () => {
      const created = await api.createSimulation(networkId, params);
      setSimulations((prev) => [created, ...prev]);
      setSelectedSimId(created.simulation_id);
    });

  const runSimulation = () =>
    run(async () => {
      const done = await api.runSimulation(networkId, selectedSimId);
      setSimulations((prev) => prev.map((s) => (s.simulation_id === done.simulation_id ? done : s)));
    });

  const createNetwork = (name) =>
    run(async () => {
      const created = await api.createNetwork(name);
      const list = await api.listNetworks();
      // set together (no await between) so React renders the new list and selection in one pass
      setNetworks(list);
      setNetworkId(created.network_id);
    });

  const mutate = (action) =>
    run(async () => {
      await action();
      await refreshTopology(networkId);
    });

  // Chaos edits the real topology, so both the topology and the chaos lists are reloaded afterwards.
  const chaosAction = (action) =>
    run(async () => {
      await action();
      await Promise.all([refreshTopology(networkId), refreshChaos(networkId)]);
    });

  const hasNetwork = Boolean(networkId);
  // While a newly selected network is loading, don't show (or act on) the previous network's data.
  const loading = hasNetwork && loadedTopology.network_id !== networkId;
  const topology = loading ? EMPTY_TOPOLOGY : loadedTopology;
  const { summary } = topology;

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>NetChaos <small>Topology · Traffic · Chaos</small></h1>
        <NetworkPanel networks={networks} networkId={networkId} onSelect={setNetworkId} onCreate={createNetwork} />
        <NodeForm disabled={!hasNetwork} onAdd={(node) => mutate(() => api.addNode(networkId, node))} />
        <LinkForm nodes={topology.nodes} disabled={!hasNetwork} onAdd={(link) => mutate(() => api.addLink(networkId, link))} />
        <TemplatePanel
          disabled={!hasNetwork || loading}
          isEmpty={summary.nodes === 0}
          onApply={(template) => mutate(() => api.applyTemplate(networkId, template))}
        />
        <TrafficPanel
          nodes={topology.nodes}
          disabled={!hasNetwork || loading}
          selectedSim={selectedSim}
          onCreate={createSimulation}
          onRun={runSimulation}
        />
        <ChaosPanel
          nodes={topology.nodes}
          links={topology.links}
          disabled={!hasNetwork || loading}
          onInject={(kind, body) => chaosAction(() => api.injectChaos(networkId, kind, body))}
        />
        <ActiveChaosPanel
          active={chaosActive}
          disabled={!hasNetwork || loading}
          onRevert={(id) => chaosAction(() => api.revertChaos(networkId, id))}
          onReset={() => chaosAction(() => api.resetChaos(networkId))}
        />
        <DetailsPanel
          selection={selection}
          topology={topology}
          onDeleteNode={(node) => mutate(() => api.deleteNode(networkId, node.id)).then(() => setSelection(null))}
          onDeleteLink={(link) => mutate(() => api.deleteLink(networkId, link.id)).then(() => setSelection(null))}
        />
      </aside>

      <main className="main">
        {error && (
          <div className="error" role="alert">
            {error}
            <button type="button" onClick={() => setError(null)} aria-label="Dismiss">×</button>
          </div>
        )}
        <div className="canvas">
          {hasNetwork ? (
            <TopologyCanvas
              topology={topology} selection={selection} onSelect={setSelection} resetKey={networkId}
              route={selectedSim?.route ?? null} chaos={chaosActive}
            />
          ) : (
            <p className="empty">Create a network to get started.</p>
          )}
          {hasNetwork && !loading && summary.nodes === 0 && <p className="empty">Add nodes or generate a template.</p>}
        </div>
        {hasNetwork && (
          <TrafficResults
            simulations={simulations}
            selectedId={selectedSimId}
            metrics={metrics}
            nameOf={(id) => topology.nodes.find((n) => n.id === id)?.name ?? id}
            onSelect={setSelectedSimId}
          >
            <ChaosHistory history={chaosHistory} />
            <Failures networkId={networkId} />
            <RecoveryPanel 
              networkId={networkId} 
              simulations={simulations} 
              selectedSimId={selectedSimId} 
              nameOf={(id) => topology.nodes.find((n) => n.id === id)?.name ?? id}
              onRecovered={() => {
                // Refresh simulations and topology
                api.listSimulations(networkId).then(list => setSimulations(list));
                run(() => refreshTopology(networkId));
              }}
            />
          </TrafficResults>
        )}
        <footer className="stats">
          <span>Nodes: <b>{summary.nodes}</b></span>
          <span>Links: <b>{summary.links}</b></span>
          <span>Active Nodes: <b>{summary.active_nodes}</b></span>
          <span>Active Links: <b>{summary.active_links}</b></span>
        </footer>
      </main>
    </div>
  );
}
