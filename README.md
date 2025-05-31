# Agentic RAG - AI Chat System

A complete AI chat system with modular architecture, featuring document processing, file management, and an interactive chat interface with artifacts support.

## 🚀 Features

### 📊 Dashboard
- **AdminLTE-themed dashboard** with real-time system monitoring
- **API health monitoring** with live status updates
- **File storage metrics** and usage statistics
- **Navigation between modules** (Dashboard, Chat, File Manager)

### 💬 AI Chat Interface
- **Claude-inspired design** with modern, responsive UI
- **Real-time WebSocket communication** for instant responses
- **Artifacts system** supporting:
  - Code snippets with syntax highlighting (Prism.js)
  - Mermaid diagrams and flowcharts
  - HTML/Markdown rendering
  - JSON formatting and validation
- **File upload support** with drag-and-drop functionality
- **Chat history** with session management
- **Export capabilities** (JSON, TXT formats)
- **User preferences** for customization
- **Responsive design** for mobile and desktop

### 📁 File Manager
- **Web-based file browser** with grid and list views
- **Upload/download** with progress tracking
- **Folder management** (create, rename, move, delete)
- **Search functionality** across files and folders
- **Drag-and-drop** file operations
- **Context menus** for file actions
- **Breadcrumb navigation**

### 🔧 Backend API
- **FastAPI-based REST API** with automatic documentation
- **WebSocket support** for real-time chat
- **File upload/processing** endpoints
- **Health monitoring** and metrics
- **Redis integration** for queue management
- **Structured logging** with detailed request tracking

## 📁 Project Structure

```
agentic-rag/
├── app/                          # Backend FastAPI application
│   ├── api/routes/              # API route handlers
│   │   ├── chat_routes.py       # Chat API endpoints
│   │   ├── document_routes.py   # Document processing
│   │   ├── file_manager.py      # File management API
│   │   └── file_routes.py       # File upload/download
│   ├── core/                    # Core configuration
│   ├── models/                  # Pydantic models
│   └── main.py                  # Main FastAPI application
├── static/modules/              # Frontend modules
│   ├── chat/                    # AI Chat Interface
│   │   ├── chat.html           # Main chat UI
│   │   ├── css/chat.css        # Claude-inspired styling
│   │   └── js/                 # Modular JavaScript
│   │       ├── chat-app.js     # Main application coordinator
│   │       ├── chat-websocket.js # WebSocket management
│   │       ├── chat-artifacts.js # Artifacts system
│   │       ├── chat-messages.js # Message handling
│   │       └── chat-service.js  # API communication
│   ├── dashboard/               # Main Dashboard
│   │   ├── dashboard.html      # AdminLTE dashboard
│   │   ├── css/dashboard.css   # Dashboard styling
│   │   └── js/dashboard.js     # Dashboard functionality
│   └── file-manager/           # File Manager
│       ├── index.html          # File browser UI
│       ├── css/                # File manager styles
│       └── js/                 # File management logic
└── requirements.txt            # Python dependencies
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Redis (for queue management)
- Node.js (optional, for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-rag
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Redis server**
   ```bash
   redis-server
   ```

4. **Run the application**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - Dashboard: http://localhost:8000/
   - Chat Interface: http://localhost:8000/chat
   - File Manager: http://localhost:8000/file-manager
   - API Documentation: http://localhost:8000/docs

## 💻 Usage

### Dashboard
1. Navigate to http://localhost:8000/
2. Monitor system health and metrics
3. Use the sidebar to switch between modules
4. View real-time API status and file storage usage

### AI Chat
1. Click "AI Chat" in the dashboard or visit http://localhost:8000/chat
2. Type messages in the input field at the bottom
3. Use suggestion cards for quick interactions
4. Upload files by clicking the attachment button or dragging files
5. View generated artifacts (code, diagrams) in the sidebar
6. Export chat history using the history button

### File Manager
1. Click "File Manager" in the dashboard or visit http://localhost:8000/file-manager
2. Browse files and folders using the grid or list view
3. Upload files by clicking "Upload" or dragging files to the interface
4. Create folders, rename files, and manage your documents
5. Use the search bar to find specific files

## 🔌 API Endpoints

### Chat API
- `GET /api/v1/chat/preferences` - Get user preferences
- `PUT /api/v1/chat/preferences` - Update user preferences
- `POST /api/v1/chat/message` - Send chat message (HTTP fallback)
- `GET /api/v1/chat/history` - Get chat history
- `POST /api/v1/chat/sessions` - Save chat session
- `GET /api/v1/chat/sessions` - List chat sessions
- `WS /ws/chat` - WebSocket endpoint for real-time chat

### File Management API
- `GET /api/v1/file-manager/` - List files and folders
- `POST /api/v1/file-manager/upload` - Upload files
- `POST /api/v1/file-manager/folder` - Create folder
- `DELETE /api/v1/file-manager/item` - Delete files/folders
- `PUT /api/v1/file-manager/rename` - Rename items
- `PUT /api/v1/file-manager/move` - Move items

### System API
- `GET /health` - System health check
- `GET /api` - API information

## 🏗️ Architecture

### Modular Frontend Design
- **Separation of concerns** with dedicated modules for each feature
- **Component-based architecture** for easy maintenance
- **Event-driven communication** between modules
- **Responsive design** with Bootstrap 5

### Backend Architecture
- **FastAPI** for high-performance async API
- **Pydantic** for data validation and serialization
- **WebSocket** support for real-time communication
- **Redis** for queue management and caching
- **Structured logging** for monitoring and debugging

### Real-time Features
- **WebSocket communication** for instant chat responses
- **Live dashboard updates** with health monitoring
- **File upload progress** tracking
- **Connection status** indicators

## 🔧 Customization

### Adding New Chat Features
1. Extend `chat-service.js` for new API endpoints
2. Add message types in `chat-websocket.js`
3. Implement UI components in `chat-app.js`
4. Add backend endpoints in `chat_routes.py`

### Extending File Manager
1. Add new file operations in `file-operations.js`
2. Implement backend handlers in `file_manager.py`
3. Update UI components in `ui-components.js`

### Dashboard Customization
1. Modify `dashboard.css` for styling
2. Add new widgets in `dashboard.js`
3. Extend health monitoring in `main.py`

## 🚧 Development Status

### ✅ Completed Features
- Complete chat interface with artifacts
- Real-time WebSocket communication
- File upload and management
- Dashboard with system monitoring
- Modular frontend architecture
- Backend API with documentation
- Health monitoring and logging

### 🔄 Ready for LLM Integration
The system is **production-ready** and designed for easy LLM integration:

1. **Replace mock responses** in `generate_ai_response()` function
2. **Add your LLM service** (OpenAI, Anthropic, local models, etc.)
3. **Customize artifact types** based on your LLM capabilities
4. **Configure authentication** if needed

### 🔮 Future Enhancements
- Voice input integration
- Advanced file processing (OCR, document parsing)
- User authentication and multi-tenancy
- Plugin system for custom artifacts
- Advanced search with semantic similarity
- Real-time collaboration features

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For questions, issues, or feature requests, please open an issue on GitHub.

---

**Built with ❤️ using FastAPI, WebSockets, and modern web technologies.** 