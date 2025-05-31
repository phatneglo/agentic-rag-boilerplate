/**
 * Chat WebSocket Module
 * Handles real-time communication between client and AI service
 */

class ChatWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnecting = false;
        this.messageQueue = [];
        this.listeners = new Map();
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.handleOpen = this.handleOpen.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleError = this.handleError.bind(this);
        this.handleClose = this.handleClose.bind(this);
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        this.isConnecting = true;
        
        try {
            // Real WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
            
            console.log('Connecting to WebSocket:', wsUrl);
            
            // Use real WebSocket implementation
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = this.handleOpen;
            this.ws.onmessage = this.handleMessage;
            this.ws.onerror = this.handleError;
            this.ws.onclose = this.handleClose;
            
            // Set a timeout to fallback to mock if connection fails
            this.connectionTimeout = setTimeout(() => {
                if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
                    console.warn('WebSocket connection timeout, falling back to mock mode');
                    this.ws.close();
                    this.useMockWebSocket();
                }
            }, 5000); // 5 second timeout
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.handleConnectionError();
        }
    }

    /**
     * Use mock WebSocket when real connection fails
     */
    useMockWebSocket() {
        console.log('Using mock WebSocket for development');
        this.ws = this.createMockWebSocket();
        this.ws.onopen = this.handleOpen;
        this.ws.onmessage = this.handleMessage;
        this.ws.onerror = this.handleError;
        this.ws.onclose = this.handleClose;
    }

    /**
     * Create a mock WebSocket for development
     */
    createMockWebSocket() {
        const mockWs = {
            readyState: WebSocket.CONNECTING,
            onopen: null,
            onmessage: null,
            onerror: null,
            onclose: null,
            send: (data) => {
                console.log('Mock WebSocket sending:', data);
                this.handleMockMessage(JSON.parse(data));
            },
            close: () => {
                this.readyState = WebSocket.CLOSED;
                if (this.onclose) this.onclose();
            }
        };

        // Simulate connection opening
        setTimeout(() => {
            mockWs.readyState = WebSocket.OPEN;
            if (mockWs.onopen) mockWs.onopen();
        }, 500);

        return mockWs;
    }

    /**
     * Handle mock messages for development
     */
    handleMockMessage(message) {
        setTimeout(() => {
            let response;
            
            if (message.type === 'chat_message') {
                response = this.generateMockResponse(message.content);
            } else if (message.type === 'ping') {
                response = { type: 'pong', timestamp: Date.now() };
            }
            
            if (response && this.ws.onmessage) {
                this.ws.onmessage({
                    data: JSON.stringify(response)
                });
            }
        }, 1000 + Math.random() * 2000); // Simulate response delay
    }

    /**
     * Generate mock response based on user message
     */
    generateMockResponse(userMessage) {
        const responses = [
            {
                type: 'chat_response',
                content: 'I understand you\'re asking about: "' + userMessage + '". Let me help you with that!',
                timestamp: Date.now(),
                artifacts: []
            },
            {
                type: 'chat_response',
                content: 'That\'s an interesting question! Here\'s what I think about "' + userMessage + '".',
                timestamp: Date.now(),
                artifacts: [
                    {
                        id: 'artifact_' + Date.now(),
                        type: 'code',
                        title: 'Python Example',
                        language: 'python',
                        content: `def fibonacci(n):
    """Generate fibonacci sequence"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Example usage
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")`,
                    }
                ]
            },
            {
                type: 'chat_response',
                content: 'Here\'s a comprehensive guide based on your request:',
                timestamp: Date.now(),
                artifacts: [
                    {
                        id: 'artifact_' + Date.now(),
                        type: 'markdown',
                        title: 'Getting Started Guide',
                        content: `# Getting Started Guide

## Overview
This guide will help you understand the basics and get started quickly.

### Key Features
- **Easy to use**: Simple and intuitive interface
- **Powerful**: Advanced functionality when you need it
- **Flexible**: Customizable to your needs

### Quick Start
1. First, install the required dependencies
2. Configure your settings
3. Run the application

\`\`\`bash
npm install
npm start
\`\`\`

> **Note**: Make sure you have Node.js installed before running these commands.

For more information, check the [documentation](https://example.com).`
                    }
                ]
            }
        ];
        
        // Check for specific keywords to generate appropriate responses
        const lowerMessage = userMessage.toLowerCase();
        
        if (lowerMessage.includes('code') || lowerMessage.includes('python') || lowerMessage.includes('function')) {
            return responses[1]; // Response with code artifact
        }
        
        if (lowerMessage.includes('guide') || lowerMessage.includes('markdown') || lowerMessage.includes('documentation')) {
            return responses[2]; // Response with markdown artifact
        }
        
        if (lowerMessage.includes('diagram') || lowerMessage.includes('mermaid') || lowerMessage.includes('architecture')) {
            return {
                type: 'chat_response',
                content: 'I\'ll create a diagram to visualize this for you.',
                timestamp: Date.now(),
                artifacts: [
                    {
                        id: 'artifact_' + Date.now(),
                        type: 'mermaid',
                        title: 'System Architecture Diagram',
                        content: `graph TD
    A[User Interface] --> B[API Gateway]
    B --> C[Authentication Service]
    B --> D[Business Logic]
    C --> E[User Database]
    D --> F[Main Database]
    D --> G[Cache Layer]
    F --> H[Analytics Engine]
    G --> I[Session Store]`
                    }
                ]
            };
        }
        
        if (lowerMessage.includes('flowchart') || lowerMessage.includes('process') || lowerMessage.includes('workflow')) {
            return {
                type: 'chat_response',
                content: 'Here\'s a flowchart showing the process:',
                timestamp: Date.now(),
                artifacts: [
                    {
                        id: 'artifact_' + Date.now(),
                        type: 'mermaid',
                        title: 'Process Flowchart',
                        content: `flowchart LR
    Start([Start]) --> Input[Get User Input]
    Input --> Process{Process Data}
    Process -->|Valid| Success[Success]
    Process -->|Invalid| Error[Show Error]
    Error --> Input
    Success --> End([End])`
                    }
                ]
            };
        }
        
        return responses[0]; // Default response
    }

    /**
     * Handle WebSocket connection opened
     */
    handleOpen() {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        
        // Clear connection timeout if set
        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
        }
        
        // Process queued messages
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
        
        this.emit('connected');
        
        // Start heartbeat
        this.startHeartbeat();
    }

    /**
     * Handle WebSocket message received
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('WebSocket message received:', message);
            
            switch (message.type) {
                // Legacy message types (keep for compatibility)
                case 'chat_response':
                    this.emit('chat_response', message);
                    break;
                case 'typing_start':
                    this.emit('typing_start');
                    break;
                case 'typing_stop':
                    this.emit('typing_stop');
                    break;
                    
                // New streaming message types
                case 'response_start':
                    this.emit('response_start', message);
                    break;
                case 'agent_thinking':
                    this.emit('agent_thinking', message);
                    break;
                case 'agent_streaming':
                    this.emit('agent_streaming', message);
                    break;
                case 'response_complete':
                    this.emit('response_complete', message);
                    break;
                case 'agent_error':
                    this.emit('agent_error', message);
                    break;
                    
                // System messages
                case 'error':
                    this.emit('error', message);
                    break;
                case 'pong':
                    this.emit('pong', message);
                    break;
                    
                default:
                    console.warn('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    /**
     * Handle WebSocket error
     */
    handleError(error) {
        console.error('WebSocket error:', error);
        this.emit('error', { message: 'Connection error occurred' });
    }

    /**
     * Handle WebSocket connection closed
     */
    handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        this.isConnecting = false;
        this.stopHeartbeat();
        
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
        } else {
            this.emit('disconnected', { 
                code: event.code, 
                reason: event.reason,
                canReconnect: this.reconnectAttempts < this.maxReconnectAttempts 
            });
        }
    }

    /**
     * Handle connection error
     */
    handleConnectionError() {
        this.isConnecting = false;
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
        } else {
            console.warn('Max reconnection attempts reached, falling back to mock WebSocket');
            this.useMockWebSocket();
        }
    }

    /**
     * Attempt to reconnect
     */
    attemptReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Send message through WebSocket
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.log('WebSocket not connected, queuing message');
            this.messageQueue.push(message);
            
            if (!this.isConnecting) {
                this.connect();
            }
        }
    }

    /**
     * Send chat message
     */
    sendChatMessage(content, attachments = []) {
        const message = {
            type: 'chat_message',
            content: content,
            attachments: attachments,
            timestamp: Date.now()
        };
        
        this.send(message);
    }

    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.stopHeartbeat();
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'ping', timestamp: Date.now() });
            }
        }, 30000); // 30 seconds
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Add event listener
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    /**
     * Remove event listener
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Emit event
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Get connection status
     */
    getStatus() {
        if (!this.ws) return 'disconnected';
        
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'disconnected';
            default:
                return 'unknown';
        }
    }

    /**
     * Close WebSocket connection
     */
    close() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close(1000, 'Client closing connection');
        }
    }

    /**
     * Reconnect manually
     */
    reconnect() {
        this.close();
        this.reconnectAttempts = 0;
        setTimeout(() => this.connect(), 100);
    }
}

// Export for use in other modules
window.ChatWebSocket = ChatWebSocket; 