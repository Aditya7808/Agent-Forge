import { useState, useCallback, useRef } from 'react';
import { sendMessage } from '../api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const abortRef = useRef(null);

  const send = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendMessage(text, sessionId);
      const assistantMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.response,
        timestamp: Date.now(),
        routeUsed: response.route_used,
        trustScore: response.trust_score,
        sqlQuery: response.sql_query,
        metadata: response.metadata,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: ${error.message}`,
        timestamp: Date.now(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(crypto.randomUUID());
  }, []);

  return { messages, isLoading, send, clearMessages, sessionId, setSessionId };
}
