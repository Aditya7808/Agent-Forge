import { useState, useEffect } from 'react';
import { BarChart3, Search, Download, Play, Table, TrendingUp, MapPin, Users } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { getDatabaseStats, getDatabaseData, runDatabaseQuery } from '../api';

const COLORS = ['#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#06b6d4'];

export default function DatabaseExplorer() {
  const [stats, setStats] = useState(null);
  const [data, setData] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [customQuery, setCustomQuery] = useState('SELECT * FROM city_stats ORDER BY population DESC LIMIT 10');
  const [queryResult, setQueryResult] = useState(null);
  const [queryError, setQueryError] = useState(null);
  const [activeView, setActiveView] = useState('overview');

  useEffect(() => {
    getDatabaseStats().then(setStats).catch(console.error);
    getDatabaseData().then(setData).catch(console.error);
  }, []);

  const handleRunQuery = async () => {
    setQueryError(null);
    try {
      const result = await runDatabaseQuery(customQuery);
      setQueryResult(result);
    } catch (err) {
      setQueryError(err.message);
      setQueryResult(null);
    }
  };

  const filteredData = data?.data?.filter(row =>
    row.city_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    row.state?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const downloadCSV = () => {
    if (!data?.data) return;
    const csv = [
      data.columns.join(','),
      ...data.data.map(row => data.columns.map(col => row[col]).join(','))
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'city_stats.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-4 gap-4">
            <StatCard icon={MapPin} label="Total Cities" value={stats.total_cities} color="primary" />
            <StatCard icon={Users} label="Total Population" value={stats.total_population?.toLocaleString()} color="emerald" />
            <StatCard icon={Table} label="States" value={stats.total_states} color="purple" />
            <StatCard icon={TrendingUp} label="Avg Population" value={stats.avg_population?.toLocaleString()} color="amber" />
          </div>
        )}

        {/* View Tabs */}
        <div className="flex items-center gap-2 border-b border-dark-800 pb-3">
          {['overview', 'table', 'query'].map(view => (
            <button
              key={view}
              onClick={() => setActiveView(view)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeView === view
                  ? 'bg-dark-800 text-dark-100 border border-dark-700'
                  : 'text-dark-500 hover:text-dark-300'
              }`}
            >
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview - Charts */}
        {activeView === 'overview' && stats && (
          <div className="grid grid-cols-2 gap-6">
            <div className="glass-panel p-5">
              <h3 className="text-sm font-semibold text-dark-200 mb-4 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary-400" />
                Top 10 Cities by Population
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={stats.top_cities}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="city" tick={{ fill: '#64748b', fontSize: 11 }} angle={-45} textAnchor="end" height={80} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={v => `${(v/1e6).toFixed(1)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px' }}
                    labelStyle={{ color: '#e2e8f0' }}
                    itemStyle={{ color: '#a5b4fc' }}
                    formatter={v => [v.toLocaleString(), 'Population']}
                  />
                  <Bar dataKey="population" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="glass-panel p-5">
              <h3 className="text-sm font-semibold text-dark-200 mb-4">State Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={stats.state_distribution}
                    dataKey="count"
                    nameKey="state"
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    innerRadius={60}
                    label={({ state, count }) => `${state} (${count})`}
                    labelLine={false}
                  >
                    {stats.state_distribution.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px' }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Table View */}
        {activeView === 'table' && (
          <div className="glass-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-500" />
                <input
                  type="text"
                  placeholder="Search cities or states..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-field pl-10 w-full text-sm"
                />
              </div>
              <button onClick={downloadCSV} className="btn-ghost flex items-center gap-2 text-sm">
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            </div>
            <div className="overflow-x-auto rounded-xl border border-dark-700/50">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-dark-800/50">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-dark-400 uppercase tracking-wider">City</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-dark-400 uppercase tracking-wider">State</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-dark-400 uppercase tracking-wider">Population</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-800">
                  {filteredData.slice(0, 50).map((row, i) => (
                    <tr key={i} className="hover:bg-dark-800/30 transition-colors">
                      <td className="px-4 py-3 text-dark-200 font-medium">{row.city_name}</td>
                      <td className="px-4 py-3 text-dark-400">{row.state}</td>
                      <td className="px-4 py-3 text-dark-300 text-right font-['JetBrains_Mono'] text-xs">
                        {row.population?.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-dark-500 mt-3">
              Showing {Math.min(filteredData.length, 50)} of {filteredData.length} results
            </p>
          </div>
        )}

        {/* Custom Query */}
        {activeView === 'query' && (
          <div className="glass-panel p-5 space-y-4">
            <h3 className="text-sm font-semibold text-dark-200">Custom SQL Query</h3>
            <div className="flex gap-3">
              <textarea
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                className="input-field flex-1 font-['JetBrains_Mono'] text-sm resize-none"
                rows={3}
                placeholder="SELECT * FROM city_stats WHERE..."
              />
              <button onClick={handleRunQuery} className="btn-primary self-end flex items-center gap-2">
                <Play className="w-4 h-4" />
                Run
              </button>
            </div>
            <div className="flex gap-2 flex-wrap">
              {[
                "SELECT * FROM city_stats ORDER BY population DESC LIMIT 10",
                "SELECT state, COUNT(*) as count FROM city_stats GROUP BY state ORDER BY count DESC",
                "SELECT * FROM city_stats WHERE population > 1000000",
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => setCustomQuery(q)}
                  className="text-xs bg-dark-800/50 border border-dark-700/50 px-3 py-1.5 rounded-lg text-dark-400 hover:text-dark-200 hover:border-dark-600 transition-colors"
                >
                  {q.slice(0, 50)}...
                </button>
              ))}
            </div>
            {queryError && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                <p className="text-sm text-red-300">{queryError}</p>
              </div>
            )}
            {queryResult && (
              <div className="overflow-x-auto rounded-xl border border-dark-700/50">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-dark-800/50">
                      {queryResult.columns.map((col, i) => (
                        <th key={i} className="px-4 py-3 text-left text-xs font-semibold text-dark-400 uppercase tracking-wider">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-800">
                    {queryResult.data.slice(0, 50).map((row, i) => (
                      <tr key={i} className="hover:bg-dark-800/30 transition-colors">
                        {queryResult.columns.map((col, j) => (
                          <td key={j} className="px-4 py-3 text-dark-300 font-['JetBrains_Mono'] text-xs">{row[col]?.toLocaleString?.() || row[col]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-xs text-dark-500 p-3">{queryResult.row_count} rows returned</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  const colorMap = {
    primary: 'from-primary-500/20 to-primary-700/10 border-primary-500/20 text-primary-400',
    emerald: 'from-emerald-500/20 to-emerald-700/10 border-emerald-500/20 text-emerald-400',
    purple: 'from-purple-500/20 to-purple-700/10 border-purple-500/20 text-purple-400',
    amber: 'from-amber-500/20 to-amber-700/10 border-amber-500/20 text-amber-400',
  };

  return (
    <div className={`bg-gradient-to-br ${colorMap[color]} border rounded-2xl p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium text-dark-400">{label}</span>
      </div>
      <p className="text-xl font-bold text-dark-100">{value}</p>
    </div>
  );
}
