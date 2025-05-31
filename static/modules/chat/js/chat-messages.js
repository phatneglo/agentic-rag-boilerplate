/**
 * Chat Messages Module
 * Handles message display, formatting, and management
 */

class ChatMessages {
    constructor() {
        this.messages = [];
        this.messagesContainer = null;
        this.welcomeScreen = null;
        this.typingIndicator = null;
        
        this.init();
    }

    /**
     * Initialize messages system
     */
    init() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.setupEventListeners();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Suggestion cards click handlers
        const suggestionCards = document.querySelectorAll('.suggestion-card');
        suggestionCards.forEach(card => {
            card.addEventListener('click', () => {
                const suggestion = card.getAttribute('data-suggestion');
                if (suggestion && window.chatApp) {
                    window.chatApp.sendMessage(suggestion);
                }
            });
        });
    }

    /**
     * Add user message
     */
    addUserMessage(content, attachments = []) {
        const message = this.createMessage('user', content, attachments);
        this.addMessage(message);
        return message;
    }

    /**
     * Add AI message
     */
    addAIMessage(content, artifacts = []) {
        const message = this.createMessage('ai', content, [], artifacts);
        this.addMessage(message);
        return message;
    }

    /**
     * Create message object
     */
    createMessage(type, content, attachments = [], artifacts = []) {
        const message = {
            id: this.generateMessageId(),
            type: type,
            content: content,
            attachments: attachments,
            artifacts: artifacts,
            timestamp: new Date(),
            element: null
        };

        return message;
    }

    /**
     * Generate unique message ID
     */
    generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Add message to chat
     */
    addMessage(message) {
        this.messages.push(message);
        
        // Hide welcome screen if visible
        if (this.welcomeScreen && !this.welcomeScreen.classList.contains('d-none')) {
            this.welcomeScreen.classList.add('d-none');
        }
        
        // Render message
        const messageElement = this.renderMessage(message);
        message.element = messageElement;
        
        if (this.messagesContainer) {
            this.messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
        }
        
        return message;
    }

    /**
     * Render message HTML
     */
    renderMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.type} fade-in`;
        messageDiv.setAttribute('data-message-id', message.id);
        
        const avatar = this.createMessageAvatar(message);
        const content = this.createMessageContent(message);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        return messageDiv;
    }

    /**
     * Create message avatar
     */
    createMessageAvatar(message) {
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        if (message.type === 'user') {
            avatarDiv.innerHTML = '<i class="fas fa-user"></i>';
        } else {
            avatarDiv.innerHTML = '<i class="fas fa-robot"></i>';
        }
        
        return avatarDiv;
    }

    /**
     * Create message content
     */
    createMessageContent(message) {
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const bubble = this.createMessageBubble(message);
        const meta = this.createMessageMeta(message);
        
        contentDiv.appendChild(bubble);
        contentDiv.appendChild(meta);
        
        return contentDiv;
    }

    /**
     * Create message bubble
     */
    createMessageBubble(message) {
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        // Process message content (markdown, etc.)
        const processedContent = this.processMessageContent(message.content);
        bubbleDiv.innerHTML = processedContent;
        
        // Add attachments
        if (message.attachments && message.attachments.length > 0) {
            const attachmentsDiv = this.createAttachmentsDisplay(message.attachments);
            bubbleDiv.appendChild(attachmentsDiv);
        }
        
        // Add artifacts buttons
        if (message.artifacts && message.artifacts.length > 0) {
            const artifactsDiv = this.createArtifactsDisplay(message.artifacts);
            bubbleDiv.appendChild(artifactsDiv);
        }
        
        return bubbleDiv;
    }

    /**
     * Create message meta information
     */
    createMessageMeta(message) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';
        
        const timestamp = this.formatTimestamp(message.timestamp);
        metaDiv.innerHTML = `
            <span class="message-time">${timestamp}</span>
            ${message.type === 'ai' ? '<span class="message-status">AI</span>' : ''}
        `;
        
        return metaDiv;
    }

    /**
     * Process message content (basic markdown, links, etc.)
     */
    processMessageContent(content) {
        // Basic text processing
        let processed = this.escapeHtml(content);
        
        // Convert URLs to links
        processed = this.linkifyUrls(processed);
        
        // Basic markdown support
        processed = this.processBasicMarkdown(processed);
        
        // Convert newlines to <br>
        processed = processed.replace(/\n/g, '<br>');
        
        return processed;
    }

    /**
     * Convert URLs to clickable links
     */
    linkifyUrls(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    }

    /**
     * Process basic markdown
     */
    processBasicMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/~~(.*?)~~/g, '<del>$1</del>');
    }

    /**
     * Create attachments display
     */
    createAttachmentsDisplay(attachments) {
        const attachmentsDiv = document.createElement('div');
        attachmentsDiv.className = 'message-attachments';
        
        attachments.forEach(attachment => {
            const attachmentDiv = document.createElement('div');
            attachmentDiv.className = 'attachment-item';
            
            const icon = this.getAttachmentIcon(attachment.type);
            attachmentDiv.innerHTML = `
                <i class="${icon}"></i>
                <span class="attachment-name">${attachment.name}</span>
                <span class="attachment-size">${this.formatFileSize(attachment.size)}</span>
            `;
            
            attachmentsDiv.appendChild(attachmentDiv);
        });
        
        return attachmentsDiv;
    }

    /**
     * Create artifacts display
     */
    createArtifactsDisplay(artifacts) {
        const artifactsDiv = document.createElement('div');
        artifactsDiv.className = 'message-artifacts';
        
        artifacts.forEach(artifactData => {
            // Create artifact and get button HTML
            const artifact = window.chatArtifacts.createArtifact(artifactData);
            const buttonHtml = window.chatArtifacts.createArtifactButton(artifact);
            
            const buttonContainer = document.createElement('div');
            buttonContainer.innerHTML = buttonHtml;
            artifactsDiv.appendChild(buttonContainer.firstElementChild);
        });
        
        return artifactsDiv;
    }

    /**
     * Get icon for attachment type
     */
    getAttachmentIcon(type) {
        const icons = {
            'image': 'fas fa-image',
            'document': 'fas fa-file-alt',
            'pdf': 'fas fa-file-pdf',
            'text': 'fas fa-file-text',
            'code': 'fas fa-file-code',
            'archive': 'fas fa-file-archive',
            'video': 'fas fa-file-video',
            'audio': 'fas fa-file-audio'
        };
        
        return icons[type] || 'fas fa-file';
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
     * Format timestamp
     */
    formatTimestamp(date) {
        const now = new Date();
        const diff = now - date;
        
        // Less than 1 minute
        if (diff < 60000) {
            return 'Just now';
        }
        
        // Less than 1 hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        }
        
        // Less than 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        }
        
        // More than 24 hours
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.classList.remove('d-none');
            this.scrollToBottom();
        }
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.classList.add('d-none');
        }
    }

    /**
     * Update typing indicator text
     */
    updateTypingIndicator(text) {
        if (this.typingIndicator) {
            const textElement = this.typingIndicator.querySelector('.typing-text');
            if (textElement) {
                textElement.textContent = text;
            }
        }
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        if (this.messagesContainer) {
            setTimeout(() => {
                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
            }, 100);
        }
    }

    /**
     * Clear all messages
     */
    clearMessages() {
        this.messages = [];
        if (this.messagesContainer) {
            this.messagesContainer.innerHTML = '';
        }
        
        // Show welcome screen
        if (this.welcomeScreen) {
            this.welcomeScreen.classList.remove('d-none');
        }
        
        // Clear artifacts
        if (window.chatArtifacts) {
            window.chatArtifacts.clearArtifacts();
        }
    }

    /**
     * Get all messages
     */
    getAllMessages() {
        return this.messages;
    }

    /**
     * Get message by ID
     */
    getMessageById(messageId) {
        return this.messages.find(msg => msg.id === messageId);
    }

    /**
     * Remove message by ID
     */
    removeMessage(messageId) {
        const index = this.messages.findIndex(msg => msg.id === messageId);
        if (index > -1) {
            const message = this.messages[index];
            if (message.element && message.element.parentNode) {
                message.element.parentNode.removeChild(message.element);
            }
            this.messages.splice(index, 1);
        }
    }

    /**
     * Update message content
     */
    updateMessage(messageId, newContent) {
        const message = this.getMessageById(messageId);
        if (message) {
            message.content = newContent;
            message.timestamp = new Date();
            
            // Re-render the message
            if (message.element) {
                const newElement = this.renderMessage(message);
                message.element.parentNode.replaceChild(newElement, message.element);
                message.element = newElement;
            }
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Export chat history
     */
    exportChat(format = 'json') {
        const chatData = {
            messages: this.messages.map(msg => ({
                id: msg.id,
                type: msg.type,
                content: msg.content,
                attachments: msg.attachments,
                artifacts: msg.artifacts,
                timestamp: msg.timestamp.toISOString()
            })),
            exported: new Date().toISOString()
        };
        
        let content, filename, mimeType;
        
        switch (format) {
            case 'json':
                content = JSON.stringify(chatData, null, 2);
                filename = `chat_export_${new Date().toISOString().split('T')[0]}.json`;
                mimeType = 'application/json';
                break;
            case 'txt':
                content = this.formatChatAsText(chatData.messages);
                filename = `chat_export_${new Date().toISOString().split('T')[0]}.txt`;
                mimeType = 'text/plain';
                break;
            default:
                throw new Error('Unsupported export format');
        }
        
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Format chat as plain text
     */
    formatChatAsText(messages) {
        return messages.map(msg => {
            const timestamp = new Date(msg.timestamp).toLocaleString();
            const sender = msg.type === 'user' ? 'You' : 'AI';
            return `[${timestamp}] ${sender}: ${msg.content}`;
        }).join('\n\n');
    }
}

// Create global instance
window.chatMessages = new ChatMessages(); 