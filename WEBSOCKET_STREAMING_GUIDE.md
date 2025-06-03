# WebSocket Streaming Multi-Agent System Guide

## 🚀 Overview

This WebSocket-based multi-agent system provides real-time streaming with structured JSON responses, making it perfect for rich frontend experiences. Each event includes metadata about which agent is responding, what tools they're using, and their current mode.

## 📡 JSON Structure

Every WebSocket message follows this structured format:

```json
{
  "timestamp": "2025-06-03T14:10:30.123456",
  "user": "ChatAgent",           // Which agent is responding
  "tool": "search_documents_websocket",  // Tool being used ("none" if no tool)
  "mode": "thinking",           // thinking|output|error
  "event_type": "tool_call",    // Type of event
  "content": "Using tool: search_documents_websocket"
}
```

## 🎯 Event Types

### 1. **system_ready**
```json
{
  "user": "system",
  "tool": "none", 
  "mode": "output",
  "event_type": "system_ready",
  "content": "🤖 WebSocket Multi-Agent System Ready! Type your message to begin."
}
```

### 2. **agent_switch** 
```json
{
  "user": "KnowledgeBaseAgent",
  "tool": "none",
  "mode": "thinking", 
  "event_type": "agent_switch",
  "content": "KnowledgeBaseAgent is handling your request..."
}
```

### 3. **tool_call**
```json
{
  "user": "KnowledgeBaseAgent", 
  "tool": "search_documents_websocket",
  "mode": "thinking",
  "event_type": "tool_call", 
  "content": "Using tool: search_documents_websocket"
}
```

### 4. **search_progress** (Tool-specific)
```json
{
  "user": "KnowledgeBaseAgent",
  "tool": "search_documents_websocket", 
  "mode": "thinking",
  "event_type": "search_progress",
  "content": "🔎 Executing search query..."
}
```

### 5. **tool_result**
```json
{
  "user": "KnowledgeBaseAgent",
  "tool": "search_documents_websocket",
  "mode": "output", 
  "event_type": "tool_result",
  "content": "🎯 Found 3 documents for 'baguio':\n📄 Document 1: ..."
}
```

### 6. **agent_response**
```json
{
  "user": "KnowledgeBaseAgent", 
  "tool": "none",
  "mode": "output",
  "event_type": "agent_response", 
  "content": "Here are the search results for you, Roniel Nuqui!"
}
```

### 7. **stream_token** (Real-time typing)
```json
{
  "user": "ChatAgent",
  "tool": "none", 
  "mode": "output",
  "event_type": "stream_token",
  "content": "Hello"
}
```

### 8. **error**
```json
{
  "user": "system",
  "tool": "none",
  "mode": "error", 
  "event_type": "error",
  "content": "❌ Typesense connection failed"
}
```

## 🔧 How to Use

### 1. **Start the Server**
```bash
python websocket_streaming_agents.py
```
Server runs on `ws://localhost:8765`

### 2. **Start Test Client** 
```bash
python websocket_streaming_agents.py client
```

### 3. **Send Messages**
Send JSON messages to the WebSocket:
```json
{
  "message": "Hello there, my name is Roniel Nuqui"
}
```

### 4. **Receive Structured Events**
You'll get real-time JSON events showing:
- Which agent is handling the request
- What tools they're using
- Their thinking process
- Final results

## 🎨 Frontend Integration Ideas

### React Example
```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.event_type) {
    case 'agent_switch':
      showAgentIndicator(data.user);
      break;
      
    case 'tool_call':
      showToolActivity(data.tool, data.user);
      break;
      
    case 'search_progress':
      showThinkingAnimation(data.content);
      break;
      
    case 'agent_response':
      displayMessage(data.content, data.user);
      break;
      
    case 'stream_token':
      appendToTypingIndicator(data.content);
      break;
      
    case 'error':
      showError(data.content);
      break;
  }
};

// Send message
ws.send(JSON.stringify({
  message: "Search for documents about Baguio"
}));
```

### Vue.js Example
```javascript
// Component data
data() {
  return {
    ws: null,
    messages: [],
    currentAgent: null,
    isThinking: false,
    toolsActive: []
  }
}

// WebSocket handler
handleWebSocketMessage(event) {
  const data = JSON.parse(event.data);
  
  if (data.mode === 'thinking') {
    this.isThinking = true;
    this.showThinkingBubble(data.content);
  } else if (data.mode === 'output') {
    this.isThinking = false;
    this.addMessage(data.content, data.user);
  }
  
  if (data.event_type === 'agent_switch') {
    this.currentAgent = data.user;
  }
}
```

## 🗄️ Database Features

### Enhanced Memory
- **Chat History**: Stores all conversations in PostgreSQL
- **User Facts**: Automatically extracts and remembers facts about users
- **Session Management**: Persistent memory across sessions

### Database Tables
```sql
-- Chat history
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User facts 
CREATE TABLE user_facts (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    fact TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, fact)
);
```

## 🎯 Benefits

### For Development
- **Real-time debugging**: See exactly what each agent is doing
- **Tool transparency**: Monitor all tool calls and results
- **Error tracking**: Immediate error visibility

### For Users
- **Rich feedback**: Know which agent is helping them
- **Progress updates**: See search and processing progress
- **Interactive experience**: Real-time streaming responses

### For Frontend
- **Structured data**: Clean JSON format for easy parsing
- **Event-driven**: Build reactive UIs based on agent events
- **Flexible rendering**: Different UI for different event types

## 🚀 Example Flow

1. **User**: "Hello, my name is Roniel Nuqui"
   - `system_ready` → Show welcome
   - `processing_start` → Show thinking
   - `agent_switch` → ChatAgent indicator
   - `agent_response` → "Hello Roniel Nuqui!"

2. **User**: "Search for documents about Baguio"
   - `agent_switch` → KnowledgeBaseAgent
   - `tool_call` → search_documents_websocket
   - `search_progress` → "🔍 Starting search..."
   - `search_progress` → "📡 Connecting to Typesense..."
   - `search_progress` → "🔎 Executing search query..."
   - `tool_result` → Full search results
   - `agent_response` → Agent's response

## 🔧 Configuration

### Database Setup
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'standard_db_eassist',
    'user': 'postgres',
    'password': '0yq5h3to9',
    'port': 5432
}
```

### WebSocket Settings
- **Port**: 8765
- **Protocol**: WebSocket
- **Format**: JSON
- **Encoding**: UTF-8

This system provides the foundation for building rich, interactive multi-agent experiences with full transparency into the AI's thought process! 