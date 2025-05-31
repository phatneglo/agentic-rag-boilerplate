# AI Chat Interface

A modular, Claude-inspired AI chat interface built with Bootstrap, vanilla JavaScript, and FastAPI WebSocket support.

## Features

### 🎨 **Modern UI/UX**
- Claude-inspired chat interface design
- Responsive Bootstrap 5 layout
- Dark/light theme support
- Smooth animations and transitions
- Professional typography and spacing

### 💬 **Chat Functionality**
- Real-time WebSocket communication
- Mock AI responses with intelligent content detection
- Typing indicators and status updates
- Message history with timestamps
- Auto-reconnection on connection loss

### 🛠 **Artifacts System**
- Interactive code viewer with syntax highlighting (Prism.js)
- Mermaid diagram rendering
- HTML/Markdown preview
- JSON formatter
- Copy, download, and export functionality
- Expandable artifact viewer

### 📁 **File Management**
- File upload interface (UI ready)
- Drag-and-drop support
- File preview capabilities
- Progress indicators

### 🔧 **Modular Architecture**
- Separated concerns across multiple JS modules
- Easy to extend and customize
- CDN-based dependencies for quick setup
- API-ready for real LLM integration

## File Structure

```
static/modules/chat/
├── chat.html              # Main chat interface
├── css/
│   └── chat.css           # Complete styling
├── js/
│   ├── chat-app.js        # Main application controller
│   ├── chat-websocket.js  # WebSocket communication
│   ├── chat-messages.js   # Message management
│   ├── chat-artifacts.js  # Artifacts system
│   └── chat-service.js    # API service layer
└── README.md              # This file
```

## Components

### **chat-app.js**
Main application controller that orchestrates all chat functionality:
- Initializes all modules
- Manages application state
- Handles user interactions
- Coordinates between modules

### **chat-websocket.js**
WebSocket communication module:
- Connection management with auto-reconnection
- Message queuing and delivery
- Heartbeat mechanism
- Mock AI response generation
- Event-driven architecture

### **chat-messages.js**
Message handling and UI management:
- Message rendering and formatting
- Timestamp formatting
- User/AI message differentiation
- Message history management
- UI state updates

### **chat-artifacts.js**
Artifacts system for displaying interactive content:
- Code highlighting with Prism.js
- Mermaid diagram rendering
- HTML/Markdown preview
- Copy/download functionality
- Toast notifications

### **chat-service.js**
API service layer for HTTP endpoints:
- RESTful API communication
- User preferences management
- Chat history operations
- File upload handling
- Error handling

## API Integration

The chat interface integrates with FastAPI backend routes:

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/chat`
- **Purpose**: Real-time bidirectional communication
- **Protocols**: JSON message format

### HTTP Endpoints
- `POST /api/v1/chat/message` - Send chat message
- `GET /api/v1/chat/preferences` - Get user preferences
- `PUT /api/v1/chat/preferences` - Update preferences
- `GET /api/v1/chat/history` - Get chat history
- `POST /api/v1/chat/sessions` - Save chat session

## Usage

### Accessing the Chat Interface
Navigate to: `http://localhost:8000/chat`

### Sending Messages
1. Type your message in the input area
2. Press Enter or click Send button
3. View AI responses with potential artifacts
4. Interact with code, diagrams, or other content

### Using Artifacts
1. AI responses may include interactive artifacts
2. Click artifact buttons to view content
3. Use copy, download, or export features
4. Expand/collapse artifact viewer as needed

### File Upload (UI Ready)
1. Click the file upload button
2. Select files via file dialog or drag-and-drop
3. Monitor upload progress
4. Files will be processed for chat context

## Customization

### Themes
The interface supports customization through CSS variables:

```css
:root {
  --chat-primary-color: #667eea;
  --chat-bg-color: #ffffff;
  --chat-text-color: #2d3748;
  --chat-border-color: #e2e8f0;
}
```

### Mock Responses
Modify `chat-websocket.js` to customize AI response patterns:

```javascript
// In generateMockResponse function
if (content.includes("your-keyword")) {
    return {
        type: "chat_response",
        content: "Your custom response",
        artifacts: [/* your artifacts */]
    };
}
```

## Development

### Local Development
1. Ensure FastAPI server is running: `python -m app.main`
2. Navigate to `http://localhost:8000/chat`
3. Open browser developer tools for debugging
4. WebSocket connection auto-establishes

### Adding New Features
1. **New Message Types**: Extend `chat-websocket.js` message handlers
2. **New Artifacts**: Add support in `chat-artifacts.js`
3. **UI Components**: Modify `chat.html` and `chat.css`
4. **API Endpoints**: Add routes in `app/api/routes/chat_routes.py`

### Debugging
- WebSocket messages logged to browser console
- Network requests visible in DevTools
- UI state changes logged with detail levels

## Future Enhancements

### Planned Features
- [ ] Voice chat integration
- [ ] Real LLM (OpenAI/Anthropic) integration
- [ ] Advanced file processing
- [ ] Chat export formats (PDF, Word)
- [ ] Collaborative chat sessions
- [ ] Plugin system for custom artifacts

### Integration Points
- **LLM Services**: Replace mock responses in WebSocket handler
- **Vector Database**: Add context retrieval for RAG functionality
- **Auth System**: Integrate user authentication
- **Analytics**: Add usage tracking and insights

## Dependencies

### CDN Libraries
- **Bootstrap 5.3.2**: UI framework
- **FontAwesome 6.5.1**: Icons
- **Prism.js 1.29.0**: Code highlighting
- **Marked 9.1.6**: Markdown parsing
- **Mermaid 10.6.1**: Diagram rendering
- **DOMPurify 3.0.5**: HTML sanitization

### Backend Dependencies
- **FastAPI**: Web framework
- **WebSockets**: Real-time communication
- **Pydantic**: Data validation

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance
- Lazy loading of artifacts
- Efficient DOM updates
- WebSocket connection pooling
- Minimal external dependencies

## Recent Improvements

### Enhanced Markdown Processing
- **Improved chat message rendering**: Headers, lists, blockquotes, code blocks properly formatted
- **Enhanced artifact markdown display**: Full markdown support with styling
- **Better line break handling**: Proper paragraph and line break conversion
- **Code syntax highlighting**: Using Prism.js for better code display

### Robust Mermaid Diagram Support
- **Error handling**: Graceful error display with helpful debugging information
- **Syntax validation**: Automatic cleaning and fixing of common syntax issues
- **Multiple diagram types**: Support for flowcharts, graphs, and architecture diagrams
- **Raw code fallback**: Shows diagram source when rendering fails

### UI/UX Enhancements
- **Clickable artifact markers**: Enhanced "[Code artifact generated]" buttons with visual feedback
- **Responsive artifact viewer**: Proper space allocation and mobile-friendly design
- **Send/Stop button functionality**: Visual state changes during message generation
- **Enhanced styling**: Better typography, spacing, and visual hierarchy

---

**Built with ❤️ for the Agentic RAG Project** 