import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { ActiveChaosPanel, ChaosHistory, ChaosPanel } from "./components/Chaos.jsx";
import { DetailsPanel, LinkForm, NetworkPanel, NodeForm, TemplatePanel } from "./components/Panels.jsx";
import TopologyCanvas from "./components/TopologyCanvas.jsx";
import { TrafficPanel, TrafficResults } from "./components/Traffic.jsx";
import Failures from "./components/Failures.jsx";
import RecoveryPanel from "./components/Recovery.jsx";
import { MonitoringDashboard } from "./components/Monitoring.jsx";
import { HistoryDashboard } from "./components/History.jsx";
import { DashboardOverview } from "./components/DashboardOverview.jsx";

const EMPTY_TOPOLOGY = { nodes: [], links: [], summary: { nodes: 0, links: 0, active_nodes: 0, active_links: 0 } };

const TABS = ["Dashboard", "Topology", "Traffic", "Chaos", "Failures", "Recovery", "Monitoring", "History"];

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
  
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [networkStatus, setNetworkStatus] = useState("UNKNOWN");

  const refreshTopology = useCallback(async (id) => {
    setLoadedTopology(id ? await api.getTopology(id) : EMPTY_TOPOLOGY);
  }, []);

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
      if (list.length > 0) {
        setNetworkId(list[list.length - 1].network_id);
      } else {
        setActiveTab("Topology"); // Force topology tab if empty to allow creation
      }
    });
  }, [run]);

  useEffect(() => {
    setSelection(null);
    run(() => refreshTopology(networkId));
    if (networkId) {
       // Fetch top level status 
       api.getMonitoringCurrent(networkId).then(data => setNetworkStatus(data.health_status)).catch(() => setNetworkStatus("UNKNOWN"));
    } else {
       setNetworkStatus("UNKNOWN");
    }
  }, [networkId, refreshTopology, run]);

  // Simulations polling
  useEffect(() => {
    let cancelled = false;
    setSimulations([]);
    setSelectedSimId(null);
    if (!networkId) return;
    run(async () => {
      const list = await api.listSimulations(networkId);
      if (cancelled) return;
      setSimulations(list);
      setSelectedSimId(list[0]?.simulation_id ?? null);
    });
    return () => { cancelled = true; };
  }, [networkId, run]);

  // Chaos details
  const refreshChaos = useCallback(async (id) => {
    const [active, history] = await Promise.all([api.getActiveChaos(id), api.getChaosHistory(id)]);
    setChaosActive(active.active_experiments);
    setChaosHistory(history.experiments);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setChaosActive([]);
    setChaosHistory([]);
    if (!networkId) return;
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
      setNetworks(list);
      setNetworkId(created.network_id);
      setActiveTab("Topology");
    });

  const mutate = (action) =>
    run(async () => {
      await action();
      await refreshTopology(networkId);
    });

  const chaosAction = (action) =>
    run(async () => {
      await action();
      await Promise.all([refreshTopology(networkId), refreshChaos(networkId)]);
    });

  // Derived state
  const hasNetwork = Boolean(networkId);
  const loading = hasNetwork && loadedTopology.network_id !== networkId;
  const topology = loading ? EMPTY_TOPOLOGY : loadedTopology;
  const { summary } = topology;
  
  const showTopologyCanvas = ["Topology", "Traffic", "Chaos", "Failures", "Recovery"].includes(activeTab);

  return (
    <div className="app-layout">
      {/* GLOBAL HEADER */}
      <header className="app-header">
        <div>
          <b style={{marginRight: '20px', fontSize: '1.2rem'}}>NetChaos</b>
          <label>Network:
            <select 
              value={networkId || ""} 
              onChange={e => setNetworkId(e.target.value)}
              style={{marginRight: '10px'}}
            >
              {networks.map(n => <option key={n.network_id} value={n.network_id}>{n.name}</option>)}
            </select>
          </label>
        </div>
        <div style={{display:'flex', gap: '20px', alignItems: 'center'}}>
           {hasNetwork && (
             <>
               <span>Nodes: {summary.nodes}</span>
               <span>Links: {summary.links}</span>
               <span className={`status-${networkStatus.toLowerCase()}`}>Status: {networkStatus}</span>
             </>
           )}
        </div>
      </header>
      
      {/* DASHBOARD BODY */}
      <div className="app-body">
        {/* SIDEBAR NAVIGATION */}
        <aside className="app-sidebar">
          {TABS.map(tab => (
            <button 
              key={tab} 
              className={`nav-tab ${activeTab === tab ? "active" : ""}`}
              onClick={() => setActiveTab(tab)}
              disabled={!hasNetwork && tab !== 'Topology'}
            >
              {tab}
            </button>
          ))}
        </aside>
        
        {/* MAIN DISPLAY */}
        <main className="app-content">
          {error && (
            <div className="error" role="alert" style={{position:'absolute', zIndex: 1000, width: '100%', top:0}}>
              {error}
              <button type="button" onClick={() => setError(null)} aria-label="Dismiss">×</button>
            </div>
          )}
          
          {activeTab === "Dashboard" && hasNetwork && (
             <DashboardOverview networkId={networkId} topology={topology} chaosActive={chaosActive} simulations={simulations} />
          )}
          
          {activeTab === "Monitoring" && hasNetwork && (
             <MonitoringDashboard networkId={networkId} inline={true} />
          )}
          
          {activeTab === "History" && hasNetwork && (
             <HistoryDashboard networkId={networkId} inline={true} />
          )}
          
          {showTopologyCanvas && (
             <div className="content-panel-wrapper">
               {/* Contextual Side Panel based on Tab */}
               <aside className="side-panel sidebar">
                 {activeTab === "Topology" && (
                   <>
                     <NetworkPanel networks={networks} networkId={networkId} onSelect={setNetworkId} onCreate={createNetwork} />
                     <NodeForm disabled={!hasNetwork} onAdd={(node) => mutate(() => api.addNode(networkId, node))} />
                     <LinkForm nodes={topology.nodes} disabled={!hasNetwork} onAdd={(link) => mutate(() => api.addLink(networkId, link))} />
                     <TemplatePanel disabled={!hasNetwork || loading} isEmpty={summary.nodes === 0} onApply={(template) => mutate(() => api.applyTemplate(networkId, template))} />
                     <DetailsPanel selection={selection} topology={topology} onDeleteNode={(node) => mutate(() => api.deleteNode(networkId, node.id)).then(() => setSelection(null))} onDeleteLink={(link) => mutate(() => api.deleteLink(networkId, link.id)).then(() => setSelection(null))} />
                   </>
                 )}
                 
                 {activeTab === "Traffic" && (
                   <>
                     <TrafficPanel nodes={topology.nodes} disabled={!hasNetwork || loading} selectedSim={selectedSim} onCreate={createSimulation} onRun={runSimulation} />
                     {hasNetwork && (
                       <TrafficResults simulations={simulations} selectedId={selectedSimId} metrics={metrics} nameOf={(id) => topology.nodes.find((n) => n.id === id)?.name ?? id} onSelect={setSelectedSimId} />
                     )}
                   </>
                 )}
                 
                 {activeTab === "Chaos" && (
                   <>
                     <ChaosPanel nodes={topology.nodes} links={topology.links} disabled={!hasNetwork || loading} onInject={(kind, body) => chaosAction(() => api.injectChaos(networkId, kind, body))} />
                     <ActiveChaosPanel active={chaosActive} disabled={!hasNetwork || loading} onRevert={(id) => chaosAction(() => api.revertChaos(networkId, id))} onReset={() => chaosAction(() => api.resetChaos(networkId))} />
                     <ChaosHistory history={chaosHistory} />
                   </>
                 )}
                 
                 {activeTab === "Failures" && (
                    <Failures networkId={networkId} />
                 )}
                 
                 {activeTab === "Recovery" && (
                    <RecoveryPanel 
                      networkId={networkId} 
                      simulations={simulations} 
                      selectedSimId={selectedSimId} 
                      nameOf={(id) => topology.nodes.find((n) => n.id === id)?.name ?? id}
                      onRecovered={() => {
                        api.listSimulations(networkId).then(list => setSimulations(list));
                        run(() => refreshTopology(networkId));
                        api.getMonitoringCurrent(networkId).then(data => setNetworkStatus(data.health_status));
                      }}
                    />
                 )}
               </aside>
               
               {/* Topology Canvas rendered next to the Contextual panels */}
               <div className="canvas">
                 {hasNetwork ? (
                   <TopologyCanvas
                     topology={topology} selection={selection} onSelect={setSelection} resetKey={`${networkId}-${activeTab}`}
                     route={selectedSim?.route ?? null} chaos={chaosActive}
                   />
                 ) : (
                   <p className="empty">Create a network to get started.</p>
                 )}
                 {hasNetwork && !loading && summary.nodes === 0 && <p className="empty">Add nodes or generate a template.</p>}
               </div>
             </div>
          )}
        </main>
      </div>
    </div>
  );
}
