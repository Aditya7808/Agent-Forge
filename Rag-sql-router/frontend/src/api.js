const API_BASE = '/api';

export async function sendMessage(message, sessionId) {
  const response = await fetch(`${API_BASE}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to process message');
  }
  return response.json();
}

export async function uploadDocuments(files, sessionId) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  if (sessionId) formData.append('session_id', sessionId);

  const response = await fetch(`${API_BASE}/documents/upload?session_id=${sessionId || ''}`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }
  return response.json();
}

export async function getDatabaseStats() {
  const response = await fetch(`${API_BASE}/database/stats`);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}

export async function getDatabaseData() {
  const response = await fetch(`${API_BASE}/database/data`);
  if (!response.ok) throw new Error('Failed to fetch data');
  return response.json();
}

export async function runDatabaseQuery(query) {
  const response = await fetch(`${API_BASE}/database/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Query failed');
  }
  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error('API unavailable');
  return response.json();
}
