/**
 * Main Chat Application Module
 * Coordinates all chat modules and handles the main application logic
 */

class ChatApp {
    constructor() {
        this.wsManager = null;
        this.messagesManager = null;
        this.artifactsManager = null;
        this.serviceManager = null;
        
        // UI elements
        this.messageInput = null;
        this.sendBtn = null;
        this.attachmentBtn = null;
        this.characterCount = null;
        this.uploadArea = null;
        this.uploadFiles = null;
        
        // State
        this.currentFiles = [];
        this.isConnected = false;
        this.isTyping = false;
        this.isGenerating = false;
        this.currentRequestId = null;
        this.stopSignalSent = false;
        
        // Enhanced memory state
        this.currentSessionId = null;
        this.currentUserId = null;
        
        // Streaming state
        this.currentStreamingMessage = null;
        this.currentStreamingArtifacts = null;
        
        this.init();
    }

    /**
     * Initialize the chat application
     */
    async init() {
        console.log('Initializing ChatApp...');
        
        // Wait for dependencies to be available
        await this.waitForDependencies();
        
        // Initialize modules in order
        this.initializeComponents();
        this.setupEventListeners();
        this.setupStateManagement();
        
        console.log('ChatApp initialized successfully');
    }

    /**
     * Wait for dependencies to be available
     */
    async waitForDependencies() {
        const maxWait = 5000; // 5 seconds
        const checkInterval = 100; // 100ms
        let waited = 0;
        
        return new Promise((resolve) => {
            const checkDeps = () => {
                if (window.chatMessages && window.chatArtifacts && window.chatService) {
                    console.log('Dependencies ready');
                    resolve();
                } else if (waited >= maxWait) {
                    console.warn('Dependency timeout - proceeding anyway');
                    resolve();
                } else {
                    waited += checkInterval;
                    setTimeout(checkDeps, checkInterval);
                }
            };
            checkDeps();
        });
    }

    /**
     * Initialize components and dependencies
     */
    initializeComponents() {
        // Initialize managers
        this.wsManager = new ChatWebSocket();
        this.messagesManager = window.chatMessages;
        this.artifactsManager = window.chatArtifacts;
        this.serviceManager = window.chatService;
        
        if (!this.messagesManager || !this.artifactsManager || !this.serviceManager) {
            console.error('Failed to initialize chat dependencies');
            this.showNotification('Failed to initialize chat interface', 'error');
            return;
        }
        
        // Get UI elements
        this.initializeUIElements();
        
        // Connect WebSocket
        this.connectWebSocket();
    }

    /**
     * Initialize UI elements
     */
    initializeUIElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.attachmentBtn = document.getElementById('attachmentBtn');
        this.characterCount = document.getElementById('characterCount');
        this.uploadArea = document.getElementById('uploadArea');
        this.uploadFiles = document.getElementById('uploadFiles');
        
        if (!this.messageInput || !this.sendBtn) {
            console.error('Required UI elements not found');
            return false;
        }
        
        return true;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Send button
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => {
                if (this.isGenerating) {
                    this.stopGeneration();
                } else {
                    this.sendMessage();
                }
            });
        }

        // Message input
        if (this.messageInput) {
            this.messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!this.isGenerating) {
                        this.sendMessage();
                    }
                }
            });

            this.messageInput.addEventListener('input', () => {
                this.updateCharacterCount();
                this.adjustTextareaHeight();
                this.updateSendButton();
            });
        }

        // Attachment button
        if (this.attachmentBtn) {
            this.attachmentBtn.addEventListener('click', () => {
                this.openFileDialog();
            });
        }

        // WebSocket events - using the correct event system  
        if (this.wsManager) {
            this.wsManager.on('connected', () => {
                this.isConnected = true;
                this.updateConnectionStatus(true);
            });

            this.wsManager.on('disconnected', () => {
                this.isConnected = false;
                this.updateConnectionStatus(false);
            });

            // Enhanced memory system events
            this.wsManager.on('session_initialized', (data) => {
                this.handleSessionInitialized(data);
            });

            this.wsManager.on('session_history', (data) => {
                this.handleSessionHistory(data);
            });

            this.wsManager.on('session_info', (data) => {
                this.handleSessionInfo(data);
            });

            // Multi-agent streaming events
            this.wsManager.on('agent_thinking', (data) => {
                this.handleAgentThinking(data);
            });

            this.wsManager.on('agent_streaming', (data) => {
                this.handleContentChunk(data);  // Reuse existing content handler
            });

            this.wsManager.on('agent_content_chunk', (data) => {
                this.handleAgentContentChunk(data);
            });

            this.wsManager.on('agent_artifact_start', (data) => {
                this.handleAgentArtifactStart(data);
            });

            this.wsManager.on('agent_artifact_chunk', (data) => {
                this.handleAgentArtifactChunk(data);
            });

            this.wsManager.on('agent_error', (data) => {
                this.handleAgentError(data);
            });

            // Legacy streaming events (for backward compatibility)
            this.wsManager.on('thinking_status', (data) => {
                this.handleThinkingStatus(data);
            });

            this.wsManager.on('response_start', (data) => {
                this.handleResponseStart(data);
            });

            this.wsManager.on('content_chunk', (data) => {
                this.handleContentChunk(data);
            });

            this.wsManager.on('artifact_start', (data) => {
                this.handleArtifactStart(data);
            });

            this.wsManager.on('artifact_chunk', (data) => {
                this.handleArtifactChunk(data);
            });

            this.wsManager.on('response_complete', (data) => {
                this.handleResponseComplete(data);
            });

            this.wsManager.on('response_error', (data) => {
                this.handleResponseError(data);
            });

            this.wsManager.on('generation_stopped', (data) => {
                this.handleGenerationStopped(data);
            });

            // Fallback for non-streaming responses
            this.wsManager.on('chat_response', (data) => {
                this.handleChatResponse(data);
            });

            this.wsManager.on('error', (error) => {
                console.error('WebSocket error:', error);
                this.showError('Connection error. Please try again.');
            });
        }

        // Hidden file input event handler
        const hiddenFileInput = document.getElementById('hiddenFileInput');
        if (hiddenFileInput) {
            hiddenFileInput.addEventListener('change', (e) => {
                this.handleFileSelection(e);
            });
        }

        // Global events
        window.addEventListener('beforeunload', () => {
            if (this.wsManager) {
                this.wsManager.close();
            }
        });
    }

    /**
     * Setup state management
     */
    setupStateManagement() {
        this.isGenerating = false;
        this.currentRequestId = null;
    }

    /**
     * Connect WebSocket
     */
    connectWebSocket() {
        if (this.wsManager) {
            this.wsManager.connect();
        }
    }

    /**
     * Handle WebSocket connected
     */
    handleWSConnected() {
        this.isConnected = true;
        this.updateConnectionStatus(true);
        console.log('Chat connected');
    }

    /**
     * Handle WebSocket disconnected
     */
    handleWSDisconnected() {
        this.isConnected = false;
        this.updateConnectionStatus(false);
        console.log('Chat disconnected');
    }

    /**
     * Handle chat response from AI
     */
    handleChatResponse(data) {
        // Stop generation state
        this.stopGeneration();
        
        // Add AI response
        this.messagesManager.addAIMessage(data.content, data.artifacts || []);
        
        // Show artifacts if available
        if (data.artifacts && data.artifacts.length > 0) {
            // Auto-show first artifact
            setTimeout(() => {
                const firstArtifact = data.artifacts[0];
                if (firstArtifact && window.chatArtifacts) {
                    const artifact = window.chatArtifacts.createArtifact(firstArtifact);
                    window.chatArtifacts.showArtifact(artifact.id);
                }
            }, 500);
        }
        
        console.log('Received chat response:', data);
    }

    /**
     * Handle typing start
     */
    handleTypingStart() {
        this.messagesManager.showTypingIndicator();
    }

    /**
     * Handle typing stop
     */
    handleTypingStop() {
        this.messagesManager.hideTypingIndicator();
    }

    /**
     * Handle WebSocket error
     */
    handleWSError(error) {
        console.error('WebSocket error:', error);
        this.showNotification('Connection error occurred', 'error');
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(connected) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = statusIndicator?.querySelector('span')?.lastChild;
        
        if (statusIndicator) {
            if (connected) {
                statusIndicator.className = 'status-indicator online';
                if (statusText) statusText.textContent = ' Online';
            } else {
                statusIndicator.className = 'status-indicator offline';
                if (statusText) statusText.textContent = ' Offline';
            }
        }
    }

    /**
     * Handle input change
     */
    handleInputChange(e) {
        const value = e.target.value;
        const length = value.length;
        const maxLength = parseInt(e.target.getAttribute('maxlength')) || 8000;
        
        // Update character count
        if (this.characterCount) {
            this.characterCount.textContent = `${length}/${maxLength}`;
        }
        
        // Auto-resize textarea
        this.autoResizeTextarea(e.target);
        
        // Enable/disable send button
        this.updateSendButton();
    }

    /**
     * Handle key down events
     */
    handleKeyDown(e) {
        // Send on Ctrl+Enter or Cmd+Enter
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            this.handleSend();
        }
        
        // Prevent sending empty messages on Enter
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            if (this.messageInput.value.trim()) {
                this.handleSend();
            }
        }
    }

    /**
     * Handle paste events
     */
    handlePaste(e) {
        // Handle file paste
        const items = e.clipboardData?.items;
        if (items) {
            for (let item of items) {
                if (item.type.indexOf('image') !== -1) {
                    e.preventDefault();
                    const file = item.getAsFile();
                    if (file) {
                        this.addFile(file);
                    }
                }
            }
        }
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        if (!textarea) return;
        
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    /**
     * Update send button state and appearance
     */
    updateSendButton() {
        if (!this.sendBtn) return;
        
        const icon = this.sendBtn.querySelector('i');
        if (!icon) return;
        
        if (this.isGenerating) {
            // Change to stop button
            this.sendBtn.classList.add('btn-stop');
            this.sendBtn.title = 'Stop Generation';
            icon.className = 'fas fa-stop';
            this.sendBtn.disabled = false;
        } else {
            // Change to send button
            this.sendBtn.classList.remove('btn-stop');
            this.sendBtn.title = 'Send Message';
            icon.className = 'fas fa-paper-plane';
            
            // Enable/disable based on content
            const hasContent = this.messageInput?.value.trim().length > 0;
            const hasFiles = this.currentFiles.length > 0;
            this.sendBtn.disabled = !hasContent && !hasFiles;
        }
    }

    /**
     * Send message
     */
    async sendMessage() {
        if (!this.isConnected) {
            this.showError('Not connected to chat service. Please wait for connection.');
            return;
        }

        const content = this.messageInput.value.trim();
        if (!content && this.currentFiles.length === 0) {
            return;
        }

        try {
            // Start generation state
            this.startGeneration();
            
            // Add user message
            this.messagesManager.addUserMessage(content, this.currentFiles);
            
            // Clear input
            this.messageInput.value = '';
            this.currentFiles = [];
            this.updateCharacterCount();
            this.adjustTextareaHeight();
            this.hideUploadArea();
            
            // Send via WebSocket using enhanced memory system
            this.currentRequestId = this.generateRequestId();
            
            // Use the correct parameter order: content, context, attachments
            const context = {
                requestId: this.currentRequestId,
                timestamp: Date.now()
            };
            
            this.wsManager.sendChatMessage(content, context, this.currentFiles);
            
        } catch (error) {
            console.error('Send message error:', error);
            this.showError('Failed to send message. Please try again.');
            this.stopGeneration();
        }
    }

    /**
     * Start generation state
     */
    startGeneration() {
        this.isGenerating = true;
        this.updateSendButton();
        this.messagesManager.showTypingIndicator();
    }

    /**
     * Stop generation
     */
    stopGeneration() {
        if (!this.isGenerating) return;
        
        this.isGenerating = false;
        this.currentRequestId = null;
        this.updateSendButton();
        this.messagesManager.hideThinkingIndicator();
        
        // Send stop signal if connected (with debouncing)
        if (this.wsManager && this.isConnected && !this.stopSignalSent) {
            this.stopSignalSent = true;
            this.wsManager.send({
                type: 'stop_generation',
                requestId: this.currentRequestId,
                timestamp: Date.now()
            });
            
            // Reset flag after a short delay
            setTimeout(() => {
                this.stopSignalSent = false;
            }, 1000);
        }
    }

    /**
     * Handle attachment button click
     */
    handleAttachment() {
        const hiddenFileInput = document.getElementById('hiddenFileInput');
        if (hiddenFileInput) {
            hiddenFileInput.click();
        }
    }

    /**
     * Handle file selection from hidden input
     */
    handleFileSelection(e) {
        const files = Array.from(e.target.files);
        this.addFiles(files);
        e.target.value = ''; // Reset input
    }

    /**
     * Handle file selection from modal
     */
    handleModalFileSelection(e) {
        const files = Array.from(e.target.files);
        this.addFiles(files);
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
        if (modal) {
            modal.hide();
        }
    }

    /**
     * Handle file drop
     */
    handleFileDrop(e) {
        const files = Array.from(e.dataTransfer.files);
        this.addFiles(files);
    }

    /**
     * Add multiple files
     */
    addFiles(files) {
        files.forEach(file => this.addFile(file));
    }

    /**
     * Add single file
     */
    addFile(file) {
        try {
            // Basic file validation
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                throw new Error('File size too large (max 10MB)');
            }
            
            // Add to current files
            this.currentFiles.push(file);
            
            // Update UI
            this.updateFilesList();
            this.updateSendButton();
            
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    /**
     * Remove file
     */
    removeFile(index) {
        this.currentFiles.splice(index, 1);
        this.updateFilesList();
        this.updateSendButton();
    }

    /**
     * Update files list UI
     */
    updateFilesList() {
        if (!this.uploadFiles) return;
        
        if (this.currentFiles.length === 0) {
            this.uploadArea?.classList.add('d-none');
            this.uploadFiles.innerHTML = '';
            return;
        }
        
        this.uploadArea?.classList.remove('d-none');
        
        this.uploadFiles.innerHTML = this.currentFiles.map((file, index) => `
            <div class="uploaded-file">
                <i class="${this.getFileIcon(file)}"></i>
                <span class="file-name">${file.name}</span>
                <span class="file-size">${this.formatFileSize(file.size)}</span>
                <button type="button" class="remove-file" onclick="chatApp.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }

    /**
     * Get file icon
     */
    getFileIcon(file) {
        const type = file.type;
        if (type.startsWith('image/')) return 'fas fa-image';
        if (type.includes('pdf')) return 'fas fa-file-pdf';
        if (type.includes('text')) return 'fas fa-file-text';
        if (type.includes('json')) return 'fas fa-file-code';
        return 'fas fa-file';
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Clear input and reset state
     */
    clearInput() {
        if (this.messageInput) {
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
        }
        
        if (this.characterCount) {
            this.characterCount.textContent = '0/8000';
        }
        
        this.currentFiles = [];
        this.updateFilesList();
        this.updateSendButton();
    }

    /**
     * Start new chat
     */
    startNewChat() {
        this.messagesManager.clearMessages();
        this.clearInput();
        console.log('Started new chat');
    }

    /**
     * Show chat history
     */
    async showChatHistory() {
        try {
            const history = await this.serviceManager.listChatSessions();
            this.displayChatHistory(history.sessions || []);
        } catch (error) {
            console.error('Failed to load chat history:', error);
            this.showNotification('Failed to load chat history', 'error');
        }
    }

    /**
     * Display chat history in modal
     */
    displayChatHistory(sessions) {
        const historyList = document.getElementById('chatHistoryList');
        if (!historyList) return;
        
        if (sessions.length === 0) {
            historyList.innerHTML = '<p class="text-muted text-center">No chat history found</p>';
            return;
        }
        
        historyList.innerHTML = sessions.map(session => `
            <div class="chat-history-item" onclick="chatApp.loadChatSession('${session.id}')">
                <h6>${session.title}</h6>
                <p class="text-muted">${new Date(session.created).toLocaleDateString()}</p>
            </div>
        `).join('');
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('historyModal'));
        modal.show();
    }

    /**
     * Load chat session
     */
    async loadChatSession(sessionId) {
        try {
            const session = await this.serviceManager.loadChatSession(sessionId);
            
            // Clear current chat
            this.startNewChat();
            
            // Load messages
            session.messages.forEach(msg => {
                if (msg.type === 'user') {
                    this.messagesManager.addUserMessage(msg.content, msg.attachments || []);
                } else {
                    this.messagesManager.addAIMessage(msg.content, msg.artifacts || []);
                }
            });
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('historyModal'));
            if (modal) {
                modal.hide();
            }
            
        } catch (error) {
            console.error('Failed to load chat session:', error);
            this.showNotification('Failed to load chat session', 'error');
        }
    }

    /**
     * Show settings
     */
    showSettings() {
        // Implement settings modal
        console.log('Show settings');
    }

    /**
     * Show drop zone
     */
    showDropZone() {
        // Add visual indicator for drop zone
        document.body.classList.add('drag-over');
    }

    /**
     * Hide drop zone
     */
    hideDropZone() {
        document.body.classList.remove('drag-over');
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Simple notification implementation
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} fade-in`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 250px;
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Load user preferences
     */
    async loadUserPreferences() {
        try {
            const result = await this.serviceManager.getPreferences();
            if (result.success) {
                this.applyPreferences(result.preferences);
            }
        } catch (error) {
            console.warn('Failed to load user preferences:', error);
        }
    }

    /**
     * Apply user preferences
     */
    applyPreferences(preferences) {
        // Apply theme, language, etc.
        console.log('Applied preferences:', preferences);
    }

    /**
     * Send message (public method for external calls like suggestion cards)
     */
    sendMessageFromSuggestion(content) {
        if (this.messageInput && content) {
            this.messageInput.value = content;
            this.updateCharacterCount();
            this.adjustTextareaHeight();
            this.sendMessage();
        }
    }

    /**
     * Show error notification
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * Update character count
     */
    updateCharacterCount() {
        if (this.characterCount) {
            const length = this.messageInput.value.length;
            const maxLength = parseInt(this.messageInput.getAttribute('maxlength')) || 8000;
            this.characterCount.textContent = `${length}/${maxLength}`;
        }
    }

    /**
     * Adjust textarea height
     */
    adjustTextareaHeight() {
        this.autoResizeTextarea(this.messageInput);
    }

    /**
     * Hide upload area
     */
    hideUploadArea() {
        this.uploadArea?.classList.add('d-none');
    }

    /**
     * Open file dialog
     */
    openFileDialog() {
        const hiddenFileInput = document.getElementById('hiddenFileInput');
        if (hiddenFileInput) {
            hiddenFileInput.click();
        }
    }

    /**
     * Generate unique request ID
     */
    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Handle thinking status indicator
     */
    handleThinkingStatus(data) {
        this.messagesManager.showThinkingIndicator(data.status);
    }

    /**
     * Handle response start
     */
    handleResponseStart(data) {
        this.currentStreamingMessage = this.messagesManager.startStreamingMessage();
        this.currentStreamingArtifacts = new Map();
    }

    /**
     * Handle content chunk streaming
     */
    handleContentChunk(data) {
        // Initialize streaming message if not already started
        if (!this.currentStreamingMessage) {
            this.currentStreamingMessage = this.messagesManager.startStreamingMessage();
            this.currentStreamingArtifacts = new Map();
        }
        
        this.messagesManager.appendToStreamingMessage(
            this.currentStreamingMessage, 
            data.content, 
            data.is_final
        );
    }

    /**
     * Handle artifact start
     */
    handleArtifactStart(data) {
        const artifact = data.artifact;
        
        // Create artifact in the artifacts manager
        const createdArtifact = this.artifactsManager.createArtifact({
            id: artifact.id,
            type: artifact.type,
            title: artifact.title,
            content: "", // Will be streamed
        });
        
        // Store for streaming updates
        this.currentStreamingArtifacts.set(artifact.id, {
            artifact: createdArtifact,
            content: ""
        });
        
        // Add artifact button to current message
        if (this.currentStreamingMessage) {
            this.messagesManager.addArtifactToStreamingMessage(
                this.currentStreamingMessage,
                createdArtifact
            );
        }
        
        // Auto-show artifact for real-time viewing
        this.artifactsManager.showArtifact(artifact.id);
    }

    /**
     * Handle artifact chunk streaming
     */
    handleArtifactChunk(data) {
        const streamingArtifact = this.currentStreamingArtifacts.get(data.artifact_id);
        
        if (streamingArtifact) {
            // Append content
            streamingArtifact.content += data.content;
            
            // Update the artifact
            streamingArtifact.artifact.content = streamingArtifact.content;
            
            // Re-render the artifact in real-time
            this.artifactsManager.updateStreamingArtifact(data.artifact_id, streamingArtifact.content);
        }
    }

    /**
     * Handle response complete
     */
    handleResponseComplete(data) {
        // Handle memory metadata if present
        if (data.memory) {
            const { session_id, memory_loaded, message_count, primary_agent } = data.memory;
            console.log('💾 MEMORY: Response completed with metadata', {
                sessionId: session_id,
                memoryLoaded: memory_loaded,
                messageCount: message_count,
                primaryAgent: primary_agent
            });
            
            // Update session tracking
            this.currentSessionId = session_id;
        }
        
        // Finalize streaming message
        if (this.currentStreamingMessage) {
            this.messagesManager.finalizeStreamingMessage(this.currentStreamingMessage, data);
        }
        
        // Stop generation state
        this.stopGeneration();
        
        // Hide thinking indicator
        this.messagesManager.hideThinkingIndicator();
        
        // Clear streaming state
        this.currentStreamingMessage = null;
        this.currentStreamingArtifacts = null;
        
        console.log('Streaming response completed:', data);
    }

    /**
     * Handle response error
     */
    handleResponseError(data) {
        // Stop generation state
        this.stopGeneration();
        
        // Hide thinking indicator
        this.messagesManager.hideThinkingIndicator();
        
        // Show error message
        this.messagesManager.addAIMessage(data.content, []);
        
        // Clear streaming state
        this.currentStreamingMessage = null;
        this.currentStreamingArtifacts = null;
        
        console.error('Streaming response error:', data);
    }

    /**
     * Handle generation stopped
     */
    handleGenerationStopped(data) {
        this.stopGeneration();
        this.messagesManager.hideThinkingIndicator();
        
        // Clear streaming state
        this.currentStreamingMessage = null;
        this.currentStreamingArtifacts = null;
        
        console.log('Generation stopped by user');
    }

    /**
     * Handle agent thinking status
     */
    handleAgentThinking(data) {
        const { agent, status } = data;
        console.log(`Agent ${agent} thinking:`, status);
        
        // Show thinking indicator with agent info
        this.messagesManager.showAgentThinking(agent, status);
    }

    /**
     * Handle agent content chunk
     */
    handleAgentContentChunk(data) {
        const { agent, content, is_final } = data;
        console.log(`Agent ${agent} content chunk:`, content);
        
        // Start streaming message if not already started
        if (!this.currentStreamingMessage) {
            this.currentStreamingMessage = this.messagesManager.startStreamingMessage();
        }
        
        // Add agent content
        this.messagesManager.appendAgentContent(
            this.currentStreamingMessage,
            agent,
            content,
            is_final
        );
    }

    /**
     * Handle agent artifact start
     */
    handleAgentArtifactStart(data) {
        const { agent, artifact } = data;
        console.log(`Agent ${agent} starting artifact:`, artifact);
        
        // Create artifact with agent info
        const createdArtifact = this.artifactsManager.createArtifact({
            id: artifact.id,
            type: artifact.type,
            title: artifact.title,
            content: "",
            agent: agent
        });
        
        // Store for streaming updates
        if (!this.currentStreamingArtifacts) {
            this.currentStreamingArtifacts = new Map();
        }
        this.currentStreamingArtifacts.set(artifact.id, {
            artifact: createdArtifact,
            content: "",
            agent: agent
        });
        
        // Add artifact to current message
        if (this.currentStreamingMessage) {
            this.messagesManager.addAgentArtifact(
                this.currentStreamingMessage,
                agent,
                createdArtifact
            );
        }
        
        // Auto-show artifact for real-time viewing
        this.artifactsManager.showArtifact(artifact.id);
    }

    /**
     * Handle agent artifact chunk
     */
    handleAgentArtifactChunk(data) {
        const { agent, artifact_id, content, is_final } = data;
        console.log(`Agent ${agent} artifact chunk for ${artifact_id}`);
        
        const streamingArtifact = this.currentStreamingArtifacts?.get(artifact_id);
        
        if (streamingArtifact) {
            // Append content
            streamingArtifact.content += content;
            
            // Update the artifact
            streamingArtifact.artifact.content = streamingArtifact.content;
            
            // Re-render the artifact in real-time
            this.artifactsManager.updateStreamingArtifact(artifact_id, streamingArtifact.content);
            
            // Update in message view
            this.messagesManager.updateAgentArtifact(artifact_id, streamingArtifact.content, is_final);
        }
    }

    /**
     * Handle agent error
     */
    handleAgentError(data) {
        const { agent, error } = data;
        console.error(`Agent ${agent} error:`, error);
        
        // Show error in the UI
        this.messagesManager.showAgentError(agent, error);
        
        // Show notification
        this.showNotification(`${agent} Agent Error: ${error}`, 'error');
    }

    /**
     * Handle enhanced memory session initialized
     */
    handleSessionInitialized(data) {
        const { sessionId, userId } = data;
        console.log('🧠 MEMORY: Session initialized in UI', { sessionId, userId });
        
        // Update UI to show session info
        this.showNotification(`Chat session started (${sessionId.slice(0, 8)}...)`, 'success');
        
        // Store session info for potential future use
        this.currentSessionId = sessionId;
        this.currentUserId = userId;
    }

    /**
     * Handle session history loaded
     */
    handleSessionHistory(data) {
        const { sessionId, history, stats } = data;
        console.log('📚 MEMORY: Session history loaded in UI', { sessionId, messageCount: history.length, stats });
        
        // Clear current messages
        this.messagesManager.clearMessages();
        
        // Load history messages into the UI
        history.forEach(msg => {
            if (msg.type === 'human') {
                this.messagesManager.addUserMessage(msg.content, []);
            } else if (msg.type === 'ai') {
                this.messagesManager.addAIMessage(msg.content, []);
            }
        });
        
        // Show notification about loaded history
        this.showNotification(`Loaded ${history.length} messages from chat history`, 'info');
    }

    /**
     * Handle session info
     */
    handleSessionInfo(data) {
        console.log('📋 MEMORY: Session info received', data);
        
        // Update current session tracking
        if (data.session_id) {
            this.currentSessionId = data.session_id;
        }
        if (data.user_id) {
            this.currentUserId = data.user_id;
        }
    }
}

// Initialize chat app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});

// Export for use in other modules
window.ChatApp = ChatApp; 