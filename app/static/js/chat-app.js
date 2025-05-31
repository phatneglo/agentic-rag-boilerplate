import ChatMessages from './chat-messages.js';
import ChatArtifacts from './chat-artifacts.js';
import { scrollToBottom, showThinkingIndicator, hideThinkingIndicator } from './chat-utils.js';

class ChatApp {
    constructor() {
        this.chatMessages = new ChatMessages();
        this.chatArtifacts = new ChatArtifacts();
        this.websocket = null;
        this.isConnected = false;
        this.isSending = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.initializeElements();
        this.setupEventListeners();
        this.connectWebSocket();
    }

    initializeElements() {
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-button');
        this.messagesContainer = document.getElementById('chat-messages');
        this.artifactsPanel = document.getElementById('artifacts-panel');
        this.connectionStatus = document.getElementById('connection-status');
    }

    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });

        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.addEventListener('open', () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
            });

            this.websocket.addEventListener('message', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            });

            this.websocket.addEventListener('close', () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.handleReconnect();
            });

            this.websocket.addEventListener('error', (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('error');
            });

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.updateConnectionStatus('error');
        }
    }

    handleWebSocketMessage(data) {
        console.log('WebSocket message received:', data.type, data);
        
        switch (data.type) {
            case 'agent_thinking':
                this.chatMessages.handleAgentThinking(data);
                break;
                
            case 'agent_content_chunk':
                this.chatMessages.handleAgentContentChunk(data);
                break;
                
            case 'agent_artifact_start':
                this.chatMessages.handleAgentArtifactStart(data);
                this.showArtifacts();
                break;
                
            case 'agent_artifact_chunk':
                this.chatMessages.handleAgentArtifactChunk(data);
                break;
                
            case 'agent_error':
                this.chatMessages.handleAgentError(data);
                break;
                
            case 'response_start':
                this.chatMessages.startAssistantMessage();
                break;
                
            case 'response_complete':
                this.chatMessages.completeAssistantMessage(data);
                this.hideThinkingIndicator();
                this.setSendButtonState(false);
                break;
                
            case 'response_error':
                this.chatMessages.addErrorMessage(data.content || data.error || 'An error occurred');
                this.hideThinkingIndicator();
                this.setSendButtonState(false);
                break;
                
            case 'generation_stopped':
                this.chatMessages.completeAssistantMessage(data);
                this.hideThinkingIndicator();
                this.setSendButtonState(false);
                break;
                
            case 'pong':
                console.log('Received pong');
                break;
                
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    handleSendMessage() {
        if (this.isSending || !this.isConnected) return;

        const content = this.chatInput.value.trim();
        if (!content) return;

        // Add user message to chat
        this.chatMessages.addUserMessage(content);
        
        // Clear input
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';

        // Set sending state
        this.setSendButtonState(true);
        this.showThinkingIndicator();

        // Send message via WebSocket
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'chat_message',
                content: content
            }));
        }
    }

    handleStopGeneration() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'stop_generation'
            }));
        }
        this.setSendButtonState(false);
        this.hideThinkingIndicator();
    }

    setSendButtonState(isSending) {
        this.isSending = isSending;
        
        if (isSending) {
            this.sendButton.innerHTML = '⏹️';
            this.sendButton.title = 'Stop generation';
            this.sendButton.classList.add('stop-button');
            this.sendButton.onclick = () => this.handleStopGeneration();
        } else {
            this.sendButton.innerHTML = '→';
            this.sendButton.title = 'Send message';
            this.sendButton.classList.remove('stop-button');
            this.sendButton.onclick = () => this.handleSendMessage();
        }
    }

    showThinkingIndicator() {
        showThinkingIndicator();
    }

    hideThinkingIndicator() {
        hideThinkingIndicator();
    }

    showArtifacts() {
        if (this.artifactsPanel) {
            this.artifactsPanel.style.display = 'block';
        }
    }

    hideArtifacts() {
        if (this.artifactsPanel) {
            this.artifactsPanel.style.display = 'none';
        }
    }

    updateConnectionStatus(status) {
        if (!this.connectionStatus) return;
        
        this.connectionStatus.className = `connection-status ${status}`;
        
        const statusText = {
            'connected': '🟢 Connected',
            'disconnected': '🔴 Disconnected',
            'connecting': '🟡 Connecting...',
            'error': '🔴 Connection Error'
        };
        
        this.connectionStatus.textContent = statusText[status] || status;
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateConnectionStatus('connecting');
            
            setTimeout(() => {
                console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
                this.connectWebSocket();
            }, 2000 * this.reconnectAttempts);
        }
    }
}

// Initialize the chat app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
}); 