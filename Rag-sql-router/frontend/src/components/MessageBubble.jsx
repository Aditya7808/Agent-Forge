import { User, Bot, Database, FileSearch, ShieldCheck, AlertTriangle, Code } from 'lucide-react';
import TrustBadge from './TrustBadge';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex items-start gap-3 py-4 animate-slide-up">
        <div className="w-8 h-8 rounded-xl bg-dark-700 border border-dark-600 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-dark-300" />
        </div>
        <div className="flex-1 pt-1">
          <p className="text-dark-100 text-[15px] leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 py-4 animate-slide-up">
      <div className="w-8 h-8 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-primary-400" />
      </div>
      <div className="flex-1 pt-1 space-y-3">
        {message.routeUsed && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border ${
              message.routeUsed === 'sql'
                ? 'bg-blue-500/10 border-blue-500/20 text-blue-300'
                : 'bg-purple-500/10 border-purple-500/20 text-purple-300'
            }`}>
              {message.routeUsed === 'sql' ? (
                <Database className="w-3 h-3" />
              ) : (
                <FileSearch className="w-3 h-3" />
              )}
              {message.routeUsed === 'sql' ? 'SQL Query' : 'Document RAG'}
            </span>
            {message.trustScore !== null && message.trustScore !== undefined && (
              <TrustBadge score={message.trustScore} />
            )}
          </div>
        )}

        {message.isError ? (
          <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <p className="text-sm text-red-300">{message.content}</p>
          </div>
        ) : (
          <div className="text-dark-200 text-[15px] leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        )}

        {message.sqlQuery && (
          <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-3 mt-2">
            <div className="flex items-center gap-2 mb-2">
              <Code className="w-3.5 h-3.5 text-dark-400" />
              <span className="text-xs font-medium text-dark-400">Generated SQL</span>
            </div>
            <code className="text-xs text-emerald-300 font-['JetBrains_Mono'] block overflow-x-auto">
              {message.sqlQuery}
            </code>
          </div>
        )}

        {message.metadata?.sources && message.metadata.sources.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap mt-2">
            <span className="text-xs text-dark-500">Sources:</span>
            {message.metadata.sources.map((source, i) => (
              <span key={i} className="text-xs bg-dark-800/50 border border-dark-700/50 px-2 py-0.5 rounded-md text-dark-400">
                {source}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
