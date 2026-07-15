import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function App() {
  // ----- STATE VARIABLES -----
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState('groq');
  
  // 🆕 MODULE 1 & 2: Messages store text AND sources
  const [messages, setMessages] = useState([]);

  // Ref for auto-scrolling to the latest message
  const messagesEndRef = useRef(null);

  // Auto-scroll effect
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ----- HANDLERS -----

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a PDF first');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post(`${API_BASE_URL}/upload`, formData);
      alert('✅ PDF Uploaded and Indexed successfully!');
    } catch (e) {
      alert('❌ Upload failed. Make sure Flask is running.');
    }
  };

  const handleChat = async () => {
    if (!query.trim()) return;

    // 1. Add User Message to UI immediately
    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    
    // 2. Clear input & set loading
    setQuery('');
    setLoading(true);

    try {
      // 3. Send request to Flask (with full history for Memory)
      const res = const res = await axios.post(`${API_BASE_URL}/chat`, {
        provider: provider,
        history: messages  // Send previous messages for context
      });

      // 4. Add Assistant Message to UI (with Sources)
      const assistantMessage = {
        role: 'assistant',
        content: res.data.answer || '⚠️ No response from server.',
        sources: res.data.sources || []  // 🆕 MODULE 2: Sources attached here
      };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat Error:', error);
      // Add error message to chat
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Error: ${error.message}. Make sure Flask is running.`,
        sources: []
      }]);
    }
    setLoading(false);
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleChat();
    }
  };

  // ----- RENDER -----
  return (
    <div className="app-container">
      <h1>🚀 Agentic RAG (Hybrid + Tools)</h1>

      {/* Upload Section */}
      <div className="upload-section">
        <input 
          type="file" 
          accept=".pdf" 
          onChange={(e) => setFile(e.target.files[0])} 
          className="file-input"
        />
        <button onClick={handleUpload} className="upload-button">
          Index PDF
        </button>
      </div>

      <hr />

      {/* Chat Interface */}
      <div className="chat-interface">
        {/* Dropdown & Input */}
        <div className="chat-section">
          <select 
            value={provider} 
            onChange={(e) => setProvider(e.target.value)} 
            style={{ padding: '10px', borderRadius: '8px', marginRight: '10px', border: '2px solid #646cff' }}
          >
            <option value="groq">⚡ Groq (Fast)</option>
            <option value="gemini">🧠 Gemini (Smart)</option>
          </select>

          <input 
            type="text" 
            placeholder="Ask about the PDF or type 'company'..." 
            value={query} 
            onChange={(e) => setQuery(e.target.value)} 
            onKeyDown={handleKeyPress}
            className="chat-input"
            disabled={loading}
          />
          <button onClick={handleChat} className="chat-button" disabled={loading}>
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>

        {/* 🆕 MODULE 1 & 2: Messages Display Area */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              💬 Your conversation will appear here.
              <br />
              <span style={{ fontSize: '14px', color: '#888' }}>
                Upload a PDF and ask a question to get started.
              </span>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div 
                key={index} 
                className={`message ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}
              >
                <div className="message-bubble">
                  <strong>{msg.role === 'user' ? '🧑‍💻 You' : '🤖 AI'}:</strong>
                  <div className="message-content">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                  
                  {/* 🆕 MODULE 2: Render Sources for Assistant Messages */}
                  {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                    <div className="sources-container">
                      <span className="sources-label">📖 Sources:</span>
                      {msg.sources.map((source, idx) => (
                        <span key={idx} className="source-tag">
                          📄 {source.source} (Page {source.page})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {/* Invisible div for auto-scroll */}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  );
}

export default App;