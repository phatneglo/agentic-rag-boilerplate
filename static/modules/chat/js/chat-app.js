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
        
        this.init();
    }

    /**
     * Initialize the chat application
     */
    async init() {
        console.log('Initializing chat application...');
        
        // Wait for dependencies to be available
        await this.waitForDependencies();
        
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
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Load user preferences
        await this.loadUserPreferences();
        
        console.log('Chat application initialized successfully');
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
     * Initialize UI elements
     */
    initializeUIElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.attachmentBtn = document.getElementById('attachmentBtn');
        this.characterCount = document.getElementById('characterCount');
        this.uploadArea = document.getElementById('uploadArea');
        this.uploadFiles = document.getElementById('uploadFiles');
        
        // Status indicator
        this.statusIndicator = document.querySelector('.status-indicator');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Message input events
        if (this.messageInput) {
            this.messageInput.addEventListener('input', (e) => this.handleInputChange(e));
            this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
            this.messageInput.addEventListener('paste', (e) => this.handlePaste(e));
        }
        
        // Send button
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.handleSend());
        }
        
        // Attachment button
        if (this.attachmentBtn) {
            this.attachmentBtn.addEventListener('click', () => this.handleAttachment());
        }
        
        // File input (hidden)
        const hiddenFileInput = document.getElementById('hiddenFileInput');
        if (hiddenFileInput) {
            hiddenFileInput.addEventListener('change', (e) => this.handleFileSelection(e));
        }
        
        // New chat button
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.startNewChat());
        }
        
        // History button
        const historyBtn = document.getElementById('historyBtn');
        if (historyBtn) {
            historyBtn.addEventListener('click', () => this.showChatHistory());
        }
        
        // Settings button
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettings());
        }
        
        // Upload modal events
        this.setupUploadModalEvents();
        
        // Drag and drop
        this.setupDragAndDrop();
    }

    /**
     * Set up upload modal events
     */
    setupUploadModalEvents() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        
        if (uploadZone && fileInput) {
            uploadZone.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleModalFileSelection(e));
            
            // Drag and drop for upload zone
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });
            
            uploadZone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
            });
            
            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                this.handleFileDrop(e);
            });
        }
    }

    /**
     * Set up drag and drop for main chat area
     */
    setupDragAndDrop() {
        const chatContainer = document.querySelector('.chat-container');
        
        if (chatContainer) {
            chatContainer.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.showDropZone();
            });
            
            chatContainer.addEventListener('dragleave', (e) => {
                e.preventDefault();
                if (!chatContainer.contains(e.relatedTarget)) {
                    this.hideDropZone();
                }
            });
            
            chatContainer.addEventListener('drop', (e) => {
                e.preventDefault();
                this.hideDropZone();
                this.handleFileDrop(e);
            });
        }
    }

    /**
     * Connect WebSocket
     */
    connectWebSocket() {
        // Set up WebSocket event listeners
        this.wsManager.on('connected', () => this.handleWSConnected());
        this.wsManager.on('disconnected', () => this.handleWSDisconnected());
        this.wsManager.on('chat_response', (data) => this.handleChatResponse(data));
        this.wsManager.on('typing_start', () => this.handleTypingStart());
        this.wsManager.on('typing_stop', () => this.handleTypingStop());
        this.wsManager.on('error', (error) => this.handleWSError(error));
        
        // Connect
        this.wsManager.connect();
    }

    /**
     * Handle WebSocket connected
     */
    handleWSConnected() {
        this.isConnected = true;
        this.updateConnectionStatus('online');
        console.log('Chat connected');
    }

    /**
     * Handle WebSocket disconnected
     */
    handleWSDisconnected() {
        this.isConnected = false;
        this.updateConnectionStatus('offline');
        console.log('Chat disconnected');
    }

    /**
     * Handle chat response from AI
     */
    handleChatResponse(data) {
        // Hide typing indicator
        this.messagesManager.hideTypingIndicator();
        
        // Add AI message
        this.messagesManager.addAIMessage(data.content, data.artifacts || []);
        
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
    updateConnectionStatus(status) {
        if (this.statusIndicator) {
            this.statusIndicator.className = `status-indicator ${status}`;
            const text = this.statusIndicator.querySelector('span') || this.statusIndicator;
            text.innerHTML = `<i class="fas fa-circle"></i> ${status === 'online' ? 'Online' : 'Offline'}`;
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
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    /**
     * Update send button state
     */
    updateSendButton() {
        const hasContent = this.messageInput?.value.trim().length > 0;
        const hasFiles = this.currentFiles.length > 0;
        
        if (this.sendBtn) {
            // Enable send button if there's content or files
            // Don't block on connection status - let the WebSocket handle fallbacks
            this.sendBtn.disabled = !hasContent && !hasFiles;
        }
    }

    /**
     * Handle send message
     */
    async handleSend() {
        const content = this.messageInput?.value.trim();
        
        if (!content && this.currentFiles.length === 0) {
            return;
        }
        
        // Always try to send, even if connection status is uncertain
        // The WebSocket will fallback to mock mode if needed
        
        try {
            // Prepare attachments
            let attachments = [];
            if (this.currentFiles.length > 0) {
                const uploadResult = await this.serviceManager.uploadFiles(this.currentFiles);
                attachments = uploadResult.files;
            }
            
            // Add user message
            this.messagesManager.addUserMessage(content, attachments);
            
            // Send to AI service via WebSocket
            if (this.wsManager) {
                this.wsManager.sendChatMessage(content, attachments);
            } else {
                // Fallback to HTTP endpoint
                await this.serviceManager.sendMessage(content, attachments);
            }
            
            // Clear input
            this.clearInput();
            
            // Show typing indicator
            setTimeout(() => {
                this.messagesManager.showTypingIndicator();
            }, 500);
            
        } catch (error) {
            console.error('Send message error:', error);
            this.showNotification(`Failed to send message: ${error.message}`, 'error');
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
            // Validate file
            this.serviceManager.validateFile(file);
            
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
        return this.serviceManager.formatFileSize(bytes);
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
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} fade-in`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 250px;
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
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
     * Send message (public method for external calls)
     */
    sendMessage(content) {
        if (this.messageInput) {
            this.messageInput.value = content;
            this.handleSend();
        }
    }
}

// Initialize chat app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});

// Export for use in other modules
window.ChatApp = ChatApp; 