import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, RotateCcw, Sparkles } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatInterface({ chat }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || chat.isLoading) return;
    chat.send(input);
    setInput('');
  };

  const suggestions = [
    "What is the population of Houston, Texas?",
    "Which state has the most cities?",
    "List the top 5 largest cities",
    "What cities are in California?",
  ];

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {chat.messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500/20 to-primary-700/20 border border-primary-500/30 flex items-center justify-center mb-6">
              <Sparkles className="w-8 h-8 text-primary-400" />
            </div>
            <h2 className="text-2xl font-semibold text-dark-100 mb-2">Intelligent Query Router</h2>
            <p className="text-dark-400 text-center mb-8 max-w-md">
              Ask questions about city data (routed to SQL) or upload documents for RAG-powered answers with trust scoring.
            </p>
            <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  className="text-left text-sm text-dark-300 bg-dark-800/30 hover:bg-dark-800/60 border border-dark-700/30 hover:border-dark-600 rounded-xl px-4 py-3 transition-all duration-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-1">
            {chat.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {chat.isLoading && (
              <div className="flex items-center gap-3 py-4 px-4 animate-fade-in">
                <div className="w-8 h-8 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-dark-500 animate-bounce" style={{animationDelay: '0ms'}}></div>
                  <div className="w-2 h-2 rounded-full bg-dark-500 animate-bounce" style={{animationDelay: '150ms'}}></div>
                  <div className="w-2 h-2 rounded-full bg-dark-500 animate-bounce" style={{animationDelay: '300ms'}}></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="border-t border-dark-800 bg-dark-950/50 backdrop-blur-xl p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-center gap-3">
          <button
            type="button"
            onClick={chat.clearMessages}
            className="p-2.5 hover:bg-dark-800 rounded-xl transition-colors text-dark-500 hover:text-dark-300"
            title="Clear chat"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about city data or your documents..."
              className="w-full input-field pr-12"
              disabled={chat.isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || chat.isLoading}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-30 disabled:hover:bg-primary-600 transition-all duration-200"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
