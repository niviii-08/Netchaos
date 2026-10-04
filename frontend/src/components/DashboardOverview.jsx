import React, { useState, useEffect } from 'react';
import { api } from '../api';

export function DashboardOverview({ networkId, topology, chaosActive, simulations }) {
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  
  useEffect(() => {
    if (networkId) {
      api.getMonitoringCurrent(networkId).then(setCurrent).catch(() => {});
      api.getHistory(networkId).then(list => setHistory(list)).catch(() => {});
    }
  }, [networkId]);

  if (!networkId) return <div className="empty">Select or create a network to view dashboard</div>;
  
  return (
    <div className="dashboard-overview">
      <div className="monitoring-header">
        <h2>NETCHAOS <small>Network Resilience Simulator</small></h2>
      </div>
      
      <div className="monitoring-dashboard-grid" style={{marginTop: '20px'}}>
        <div className="monitoring-card">
          <h3>Network Status</h3>
          {current ? (
            <>
              <h1 className={`status-${current.health_status.toLowerCase()}`}>{current.health_status}</h1>
              <div className="stats-row">
                 <span>Nodes: {current.nodes.active}/{current.nodes.total}</span>
                 <span>Links: {current.links.active}/{current.links.total}</span>
                 <span>Traffic Flows: {current.traffic.affected_flows === 0 ? "Normal" : `${current.traffic.affected_flows} Affected`}</span>
                 <span>Failures: {current.nodes.failed + current.links.failed}</span>
              </div>
            </>
          ) : <p>Loading state...</p>}
        </div>

        <div className="monitoring-card">
          <h3>Performance</h3>
          {current ? (
            <div className="stats-row">
               <span>Latency: <b>{current.traffic.average_latency} ms</b></span>
               <span>Packet Loss: <b>{current.traffic.packet_loss_percentage}%</b></span>
               <span>Throughput: <b>{current.traffic.throughput} Mbps</b></span>
               <span>Availability: <b>{current.connectivity.traffic_availability}%</b></span>
            </div>
          ) : <p>Waiting for telemetry...</p>}
        </div>

        <div className="monitoring-card">
          <h3>Recent Events</h3>
          <div className="events-list">
             {history.slice(0, 5).map(e => (
               <div key={e.id}>
                 <small style={{color: '#888'}}>{new Date(e.started_at).toLocaleTimeString()}</small>
                 <div>{e.name} ({e.status})</div>
               </div>
             ))}
             {history.length === 0 && <p>No events recorded.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
