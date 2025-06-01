# LangGraph Agent Orchestrator System

## Overview

This project implements a **modular AI agent system** using **LangGraph** and **GPT-4o mini** that provides specialized artifact generation capabilities through a clean, maintainable architecture.

## 🎯 Key Features

### 🤖 **Specialized Agents**
- **Code Agent**: Generates Python, JavaScript, SQL, and other programming language artifacts
- **Diagram Agent**: Creates Mermaid diagrams, flowcharts, system architectures
- **Analysis Agent**: Performs data analysis, business intelligence, and technical evaluations
- **Document Agent**: Writes technical documentation, guides, and business reports
- **Visualization Agent**: Creates charts, graphs, and data visualizations

### 🔧 **LangGraph Orchestration**
- **Intelligent routing** based on content analysis and keyword matching
- **Parallel execution** of multiple agents for complex requests
- **State management** using TypedDict and proper workflow orchestration
- **Graceful fallbacks** when agents fail or APIs are unavailable

### 💰 **Cost-Effective GPT-4o Mini Integration**
- Uses **GPT-4o mini** for optimal cost-performance ratio
- **Mock responses** when API key is not configured
- **Configurable parameters** (temperature, max tokens, timeout)
- **Error handling** with automatic fallbacks

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chat Interface                           │
│         (WebSocket + Bootstrap + Vanilla JS)               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Agent Orchestrator                          │
│              (LangGraph Workflow)                          │
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Route     │  │   Execute   │  │   Combine          │ │
│  │  Request    │→ │   Agents    │→ │  Responses         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Specialized Agents                          │
│                                                            │
│  ┌────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │  Code  │ │Diagram  │ │Analysis │ │Document │ │Visual. ││
│  │ Agent  │ │ Agent   │ │ Agent   │ │ Agent   │ │ Agent  ││
│  └────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  GPT-4o mini                               │
│              (OpenAI API)                                  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install langgraph==0.3.28 langchain-openai==0.2.12 langchain-core==0.3.30 openai==1.57.2
```

### 2. Configuration
Set your OpenAI API key (optional - works with mock responses if not set):
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_TEMPERATURE="0.7"
export OPENAI_MAX_TOKENS="4000"
```

### 3. Run Demo
```bash
python demo_agents.py
```

### 4. Start Web Interface
```bash
python -m app.main
```
Then visit: http://localhost:8000/chat

## 📁 Project Structure

```
app/
├── agents/                          # Agent system
│   ├── __init__.py                 # Agent exports
│   ├── base_agent.py               # Base agent class
│   ├── agent_orchestrator.py       # LangGraph orchestrator
│   └── agents/                     # Specialized agents
│       ├── code_agent.py           # Code generation
│       ├── diagram_agent.py        # Mermaid diagrams
│       ├── analysis_agent.py       # Data analysis
│       ├── document_agent.py       # Documentation
│       └── visualization_agent.py  # Charts & graphs
├── core/
│   ├── agent_config.py             # Agent configuration
│   └── logging_config.py           # Logging setup
├── api/routes/
│   └── chat_routes.py              # Chat API endpoints
└── main.py                         # FastAPI application

static/modules/chat/                 # Chat interface
├── chat.html                       # Main chat interface
├── css/chat.css                    # Styling
└── js/                             # JavaScript modules
    ├── chat-websocket.js           # WebSocket handling
    ├── chat-artifacts.js           # Artifact management
    └── ...                         # Other modules

demo_agents.py                       # Agent system demo
README_AGENTS.md                     # This file
```

## 🔄 Agent Workflow

### 1. Request Routing
```python
# User sends message
user_input = "Create a Python function to sort a list"

# Orchestrator analyzes request
agent_scores = {
    'code': 4,        # High score - keywords match
    'diagram': 2,     # Medium score - some keywords
    'document': 1     # Low score - minimal match
}

# Select top agents (configurable threshold)
selected_agents = ['code', 'diagram']
```

### 2. Parallel Execution
```python
# Execute agents in parallel
async def execute_agents():
    tasks = [
        code_agent.process_request(user_input),
        diagram_agent.process_request(user_input)
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. Response Combination
```python
# Combine successful responses
final_response = {
    'content': combined_content,
    'artifacts': all_artifacts,
    'metadata': {
        'agents_used': ['code', 'diagram'],
        'processing_time': 0.5
    }
}
```

## 🎨 Artifact Types

### Code Artifacts
```python
{
    "type": "code",
    "language": "python",
    "title": "Sorting Function",
    "content": "def sort_list(data): ..."
}
```

### Mermaid Diagrams
```python
{
    "type": "mermaid", 
    "title": "Process Flow",
    "content": "graph TD\n    A --> B\n    B --> C"
}
```

### Charts & Visualizations
```python
{
    "type": "chart",
    "chart_type": "bar",
    "data": {
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "datasets": [...]
    }
}
```

## 🛠️ Adding New Agents

### 1. Create Agent Class
```python
from app.agents.base_agent import BaseAgent, AgentCapability, ArtifactType

class CustomAgent(BaseAgent):
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Custom Capability",
                description="What this agent does",
                artifact_types=[ArtifactType.CODE],
                keywords=["custom", "special"],
                examples=["Create custom solution"]
            )
        ]
        super().__init__("Custom", capabilities)
    
    def get_system_prompt(self) -> str:
        return "You are a custom agent that..."
    
    def can_handle(self, user_input: str) -> bool:
        return "custom" in user_input.lower()
    
    async def process_request(self, user_input: str, context=None):
        # Implementation here
        pass
```

### 2. Register in Orchestrator
```python
# In agent_orchestrator.py
self.agents = {
    "code": CodeAgent(),
    "diagram": DiagramAgent(),
    "custom": CustomAgent(),  # Add your agent
    # ... other agents
}
```

## 📊 Performance Metrics

- **Response Time**: ~0.01s (mock) / ~1-3s (real API)
- **Parallel Processing**: Up to 2 agents simultaneously
- **Artifact Generation**: 12 artifacts in demo test
- **Success Rate**: 100% in demo mode
- **Cost**: ~$0.001-0.005 per request (GPT-4o mini)

## 🔌 API Endpoints

### Agent Capabilities
```bash
GET /api/v1/chat/agents/capabilities
```

### Agent Suggestions
```bash
POST /api/v1/chat/agents/suggestions
Content-Type: application/json

{
    "query": "I need help with Python programming"
}
```

### WebSocket Chat
```bash
WS /ws/chat
```

## 🧪 Testing

### Run Full Demo
```bash
python demo_agents.py
```

### Test Specific Agent
```python
from app.agents.agents.code_agent import CodeAgent

agent = CodeAgent()
response = await agent.process_request("Write a hello world function")
print(response.content)
```

### Benchmark Performance
```python
from app.agents import AgentOrchestrator

orchestrator = AgentOrchestrator()
# Runs 5 parallel requests and measures performance
```

## 🔧 Configuration Options

### Environment Variables
```bash
# OpenAI Configuration
OPENAI_API_KEY=""              # OpenAI API key
OPENAI_MODEL="gpt-4o-mini"     # Model to use
OPENAI_TEMPERATURE="0.7"       # Response creativity
OPENAI_MAX_TOKENS="4000"       # Max response length

# Agent System
AGENT_TIMEOUT="30"             # Request timeout (seconds)
AGENT_MAX_RETRIES="3"          # Retry attempts
AGENT_SELECTION_THRESHOLD="1.0" # Agent selection threshold
MAX_PARALLEL_AGENTS="2"        # Max concurrent agents
```

### Runtime Configuration
```python
from app.core.agent_config import get_openai_config, get_agent_config

openai_config = get_openai_config()
agent_config = get_agent_config()
```

## 🎯 Use Cases

### Code Generation
- **Request**: "Create a REST API with authentication"
- **Agents**: Code + Document
- **Artifacts**: Python code + API documentation

### System Design
- **Request**: "Design a microservices architecture"
- **Agents**: Diagram + Analysis + Document
- **Artifacts**: System diagram + analysis report + guide

### Data Analysis
- **Request**: "Analyze sales trends and create visualizations"
- **Agents**: Analysis + Visualization
- **Artifacts**: Analysis report + charts

### Documentation
- **Request**: "Write user guide with code examples"
- **Agents**: Document + Code
- **Artifacts**: Documentation + sample code

## 🚀 Future Enhancements

### Planned Features
- [ ] **Agent Memory**: Persistent context across conversations
- [ ] **Custom Tools**: Agent-specific tool integration
- [ ] **Multi-Modal**: Image and audio input support
- [ ] **Agent Marketplace**: Plugin system for third-party agents
- [ ] **Workflow Templates**: Pre-defined agent workflows
- [ ] **Performance Optimization**: Caching and response optimization

### Easy Extensions
- [ ] **Database Agent**: SQL generation and database operations
- [ ] **UI/UX Agent**: Frontend code and design generation
- [ ] **Testing Agent**: Unit test and integration test generation
- [ ] **Security Agent**: Security analysis and recommendations
- [ ] **API Agent**: API design and implementation

## 🎉 Demo Results

```
✅ Successful: 6/6 tests
⏱️  Average processing time: 0.01s
🎯 Total artifacts generated: 12
🤖 Agents Used: All 5 agents tested
📈 Requests per second: 178.81
💰 Cost: $0 (mock mode) / ~$0.03 (real API)
```

## 📝 License

This project is part of the Agentic RAG system and follows the same licensing terms.

---

**Ready to build with intelligent agents? Start with `python demo_agents.py` and explore the future of AI assistance!** 🚀 