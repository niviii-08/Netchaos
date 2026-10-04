import React, { useState, useEffect } from 'react';

export default function DatasetLab() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [version, setVersion] = useState('1.0');
  const [failureFilter, setFailureFilter] = useState('');

  const fetchDatasets = async () => {
    try {
      const res = await fetch('/api/datasets');
      const data = await res.json();
      setDatasets(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setGenerating(true);
    let filters = {};
    if (failureFilter) {
      filters.failure_types = [failureFilter];
    }
    try {
      const res = await fetch('/api/datasets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description,
          version,
          filters: Object.keys(filters).length ? filters : null
        })
      });
      if (res.ok) {
        await fetchDatasets();
        setName('');
        setDescription('');
        setFailureFilter('');
      } else {
        alert("Generation failed");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectDataset = async (dataset_id) => {
    try {
      const res = await fetch(`/api/datasets/${dataset_id}`);
      const data = await res.json();
      setSelectedDataset(data.metadata);
      setRecords(data.records);

      const statsRes = await fetch(`/api/datasets/${dataset_id}/statistics`);
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Research Dataset Lab</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        
        {/* Generator Form */}
        <div className="col-span-1 bg-white p-6 rounded-xl shadow border border-gray-200">
          <h3 className="text-lg font-bold mb-4">Generate Dataset</h3>
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Name</label>
              <input type="text" required value={name} onChange={e=>setName(e.target.value)} className="w-full p-2 border rounded" placeholder="e.g. Resilience Baseline v1" />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Description</label>
              <input type="text" value={description} onChange={e=>setDescription(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Version</label>
              <input type="text" required value={version} onChange={e=>setVersion(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Filter by Failure Type</label>
              <select value={failureFilter} onChange={e=>setFailureFilter(e.target.value)} className="w-full p-2 border rounded">
                <option value="">(All)</option>
                <option value="link_failure">Link Failure</option>
                <option value="router_failure">Router Failure</option>
                <option value="packet_loss">Packet Loss</option>
              </select>
            </div>
            <button type="submit" disabled={generating} className="w-full bg-blue-600 text-white font-bold py-2 rounded mt-4 hover:bg-blue-700 disabled:opacity-50">
              {generating ? "Generating..." : "Generate Dataset"}
            </button>
          </form>
        </div>
        
        {/* Dataset List */}
        <div className="col-span-2 bg-white p-6 rounded-xl shadow border border-gray-200">
          <h3 className="text-lg font-bold mb-4">Available Datasets</h3>
          {loading ? (
             <p>Loading...</p>
          ) : datasets.length === 0 ? (
             <p className="text-gray-500">No datasets generated yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Dataset ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Records</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {datasets.map(ds => (
                    <tr key={ds.dataset_id} className={selectedDataset?.dataset_id === ds.dataset_id ? 'bg-blue-50' : ''}>
                      <td className="px-4 py-2 text-sm text-gray-900 font-mono">{ds.dataset_id}</td>
                      <td className="px-4 py-2 text-sm font-semibold">{ds.name} v{ds.version}</td>
                      <td className="px-4 py-2 text-sm">{ds.record_count}</td>
                      <td className="px-4 py-2 text-sm">
                         <button onClick={() => handleSelectDataset(ds.dataset_id)} className="text-blue-600 font-bold text-sm hover:underline">View</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      
      {/* Detail View */}
      {selectedDataset && (
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold">Dataset: {selectedDataset.name} (v{selectedDataset.version})</h3>
            <div className="flex gap-2">
              <a href={`/api/datasets/${selectedDataset.dataset_id}/export/csv`} download className="px-4 py-2 border rounded-lg text-sm font-semibold hover:bg-gray-50">⬇ Export CSV</a>
              <a href={`/api/datasets/${selectedDataset.dataset_id}/export/json`} download className="px-4 py-2 border rounded-lg text-sm font-semibold hover:bg-gray-50">⬇ Export JSON</a>
            </div>
          </div>
          
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                <p className="text-xs text-gray-500 uppercase font-bold">Total Records</p>
                <p className="text-2xl font-black text-gray-800">{stats.total_records}</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg border border-green-100">
                <p className="text-xs text-green-600 uppercase font-bold">Valid Records</p>
                <p className="text-2xl font-black text-green-800">{stats.data_quality_report.VALID || 0}</p>
              </div>
              <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100">
                <p className="text-xs text-yellow-600 uppercase font-bold">Partial Records</p>
                <p className="text-2xl font-black text-yellow-800">{stats.data_quality_report.PARTIAL || 0}</p>
              </div>
              <div className="bg-red-50 p-4 rounded-lg border border-red-100">
                <p className="text-xs text-red-600 uppercase font-bold">Invalid Records</p>
                <p className="text-2xl font-black text-red-800">{stats.data_quality_report.INVALID || 0}</p>
              </div>
            </div>
          )}
          
          <h4 className="font-bold text-gray-700 mb-2">Preview (first 20 records)</h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-2 py-1 text-left">Quality</th>
                  <th className="px-2 py-1 text-left">Experiment ID</th>
                  <th className="px-2 py-1 text-left">Chaos</th>
                  <th className="px-2 py-1 text-left">Outcome</th>
                  <th className="px-2 py-1 text-left">Impact</th>
                  <th className="px-2 py-1 text-left">Resilience</th>
                  <th className="px-2 py-1 text-left">Rec. Time</th>
                  <th className="px-2 py-1 text-left">Warnings</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {records.slice(0, 20).map((r, i) => (
                  <tr key={i}>
                    <td className="px-2 py-2">
                       <span className={`px-2 py-1 rounded font-bold ${r.data_quality === 'VALID' ? 'bg-green-100 text-green-800' : r.data_quality === 'PARTIAL' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                         {r.data_quality}
                       </span>
                    </td>
                    <td className="px-2 py-2 font-mono">{r.experiment_id.slice(0,8)}...</td>
                    <td className="px-2 py-2">{r.chaos_type}</td>
                    <td className="px-2 py-2 font-bold">{r.recovery_outcome}</td>
                    <td className="px-2 py-2">{r.impact_score?.toFixed(2)}</td>
                    <td className="px-2 py-2">{r.resilience_score?.toFixed(2)}</td>
                    <td className="px-2 py-2">{r.recovery_time?.toFixed(2)}s</td>
                    <td className="px-2 py-2 text-red-500">{r.validation_warnings.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
        </div>
      )}
    </div>
  );
}
