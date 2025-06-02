# PostgreSQL Chat Memory with LangGraph Integration

This document describes the PostgreSQL-based chat memory system that integrates with LangGraph for persistent conversation history and state management.

## 🎯 Overview

The chat memory system provides:

- **Persistent conversation history** stored in PostgreSQL
- **LangGraph state integration** for stateful agent workflows  
- **Session management** for grouping related conversations
- **Message tracking** with metadata and artifacts
- **Multi-user support** with user-scoped sessions
- **Advanced filtering** and search capabilities

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chat Interface                           │
│         (WebSocket + REST API + Frontend)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                LangGraph Agent Orchestrator                │
│           (with PostgreSQL Memory Integration)             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              PostgreSQL Chat Memory                        │
│            (Sessions + Messages + Metadata)                │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Database Schema

### Chat Sessions Table
```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL DEFAULT 'New Conversation',
    description TEXT,
    user_id VARCHAR(255),
    session_type VARCHAR(50) DEFAULT 'chat',
    config JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Chat Messages Table
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL, -- 'human', 'ai', 'system', 'function'
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- 'user', 'assistant', 'system'
    message_metadata JSONB DEFAULT '{}',
    additional_kwargs JSONB DEFAULT '{}',
    agent_name VARCHAR(100),
    agent_metadata JSONB DEFAULT '{}',
    sequence_number INTEGER NOT NULL,
    parent_message_id UUID REFERENCES chat_messages(id),
    tokens_used INTEGER,
    processing_time INTEGER,
    artifacts JSONB DEFAULT '[]',
    is_streamed BOOLEAN DEFAULT false,
    is_error BOOLEAN DEFAULT false,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 🚀 Quick Start

### 1. Setup Database

1. **Install PostgreSQL dependencies:**
   ```bash
   pip install asyncpg sqlalchemy[asyncio] alembic
   ```

2. **Configure database URL in `.env`:**
   ```bash
   DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/agentic_rag_db
   ```

3. **Initialize database:**
   ```python
   from app.db.session import init_db
   await init_db()
   ```

### 2. Basic Usage

#### Create a Chat Session
```python
from app.db.memory import PostgresChatMemory

memory = PostgresChatMemory()

session = await memory.create_session(
    title="My Conversation",
    user_id="user_123",
    session_type="chat",
    config={"model": "gpt-4o-mini"},
    context={"topic": "programming"}
)
```

#### Add Messages
```python
from langchain_core.messages import HumanMessage, AIMessage

# Add user message
user_msg = HumanMessage(content="Hello, how are you?")
await memory.add_message(
    session_id=session.id,
    message=user_msg,
    agent_name="user"
)

# Add AI response
ai_msg = AIMessage(content="Hello! I'm doing well, thank you!")
await memory.add_message(
    session_id=session.id,
    message=ai_msg,
    agent_name="general_agent",
    tokens_used=25,
    processing_time=150
)
```

#### Retrieve Conversation History
```python
# Get all messages
history = await memory.get_conversation_history(session.id)

# Get limited messages
recent_history = await memory.get_conversation_history(session.id, limit=10)

# Filter by message type
ai_messages = await memory.get_messages(session.id, message_types=["ai"])
```

### 3. LangGraph Integration

#### Update Agent Orchestrator
```python
from app.agents.agent_orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

# Process request with memory
response = await orchestrator.process_request(
    user_input="Write a Python function for fibonacci",
    config={"session_id": str(session.id)}
)
```

The orchestrator automatically:
- Loads conversation history at the start
- Processes the request with context
- Saves the new messages to memory

## 📝 API Endpoints

### Session Management

#### Create Session
```http
POST /api/v1/chat/memory/sessions
Content-Type: application/json

{
    "title": "New Conversation",
    "user_id": "user_123",
    "session_type": "chat",
    "config": {"model": "gpt-4o-mini"},
    "context": {"topic": "programming"}
}
```

#### List Sessions
```http
GET /api/v1/chat/memory/sessions?user_id=user_123&limit=50&offset=0
```

#### Get Session
```http
GET /api/v1/chat/memory/sessions/{session_id}
```

#### Update Session
```http
PUT /api/v1/chat/memory/sessions/{session_id}
Content-Type: application/json

{
    "title": "Updated Title"
}
```

#### Archive Session
```http
POST /api/v1/chat/memory/sessions/{session_id}/archive
```

#### Delete Session
```http
DELETE /api/v1/chat/memory/sessions/{session_id}
```

### Message Management

#### Get Conversation History
```http
GET /api/v1/chat/memory/sessions/{session_id}/messages?limit=100
```

#### Clear Messages
```http
DELETE /api/v1/chat/memory/sessions/{session_id}/messages
```

#### Get Session Statistics
```http
GET /api/v1/chat/memory/sessions/{session_id}/stats
```

### Health Check
```http
GET /api/v1/chat/memory/health
```

## 🔧 Configuration

### Environment Variables
```bash
# Database configuration
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/agentic_rag_db

# Optional: Database connection settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=0
DB_ECHO=false
```

### LangGraph Integration Settings
```python
# In agent orchestrator config
config = {
    "session_id": "uuid-string",  # Required for memory
    "callbacks": [streaming_callback],  # Optional for streaming
    "memory_limit": 20,  # Number of historical messages to load
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_chat_memory.py
```

The test covers:
- ✅ Database setup and connection
- ✅ Basic memory operations (CRUD)
- ✅ LangGraph integration
- ✅ Advanced features (filtering, stats)
- ✅ Session management
- ✅ Memory cleanup

## 🔍 Advanced Features

### Message Filtering
```python
# Get only AI responses
ai_messages = await memory.get_messages(
    session_id, 
    message_types=["ai"]
)

# Get recent messages with limit
recent = await memory.get_messages(
    session_id, 
    limit=10
)
```

### Session Statistics
```python
stats = await memory.get_session_stats(session_id)
# Returns:
# {
#     "session_id": "uuid",
#     "message_counts": {"human": 5, "ai": 5},
#     "total_messages": 10,
#     "total_tokens": 1250,
#     "created_at": "2024-01-01T10:00:00Z",
#     "last_activity": "2024-01-01T10:30:00Z"
# }
```

### Multi-User Support
```python
# List sessions for specific user
user_sessions = await memory.list_sessions(user_id="user_123")

# Filter archived sessions
active_sessions = await memory.list_sessions(
    user_id="user_123",
    include_archived=False
)
```

### Artifact Storage
```python
# Add message with artifacts
await memory.add_message(
    session_id=session.id,
    message=ai_msg,
    agent_name="code_agent",
    artifacts=[
        {
            "id": "artifact_1",
            "type": "code",
            "title": "Python Function",
            "content": "def fibonacci(n): ..."
        }
    ]
)
```

## 🛠️ LangGraph Best Practices

### 1. State Management
```python
class MessagesState(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: Optional[str]  # For memory integration
    context: Dict[str, Any]
    config: Dict[str, Any]
```

### 2. Memory Loading Node
```python
async def load_memory(state: MessagesState) -> MessagesState:
    session_id = state.get("session_id")
    if session_id:
        history = await memory.get_conversation_history(
            uuid.UUID(session_id), 
            limit=20
        )
        state["messages"] = history + state.get("messages", [])
    return state
```

### 3. Memory Saving Node
```python
async def save_memory(state: MessagesState) -> MessagesState:
    session_id = state.get("session_id")
    messages = state.get("messages", [])
    
    if session_id and messages:
        # Save recent messages
        for message in messages[-2:]:  # User + AI response
            await memory.add_message(
                session_id=uuid.UUID(session_id),
                message=message,
                agent_name=get_agent_name(message)
            )
    return state
```

### 4. Workflow Integration
```python
# Add memory nodes to workflow
workflow.add_node("load_memory", load_memory)
workflow.add_node("save_memory", save_memory)

# Connect to workflow
workflow.add_edge(START, "load_memory")
workflow.add_edge("load_memory", "route_request")
workflow.add_edge("execute_agent", "save_memory")
workflow.add_edge("save_memory", END)
```

## 📊 Performance Considerations

### Database Optimization
- **Indexes** on `session_id`, `user_id`, `created_at`
- **Connection pooling** for high throughput
- **Query optimization** for large message histories
- **Archiving strategy** for old conversations

### Memory Management
- **Limit historical messages** loaded (default: 20)
- **Pagination** for large conversation lists
- **Soft deletion** with archiving instead of hard deletes
- **Regular cleanup** of very old sessions

### Monitoring
- Track database connection pool usage
- Monitor query performance
- Set up alerts for failed memory operations
- Log memory load/save statistics

## 🚀 Production Deployment

### Database Setup
1. Use a managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
2. Configure proper backup and recovery
3. Set up read replicas for improved performance
4. Enable connection pooling (PgBouncer)

### Security
- Use environment variables for credentials
- Enable SSL/TLS for database connections
- Implement proper user authentication
- Regular security updates

### Monitoring
- Set up database monitoring (CPU, memory, connections)
- Monitor application logs for memory errors
- Track conversation metrics and usage patterns
- Set up alerts for system health

## 🤝 Contributing

When contributing to the memory system:

1. **Follow LangGraph patterns** for state management
2. **Add comprehensive tests** for new features
3. **Document API changes** in this file
4. **Consider backwards compatibility** for schema changes
5. **Test with realistic data volumes** before deployment

## 📚 References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL Async Programming](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [LangChain Memory Patterns](https://python.langchain.com/docs/modules/memory/)
- [FastAPI Database Integration](https://fastapi.tiangolo.com/tutorial/sql-databases/) 