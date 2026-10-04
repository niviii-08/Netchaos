import React, { useState, useEffect } from "react";
import { api } from "../api";

export function ExperimentLab({ networkId }) {
  const [plans, setPlans] = useState([]);
  const [activeTab, setActiveTab] = useState("builder");
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [results, setResults] = useState(null);
  
  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [repetitions, setRepetitions] = useState(1);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [packetCount, setPacketCount] = useState(100);
  const [packetSize, setPacketSize] = useState(1024);
  const [chaosType, setChaosType] = useState("link_failure");
  const [chaosTarget, setChaosTarget] = useState("");
  const [isSweep, setIsSweep] = useState(false);
  const [sweepParam, setSweepParam] = useState("loss_percentage");
  const [sweepValuesStr, setSweepValuesStr] = useState("1,5,10,20");
  const [recoveryEnabled, setRecoveryEnabled] = useState(true);
  
  // Data State
  const [nodes, setNodes] = useState([]);
  const [links, setLinks] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pollingId, setPollingId] = useState(null);

  useEffect(() => {
    if (networkId) {
      api.getTopology(networkId).then((data) => {
        setNodes(data.nodes || []);
        setLinks(data.links || []);
      });
      loadPlans();
    }
  }, [networkId]);

  useEffect(() => {
    if (selectedPlan && selectedPlan.status === "RUNNING") {
      const p = setInterval(() => reloadPlanStatus(selectedPlan.plan_id), 2000);
      setPollingId(p);
      return () => clearInterval(p);
    }
  }, [selectedPlan]);

  const loadPlans = async () => {
    try {
        // Mock get/list endpoint if it isn't listed in runner, or use custom polling logic
        // We'll trust create and single fetching for now.
    } catch (e) {
        console.error(e);
    }
  };

  const reloadPlanStatus = async (planId) => {
    try {
       const res = await api.getExperimentPlan(planId);
       setSelectedPlan(res);
       
       if (["COMPLETED", "FAILED", "PARTIAL", "CANCELLED"].includes(res.status)) {
           fetchResults(planId);
       }
    } catch(e) {
       console.error("Failed to poll plan status:", e);
    }
  };
  
  const fetchResults = async (planId) => {
      try {
          const res = await api.getExperimentPlanResults(planId);
          setResults(res);
      } catch (err) {
          console.error("Failed to fetch plan results:", err);
      }
  };

  const startExperiment = async () => {
    setError(null);
    setLoading(true);
    let sweepObj = null;
    let expectedRuns = repetitions;
    
    if (isSweep) {
        let vals = sweepValuesStr.split(",").map(v => parseFloat(v.trim()));
        sweepObj = {
            parameter: sweepParam,
            values: vals
        };
        expectedRuns *= vals.length;
    }
    
    if (expectedRuns > 100) {
        setError("Cannot exceed 100 maximum runs per batch.");
        setLoading(false);
        return;
    }
    
    try {
        const payload = {
            name: name || "Automated Experiment",
            description,
            network_id: networkId,
            traffic: {
                source,
                destination: target,
                packet_count: parseInt(packetCount),
                packet_size: parseInt(packetSize),
                protocol: "TCP"
            },
            chaos: {
                type: chaosType,
                target: chaosTarget,
                parameters: {
                    loss_percentage: chaosType === 'packet_loss' ? 10 : undefined,
                    additional_latency_ms: chaosType === 'latency' ? 50 : undefined,
                    reduction_percentage: chaosType === 'bandwidth_reduction' ? 50 : undefined,
                }
            },
            recovery: {
                enabled: recoveryEnabled,
                strategy: "shortest_hop"
            },
            repetitions: parseInt(repetitions),
            sweep: sweepObj
        };
        
        const plan = await api.createExperimentPlan(payload);
        
        // Start run natively!
        await api.runExperimentPlan(plan.plan_id);
        
        setSelectedPlan(plan);
        setActiveTab("active");
        
        // Wait 1s and refresh
        setTimeout(() => reloadPlanStatus(plan.plan_id), 1000);
        
    } catch (err) {
        setError(err.message || "Failed to create experiment from configuration");
    } finally {
        setLoading(false);
    }
  };

  const cancelExperiment = async () => {
      if (!selectedPlan) return;
      try {
          await api.cancelExperimentPlan(selectedPlan.plan_id);
          reloadPlanStatus(selectedPlan.plan_id);
      } catch(e) {
          setError(e.message);
      }
  };

  if (!networkId) return <div className="p-4 text-center text-gray-500">Pick a network to use the Experiment Lab.</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto font-sans">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
          Experiment Lab
        </h2>
        <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
          <button 
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${activeTab === 'builder' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setActiveTab('builder')}
          >
            Builder
          </button>
          <button 
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${activeTab === 'active' ? 'bg-white shadow text-indigo-600' : 'text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setActiveTab('active')}
            disabled={!selectedPlan}
          >
            Active Run
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 rounded shadow-sm">
            <p className="font-bold">Error</p>
            <p>{error}</p>
        </div>
      )}

      {activeTab === "builder" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-100 font-semibold text-gray-700 uppercase tracking-wide text-sm">
                Configuration
            </div>
            <div className="p-6 space-y-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Experiment Name</label>
                    <input className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500" type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Failure Sensitivity Analysis" />
                </div>
                
                <div className="bg-blue-50/50 p-4 rounded-lg space-y-4 border border-blue-100">
                    <h3 className="text-sm font-bold text-blue-800 uppercase">Traffic Baseline</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-blue-700">Source Node</label>
                            <select className="w-full text-sm rounded mt-1 border-blue-200 focus:ring-blue-500" value={source} onChange={e => setSource(e.target.value)}>
                                <option value="">Select...</option>
                                {nodes.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-blue-700">Destination Node</label>
                            <select className="w-full text-sm rounded mt-1 border-blue-200 focus:ring-blue-500" value={target} onChange={e => setTarget(e.target.value)}>
                                <option value="">Select...</option>
                                {nodes.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
                            </select>
                        </div>
                    </div>
                </div>

                <div className="bg-red-50/50 p-4 rounded-lg space-y-4 border border-red-100">
                    <h3 className="text-sm font-bold text-red-800 uppercase">Chaos Settings</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-red-700">Failure Type</label>
                            <select className="w-full text-sm rounded mt-1 border-red-200 focus:ring-red-500" value={chaosType} onChange={e => setChaosType(e.target.value)}>
                                <option value="link_failure">Link Failure</option>
                                <option value="router_failure">Router Failure</option>
                                <option value="packet_loss">Packet Loss</option>
                                <option value="latency">Latency Increase</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-red-700">Target Element</label>
                            <select className="w-full text-sm rounded mt-1 border-red-200 focus:ring-red-500" value={chaosTarget} onChange={e => setChaosTarget(e.target.value)}>
                                <option value="">Select Target...</option>
                                {chaosType.includes("link") || chaosType.includes("packet") || chaosType.includes("latency") ? 
                                    links.map(l => <option key={l.id} value={l.id}>Link {l.source_node_id} ➔ {l.destination_node_id}</option>) :
                                    nodes.map(n => <option key={n.id} value={n.id}>Node {n.name}</option>)
                                }
                            </select>
                        </div>
                    </div>
                </div>

                <div className="bg-purple-50/50 p-4 rounded-lg space-y-4 border border-purple-100">
                    <h3 className="text-sm font-bold text-purple-800 uppercase">Testing Strategy</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-purple-700">Repetitions Per Run</label>
                            <input type="number" min="1" max="10" className="w-full text-sm rounded mt-1 border-purple-200 focus:ring-purple-500" value={repetitions} onChange={e => setRepetitions(e.target.value)} />
                        </div>
                        <div className="flex items-center pt-5">
                            <label className="flex items-center space-x-2 text-sm text-purple-800 cursor-pointer">
                                <input type="checkbox" className="rounded text-purple-600 focus:ring-purple-500" checked={recoveryEnabled} onChange={e => setRecoveryEnabled(e.target.checked)} />
                                <span>Dynamic Recovery</span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <div className="bg-yellow-50/50 p-4 rounded-lg space-y-4 border border-yellow-100">
                    <div className="flex justify-between items-center mb-2">
                         <h3 className="text-sm font-bold text-yellow-800 uppercase">Parameter Sweep</h3>
                         <label className="flex items-center cursor-pointer">
                            <div className="relative">
                                <input type="checkbox" className="sr-only" checked={isSweep} onChange={e => setIsSweep(e.target.checked)} />
                                <div className={`block w-10 h-6 rounded-full transition ${isSweep ? 'bg-yellow-400' : 'bg-gray-300'}`}></div>
                                <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition transform ${isSweep ? 'translate-x-4' : ''}`}></div>
                            </div>
                        </label>
                    </div>
                    {isSweep && (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-yellow-700">Parameter</label>
                                <select className="w-full text-sm rounded mt-1 border-yellow-200 focus:ring-yellow-500" value={sweepParam} onChange={e => setSweepParam(e.target.value)}>
                                    <option value="packet_count">Traffic: Packet Count</option>
                                    <option value="packet_size">Traffic: Packet Size</option>
                                    <option value="loss_percentage">Chaos: Packet Loss (%)</option>
                                    <option value="additional_latency_ms">Chaos: Latency (ms)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-yellow-700">Sweep Values (comma-separated)</label>
                                <input type="text" className="w-full text-sm rounded mt-1 border-yellow-200 focus:ring-yellow-500" value={sweepValuesStr} onChange={e => setSweepValuesStr(e.target.value)} placeholder="e.g. 10,20,50,100" />
                            </div>
                        </div>
                    )}
                </div>

                <button 
                  onClick={startExperiment} 
                  disabled={loading || !source || !target || !chaosTarget}
                  className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-lg shadow-md transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-lg"
                >
                  {loading ? "Initializing..." : `Launch ${isSweep ? sweepValuesStr.split(",").length * repetitions : repetitions} Simulations 🚀`}
                </button>
            </div>
          </div>
          
          <div className="space-y-6">
              <div className="bg-gradient-to-br from-indigo-900 to-blue-900 rounded-xl p-8 text-white shadow-xl">
                  <h3 className="text-xl font-bold mb-4 flex items-center">What is Experiment Lab? 🔬</h3>
                  <p className="text-blue-100 mb-4 leading-relaxed">
                      Experiment Lab combines Modules 1 through 10 into an automated, deterministic runner.
                  </p>
                  <ul className="space-y-2 text-sm text-blue-200">
                      <li className="flex items-center"><span className="mr-2">⚡</span> Validates state between runs</li>
                      <li className="flex items-center"><span className="mr-2">⚡</span> Automatically captures and reverts chaos</li>
                      <li className="flex items-center"><span className="mr-2">⚡</span> Stores historical runs for Module 10 analysis</li>
                      <li className="flex items-center"><span className="mr-2">⚡</span> Safely supports massive parameter sweeps</li>
                  </ul>
              </div>

               <div className="bg-white rounded-xl shadow p-6 border border-gray-100">
                 <h3 className="font-bold text-gray-800 mb-2">Pre-Flight Checklist</h3>
                 <div className="space-y-2 text-sm">
                     <div className={`p-2 rounded ${source && target ? 'bg-green-50 text-green-700 flex' : 'bg-gray-50 text-gray-500 flex'}`}>
                         <span className="mr-2">{source && target ? '✓' : '○'}</span> Flow configured
                     </div>
                     <div className={`p-2 rounded ${chaosTarget ? 'bg-green-50 text-green-700 flex' : 'bg-gray-50 text-gray-500 flex'}`}>
                         <span className="mr-2">{chaosTarget ? '✓' : '○'}</span> Chaos targeted
                     </div>
                     <div className={`p-2 rounded ${(!isSweep || (sweepValuesStr.length && sweepValuesStr.split(',').length > 0)) ? 'bg-green-50 text-green-700 flex' : 'bg-yellow-50 text-yellow-700 flex'}`}>
                         <span className="mr-2">{!isSweep ? '✓' : (sweepValuesStr.length ? '✓' : '!')}</span> Safe parameter bounds
                     </div>
                 </div>
               </div>
          </div>
        </div>
      )}

      {activeTab === "active" && selectedPlan && (
        <div className="space-y-6">
           <div className="bg-white rounded-xl shadow border border-gray-200 overflow-hidden">
               <div className="p-6">
                   <div className="flex justify-between items-center mb-4">
                       <h3 className="text-2xl font-bold text-gray-800">{selectedPlan.name}</h3>
                       <div className={`px-4 py-1 rounded-full text-sm font-bold uppercase tracking-wide
                           ${selectedPlan.status === 'RUNNING' ? 'bg-blue-100 text-blue-800 animate-pulse' : 
                             selectedPlan.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : 
                             selectedPlan.status === 'CANCELLED' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                           {selectedPlan.status}
                       </div>
                   </div>
                   
                   <div className="mb-8">
                       <div className="flex justify-between text-sm font-medium text-gray-600 mb-2">
                           <span>Progress ({selectedPlan.completed_runs} / {selectedPlan.total_runs})</span>
                           <span>{Math.round(selectedPlan.progress_percentage || 0)}%</span>
                       </div>
                       <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                           <div className="bg-gradient-to-r from-blue-500 to-indigo-600 h-4 rounded-full transition-all duration-500 ease-in-out" 
                                style={{width: `${Math.max(1, selectedPlan.progress_percentage || 0)}%`}}></div>
                       </div>
                   </div>

                   {selectedPlan.status === 'RUNNING' && (
                       <button onClick={cancelExperiment} className="bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 px-6 py-2 rounded-lg font-medium transition-colors">
                           Cancel Execution
                       </button>
                   )}
               </div>
           </div>

           {results && (
              <div className="bg-white rounded-xl shadow border border-gray-200 p-6">
                  <div className="flex justify-between items-center mb-6">
                      <h3 className="text-xl font-bold text-gray-800">Batch Results</h3>
                      <div className="flex gap-2">
                          <a 
                              href={`/api/experiment-plans/${selectedPlan.plan_id}/export/csv`}
                              download
                              className="px-4 py-2 text-sm font-semibold border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
                          >
                              ⬇ CSV
                          </a>
                          <a 
                              href={`/api/experiment-plans/${selectedPlan.plan_id}/export/json`}
                              download
                              className="px-4 py-2 text-sm font-semibold border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
                          >
                              ⬇ JSON
                          </a>
                      </div>
                  </div>
                  
                  <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                              <tr>
                                  <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Run</th>
                                  <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Scenario</th>
                                  <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Resilience Score</th>
                                  <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Recovery Success</th>
                              </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                              {results.results.map((r, i) => (
                                  <tr key={r.run_id} className="hover:bg-gray-50">
                                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Run {i + 1}</td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                          {r.scenario.sweep_parameter ? `${r.scenario.sweep_parameter}: ${r.scenario.sweep_value}` : `Rep ${r.scenario.repetition}`}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                          <div className="flex items-center gap-2">
                                              <div className="w-16 h-2 bg-gray-200 rounded overflow-hidden">
                                                  <div className="h-full bg-blue-500" style={{ width: `${r.analytics.resilience_score * 100}%`}}></div>
                                              </div>
                                              <span>{r.analytics.resilience_score.toFixed(2)}</span>
                                          </div>
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap">
                                          {r.analytics.recovery_effectiveness > 0 ? (
                                              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">Recovered</span>
                                          ) : (
                                              <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">Failed</span>
                                          )}
                                      </td>
                                  </tr>
                              ))}
                          </tbody>
                      </table>
                  </div>
              </div>
           )}
           
           <div className="bg-white rounded-xl shadow border border-gray-200 p-6 overflow-hidden">
             <h3 className="text-xl font-bold text-gray-800 mb-4">Run Log</h3>
             <div className="space-y-3">
                 {selectedPlan.runs.map((r) => (
                     <div key={r.run_id} className="p-3 bg-gray-50 rounded border border-gray-100 flex items-center justify-between">
                         <div className="flex items-center">
                             <div className={`w-3 h-3 rounded-full mr-3
                                 ${r.status === 'COMPLETED' ? 'bg-green-500' : 
                                   r.status === 'FAILED' ? 'bg-red-500' : 
                                   r.status === 'RUNNING' ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'}`}>
                             </div>
                             <span className="font-medium text-sm text-gray-700">Run {r.run_number}</span>
                             <span className="ml-4 text-xs text-gray-500">
                                 {r.configuration.sweep_parameter && `${r.configuration.sweep_parameter}=${r.configuration.sweep_value} | `} 
                                 Repetition {r.configuration.repetition}
                             </span>
                         </div>
                         <div className="text-xs font-bold text-gray-500 uppercase">{r.status}</div>
                         {r.error && <p className="text-xs text-red-500 w-full col-span-full mt-2 pl-6">{r.error}</p>}
                     </div>
                 ))}
             </div>
           </div>
        </div>
      )}
    </div>
  );
}
