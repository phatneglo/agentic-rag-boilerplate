# 🤖 Multi-Agent Chat Module

A standalone chat interface built with Bootstrap 5 and vanilla JavaScript for the multi-agent RAG system.

## Features

✨ **Modern UI/UX**
- Beautiful responsive design with Bootstrap 5
- Real-time typing indicators
- Animated message bubbles
- Professional color scheme

🔄 **Real-time Communication**
- WebSocket-based chat functionality
- Live agent switching indicators
- Real-time search results display
- Connection status monitoring

🤖 **Multi-Agent Support**
- ChatAgent for general conversation
- KnowledgeBaseAgent for document search
- Visual agent identification with icons and colors
- Activity logging and session tracking

📱 **Responsive Design**
- Mobile-friendly interface
- Adaptive sidebar layout
- Touch-friendly controls
- Cross-browser compatibility

## File Structure

```
static/modules/chat/
├── index.html          # Main chat interface
├── css/
│   └── chat.css        # Custom styles
├── js/
│   └── chat.js         # Chat functionality
└── README.md           # This file
```

## Usage

### Via FastAPI Routes

1. **Standalone Chat Interface**: `/chat`
   - Full-featured chat module
   - Self-contained with all dependencies
   - Perfect for embedding or standalone use

2. **WebSocket API**: `/chat/ws/{session_id}`
   - Real-time bidirectional communication
   - JSON event streaming
   - Session management

### Direct Access

Open `http://localhost:8000/chat` in your browser to access the standalone chat interface.

## Features in Detail

### 🎨 Visual Design
- Clean, modern chat bubbles
- Agent-specific color coding
- Smooth animations and transitions
- Professional typography

### 🔧 Technical Features
- Vanilla JavaScript (no framework dependencies)
- WebSocket real-time communication
- Bootstrap 5 responsive grid
- Event-driven architecture

### 📊 Real-time Updates
- Live typing indicators
- Agent switching notifications
- Tool usage tracking
- Activity logging

### 🛠️ Quick Actions
- Pre-defined message buttons
- Chat history clearing
- Session status display
- One-click searches

## Integration

This module is designed to be:
- **Standalone**: Works independently with its own assets
- **Embeddable**: Can be integrated into other applications
- **Scalable**: Supports multiple concurrent sessions
- **Maintainable**: Clean, documented code structure

## Dependencies

- **Bootstrap 5**: CSS framework and components
- **Bootstrap Icons**: Icon library
- **Modern Browser**: WebSocket and ES6 support required

## Configuration

The chat system automatically:
- Generates unique session IDs
- Establishes WebSocket connections
- Handles connection errors gracefully
- Manages message history

No additional configuration required for basic usage. 