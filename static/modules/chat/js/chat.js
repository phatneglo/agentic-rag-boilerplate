/**
 * Multi-Agent Chat System - JavaScript Module
 * Vanilla JavaScript implementation for WebSocket chat functionality
 */

class ChatSystem {
    constructor() {
        this.websocket = null;
        this.sessionId = this.generateSessionId();
        this.messageCount = 0;
        this.currentAgent = 'None';
        this.isConnected = false;
        this.isTyping = false;
        
        // DOM elements
        this.elements = {
            chatContainer: document.getElementById('chatContainer'),
            messagesContainer: document.getElementById('messagesContainer'),
            loadingScreen: document.getElementById('loadingScreen'),
            typingIndicator: document.getElementById('typingIndicator'),
            messageInput: document.getElementById('messageInput'),
            sendButton: document.getElementById('sendButton'),
            connectionStatus: document.getElementById('connectionStatus'),
            sessionInfo: document.getElementById('sessionInfo'),
            sidebarStatus: document.getElementById('sidebarStatus'),
            sidebarSession: document.getElementById('sidebarSession'),
            messageCount: document.getElementById('messageCount'),
            currentAgent: document.getElementById('currentAgent'),
            activityLog: document.getElementById('activityLog'),
            typingText: document.getElementById('typingText')
        };
        
        this.init();
    }

    generateSessionId() {
        return 'chat_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    init() {
        this.setupEventListeners();
        this.connect();
    }

    setupEventListeners() {
        // Send button click
        this.elements.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });

        // Enter key press
        this.elements.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Window beforeunload
        window.addEventListener('beforeunload', () => {
            if (this.websocket) {
                this.websocket.close();
            }
        });
    }

    connect() {
        try {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/chat/ws/${this.sessionId}`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                this.onWebSocketOpen(event);
            };
            
            this.websocket.onmessage = (event) => {
                this.onWebSocketMessage(event);
            };
            
            this.websocket.onclose = (event) => {
                this.onWebSocketClose(event);
            };
            
            this.websocket.onerror = (event) => {
                this.onWebSocketError(event);
            };
            
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.showConnectionError('Failed to establish WebSocket connection');
        }
    }

    onWebSocketOpen(event) {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.updateConnectionStatus('connected');
        this.updateSessionInfo();
        this.enableInput();
        this.logActivity('Connected', 'WebSocket connection established');
        
        // Hide loading screen and show messages container
        this.elements.loadingScreen.classList.add('d-none');
        this.elements.messagesContainer.classList.remove('d-none');
    }

    onWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.handleChatEvent(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    onWebSocketClose(event) {
        console.log('WebSocket disconnected');
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');
        this.disableInput();
        this.hideTyping();
        this.logActivity('Disconnected', 'WebSocket connection closed');
    }

    onWebSocketError(event) {
        console.error('WebSocket error:', event);
        this.showConnectionError('WebSocket connection error');
    }

    handleChatEvent(data) {
        console.log('Chat event received:', data);
        
        const { event_type, content, user, tool, mode, timestamp } = data;
        
        switch (event_type) {
            case 'system_ready':
                this.addMessage(content, 'system-message', 'System', timestamp);
                this.logActivity('System', 'Chat system ready');
                break;
                
            case 'processing_start':
                this.showTyping('Processing your request...');
                this.logActivity('Processing', 'Started processing message');
                break;
                
            case 'agent_switch':
                this.currentAgent = user;
                this.updateCurrentAgent(user);
                this.updateTyping(`${user} is thinking...`);
                this.logActivity('Agent Switch', `${user} is now handling the request`);
                break;
                
            case 'tool_call':
                this.updateTyping(`${user} is using ${tool}...`);
                this.logActivity('Tool Call', `${user} is using ${tool}`);
                break;
                
            case 'tool_result':
                this.hideTyping();
                this.addToolResultMessage(content, user, timestamp);
                this.logActivity('Tool Result', 'Search results received');
                break;
                
            case 'agent_response':
                this.hideTyping();
                this.addMessage(content, 'agent-message', user, timestamp);
                this.logActivity('Response', `${user} responded`);
                break;
                
            case 'stream_token':
                // Handle real-time streaming if needed
                break;
                
            case 'processing_complete':
                this.hideTyping();
                this.logActivity('Complete', 'Processing completed');
                break;
                
            case 'error':
                this.hideTyping();
                this.addMessage(content, 'error-message', 'Error', timestamp);
                this.logActivity('Error', 'An error occurred');
                break;
                
            default:
                if (mode === 'thinking') {
                    this.updateTyping(content);
                } else if (mode === 'output') {
                    this.hideTyping();
                    this.addMessage(content, 'agent-message', user, timestamp);
                }
        }
    }

    sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || !this.isConnected) return;

        // Add user message to chat
        this.addMessage(message, 'user-message', 'You');
        
        // Send to WebSocket
        this.websocket.send(JSON.stringify({ message: message }));
        
        // Clear input
        this.elements.messageInput.value = '';
        
        // Update message count
        this.messageCount++;
        this.elements.messageCount.textContent = this.messageCount;
        
        this.logActivity('Sent', `Message sent: "${message.substring(0, 30)}..."`);
    }

    addMessage(content, className, agentName, timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${className}`;
        
        const time = timestamp ? 
            new Date(timestamp).toLocaleTimeString() : 
            new Date().toLocaleTimeString();
        
        // Get agent icon
        const icon = this.getAgentIcon(agentName);
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <i class="${icon}"></i>
                <span class="agent-name ${agentName.replace(' ', '')}">${agentName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-content">
                ${this.formatMessageContent(content, className)}
            </div>
        `;
        
        this.elements.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Update message count
        this.messageCount++;
        this.elements.messageCount.textContent = this.messageCount;
    }

    addToolResultMessage(content, agentName, timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message tool-result-message';
        
        const time = timestamp ? 
            new Date(timestamp).toLocaleTimeString() : 
            new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <i class="bi bi-search"></i>
                <span class="agent-name ${agentName.replace(' ', '')}">${agentName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-content search-results">
                <div class="search-header">🔍 Search Results</div>
                ${this.formatSearchResults(content)}
            </div>
        `;
        
        this.elements.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Update message count
        this.messageCount++;
        this.elements.messageCount.textContent = this.messageCount;
    }

    formatMessageContent(content, className) {
        if (className === 'tool-result-message') {
            return `<pre>${this.escapeHtml(content)}</pre>`;
        }
        
        // Convert newlines to <br> and escape HTML
        return this.escapeHtml(content).replace(/\n/g, '<br>');
    }

    formatSearchResults(content) {
        // Format search results for better display
        if (content.includes('🎯 Found') && content.includes('documents for')) {
            const lines = content.split('\n');
            let formatted = '';
            
            for (const line of lines) {
                if (line.trim()) {
                    if (line.startsWith('🎯')) {
                        formatted += `<div class="search-header">${this.escapeHtml(line)}</div>`;
                    } else if (line.startsWith('📄')) {
                        formatted += `<div class="document-item">`;
                        formatted += `<div class="document-title">${this.escapeHtml(line)}</div>`;
                    } else if (line.startsWith('   •')) {
                        formatted += `<div class="document-meta">${this.escapeHtml(line)}</div>`;
                    } else if (line.trim() && !line.startsWith('--')) {
                        formatted += `<div>${this.escapeHtml(line)}</div>`;
                    }
                    
                    if (line.includes('Document ID:')) {
                        formatted += `</div>`;
                    }
                }
            }
            
            return formatted;
        }
        
        return `<pre>${this.escapeHtml(content)}</pre>`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getAgentIcon(agentName) {
        const icons = {
            'You': 'bi bi-person-fill',
            'System': 'bi bi-gear-fill',
            'ChatAgent': 'bi bi-chat-dots-fill',
            'KnowledgeBaseAgent': 'bi bi-search',
            'Error': 'bi bi-exclamation-triangle-fill'
        };
        return icons[agentName] || 'bi bi-robot';
    }

    showTyping(message) {
        this.isTyping = true;
        this.elements.typingText.textContent = message;
        this.elements.typingIndicator.classList.remove('d-none');
        this.scrollToBottom();
    }

    updateTyping(message) {
        if (this.isTyping) {
            this.elements.typingText.textContent = message;
        }
    }

    hideTyping() {
        this.isTyping = false;
        this.elements.typingIndicator.classList.add('d-none');
    }

    updateConnectionStatus(status) {
        const statusElement = this.elements.connectionStatus;
        const sidebarStatusElement = this.elements.sidebarStatus;
        
        if (status === 'connected') {
            statusElement.innerHTML = '<i class="bi bi-circle-fill text-success"></i> Connected';
            statusElement.className = 'badge bg-light text-dark me-2';
            sidebarStatusElement.className = 'badge bg-success';
            sidebarStatusElement.textContent = 'Connected';
        } else {
            statusElement.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Disconnected';
            statusElement.className = 'badge bg-light text-dark me-2';
            sidebarStatusElement.className = 'badge bg-danger';
            sidebarStatusElement.textContent = 'Disconnected';
        }
    }

    updateSessionInfo() {
        const shortSessionId = this.sessionId.substring(this.sessionId.length - 8);
        this.elements.sessionInfo.textContent = `Session: ${shortSessionId}`;
        this.elements.sidebarSession.textContent = shortSessionId;
    }

    updateCurrentAgent(agentName) {
        this.currentAgent = agentName;
        const badgeClass = agentName === 'ChatAgent' ? 'bg-success' : 
                          agentName === 'KnowledgeBaseAgent' ? 'bg-warning' : 'bg-secondary';
        
        this.elements.currentAgent.className = `badge ${badgeClass}`;
        this.elements.currentAgent.textContent = agentName;
    }

    enableInput() {
        this.elements.messageInput.disabled = false;
        this.elements.sendButton.disabled = false;
        this.elements.messageInput.focus();
    }

    disableInput() {
        this.elements.messageInput.disabled = true;
        this.elements.sendButton.disabled = true;
    }

    scrollToBottom() {
        const container = this.elements.chatContainer;
        container.scrollTop = container.scrollHeight;
    }

    logActivity(type, message) {
        const activityLog = this.elements.activityLog;
        const time = new Date().toLocaleTimeString();
        
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <span class="activity-time">${time}</span>
            <span class="activity-text">${type}: ${message}</span>
        `;
        
        // Keep only last 10 activities
        while (activityLog.children.length >= 10) {
            activityLog.removeChild(activityLog.firstChild);
        }
        
        activityLog.appendChild(activityItem);
    }

    showConnectionError(message) {
        this.elements.loadingScreen.innerHTML = `
            <div class="text-center">
                <div class="text-danger mb-3">
                    <i class="bi bi-exclamation-triangle-fill" style="font-size: 3rem;"></i>
                </div>
                <h5 class="text-danger">Connection Error</h5>
                <p class="text-muted">${message}</p>
                <button class="btn btn-primary" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise"></i>
                    Retry Connection
                </button>
            </div>
        `;
    }
}

// Global functions for quick actions
function sendQuickMessage(message) {
    if (window.chatSystem && window.chatSystem.isConnected) {
        window.chatSystem.elements.messageInput.value = message;
        window.chatSystem.sendMessage();
    }
}

function clearChat() {
    if (window.chatSystem) {
        const container = window.chatSystem.elements.messagesContainer;
        container.innerHTML = '';
        window.chatSystem.messageCount = 0;
        window.chatSystem.elements.messageCount.textContent = '0';
        window.chatSystem.logActivity('Clear', 'Chat history cleared');
    }
}

// Initialize chat system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chatSystem = new ChatSystem();
}); 