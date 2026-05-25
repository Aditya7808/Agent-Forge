import { MessageSquare, Database, Zap } from 'lucide-react';

export default function Header({ activeTab, setActiveTab }) {
  return (
    <header className="h-16 border-b border-dark-800 bg-dark-950/80 backdrop-blur-xl flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-dark-50">RAG + SQL Router</h1>
          <p className="text-xs text-dark-500">Intelligent Query Engine</p>
        </div>
      </div>

      <nav className="flex items-center bg-dark-900/50 rounded-xl p-1 border border-dark-800">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
            activeTab === 'chat'
              ? 'bg-primary-600 text-white shadow-lg shadow-primary-600/20'
              : 'text-dark-400 hover:text-dark-200'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab('database')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
            activeTab === 'database'
              ? 'bg-primary-600 text-white shadow-lg shadow-primary-600/20'
              : 'text-dark-400 hover:text-dark-200'
          }`}
        >
          <Database className="w-4 h-4" />
          Database
        </button>
      </nav>

      <div className="flex items-center gap-2">
        <span className="text-xs text-dark-500 bg-dark-800/50 px-3 py-1.5 rounded-lg border border-dark-700/50">
          GPT-4o-mini
        </span>
      </div>
    </header>
  );
}
