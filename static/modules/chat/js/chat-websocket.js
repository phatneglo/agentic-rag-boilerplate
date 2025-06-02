/**
 * Chat WebSocket Module
 * Handles real-time communication between client and AI service with enhanced memory support
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
        
        // Enhanced memory state
        this.currentSessionId = null;
        this.userId = null;
        this.memoryLoaded = false;
        this.sessionHistory = [];
        
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
            
            console.log('🔗 Connecting to WebSocket:', wsUrl);
            
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
     * Initialize or load a chat session
     */
    async initializeSession(sessionId = null, userId = null, config = {}) {
        console.log('🧠 MEMORY: Initializing session...', { sessionId, userId });
        
        this.userId = userId;
        
        const message = {
            type: 'init_session',
            session_id: sessionId,
            user_id: userId,
            config: config,
            timestamp: Date.now()
        };
        
        this.send(message);
    }

    /**
     * Load conversation history for a session
     */
    async loadSessionHistory(sessionId) {
        console.log('📚 MEMORY: Loading session history...', sessionId);
        
        const message = {
            type: 'load_session',
            session_id: sessionId,
            timestamp: Date.now()
        };
        
        this.send(message);
    }

    /**
     * Get current session information
     */
    async getSessionInfo() {
        const message = {
            type: 'get_session_info',
            timestamp: Date.now()
        };
        
        this.send(message);
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
            } else if (message.type === 'init_session') {
                // Mock session initialization
                response = {
                    type: 'session_initialized',
                    session_id: 'mock-session-' + Date.now(),
                    user_id: message.user_id || 'mock-user',
                    timestamp: Date.now()
                };
            } else if (message.type === 'load_session') {
                // Mock session history
                response = {
                    type: 'session_history',
                    session_id: message.session_id,
                    history: [
                        { type: 'human', content: 'Hello! Can you help me?', timestamp: Date.now() - 60000 },
                        { type: 'ai', content: 'Of course! I\'d be happy to help you.', timestamp: Date.now() - 59000 }
                    ],
                    stats: { total_messages: 2, total_tokens: 150 },
                    timestamp: Date.now()
                };
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
                artifacts: [],
                memory: {
                    session_id: this.currentSessionId || 'mock-session-' + Date.now(),
                    memory_loaded: true,
                    message_count: (this.sessionHistory.length + 2), // +2 for current exchange
                    primary_agent: 'general'
                }
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
                ],
                memory: {
                    session_id: this.currentSessionId || 'mock-session-' + Date.now(),
                    memory_loaded: true,
                    message_count: (this.sessionHistory.length + 2),
                    primary_agent: 'code'
                }
            }
        ];
        
        // Check for specific keywords to generate appropriate responses
        const lowerMessage = userMessage.toLowerCase();
        
        if (lowerMessage.includes('code') || lowerMessage.includes('python') || lowerMessage.includes('function')) {
            return responses[1]; // Response with code artifact
        }
        
        return responses[0]; // Default response
    }

    /**
     * Handle WebSocket connection opened
     */
    handleOpen() {
        console.log('✅ WebSocket connected successfully');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        
        // Clear connection timeout
        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
        }
        
        // Process queued messages
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.ws.send(JSON.stringify(message));
        }
        
        // Start heartbeat
        this.startHeartbeat();
        
        // Emit connected event
        this.emit('connected', { timestamp: Date.now() });
        
        // Auto-initialize session if none exists
        if (!this.currentSessionId) {
            setTimeout(() => {
                this.initializeSession(null, this.userId);
            }, 500);
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('📨 Received message:', message.type, message);
            
            switch (message.type) {
                case 'session_initialized':
                    this.handleSessionInitialized(message);
                    break;
                case 'session_history':
                    this.handleSessionHistory(message);
                    break;
                case 'session_info':
                    this.handleSessionInfo(message);
                    break;
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
                    this.handleResponseComplete(message);
                    break;
                case 'agent_error':
                    this.emit('agent_error', message);
                    break;
                case 'generation_stopped':
                    this.emit('generation_stopped', message);
                    break;
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
     * Handle session initialized
     */
    handleSessionInitialized(message) {
        this.currentSessionId = message.session_id;
        this.userId = message.user_id;
        this.memoryLoaded = false;
        
        console.log('🆕 MEMORY: Session initialized', {
            sessionId: this.currentSessionId,
            userId: this.userId
        });
        
        this.emit('session_initialized', {
            sessionId: this.currentSessionId,
            userId: this.userId,
            message: message
        });
    }

    /**
     * Handle session history loaded
     */
    handleSessionHistory(message) {
        this.sessionHistory = message.history || [];
        this.memoryLoaded = true;
        
        console.log('📚 MEMORY: Session history loaded', {
            sessionId: message.session_id,
            messageCount: this.sessionHistory.length,
            stats: message.stats
        });
        
        this.emit('session_history', {
            sessionId: message.session_id,
            history: this.sessionHistory,
            stats: message.stats,
            message: message
        });
    }

    /**
     * Handle session info
     */
    handleSessionInfo(message) {
        this.emit('session_info', message);
    }

    /**
     * Handle response complete with memory metadata
     */
    handleResponseComplete(message) {
        // Update local memory state if provided
        if (message.memory) {
            this.currentSessionId = message.memory.session_id || this.currentSessionId;
            this.memoryLoaded = message.memory.memory_loaded || this.memoryLoaded;
            
            console.log('💾 MEMORY: Response completed', {
                sessionId: this.currentSessionId,
                messageCount: message.memory.message_count,
                primaryAgent: message.memory.primary_agent
            });
        }
        
        this.emit('response_complete', message);
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
     * Send chat message with memory context
     */
    sendChatMessage(content, context = {}, attachments = []) {
        const message = {
            type: 'chat_message',
            content: content,
            session_id: this.currentSessionId,
            user_id: this.userId,
            context: context,
            attachments: attachments,
            timestamp: Date.now()
        };
        
        console.log('💬 Sending chat message with memory context', {
            sessionId: this.currentSessionId,
            userId: this.userId,
            contentLength: content.length
        });
        
        this.send(message);
    }

    /**
     * Stop message generation
     */
    stopGeneration() {
        const message = {
            type: 'stop_generation',
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
     * Get current memory state
     */
    getMemoryState() {
        return {
            sessionId: this.currentSessionId,
            userId: this.userId,
            memoryLoaded: this.memoryLoaded,
            historyLength: this.sessionHistory.length
        };
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