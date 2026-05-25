import { useState } from 'react';
import { useChat } from './hooks/useChat';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DatabaseExplorer from './components/DatabaseExplorer';

export default function App() {
  const chat = useChat();
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [documentsUploaded, setDocumentsUploaded] = useState(false);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          open={sidebarOpen}
          setOpen={setSidebarOpen}
          sessionId={chat.sessionId}
          onDocumentsUploaded={() => setDocumentsUploaded(true)}
          documentsUploaded={documentsUploaded}
        />

        <main className="flex-1 overflow-hidden">
          {activeTab === 'chat' ? (
            <ChatInterface chat={chat} />
          ) : (
            <DatabaseExplorer />
          )}
        </main>
      </div>
    </div>
  );
}
