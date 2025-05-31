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
                    window.chatApp.sendMessageFromSuggestion(suggestion);
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
        
        const messageElement = this.renderMessage(message);
        message.element = messageElement;
        
        // Add message to container
        if (this.messagesContainer) {
            this.messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
            
            // Setup artifact marker click handlers
            this.setupArtifactMarkerHandlers(messageElement, message);
        }
        
        // Hide welcome screen if this is the first message
        if (this.messages.length === 1 && this.welcomeScreen) {
            this.welcomeScreen.classList.add('d-none');
        }
        
        return message;
    }

    /**
     * Setup click handlers for artifact markers
     */
    setupArtifactMarkerHandlers(messageElement, message) {
        const artifactMarkers = messageElement.querySelectorAll('.artifact-marker');
        
        artifactMarkers.forEach((marker, index) => {
            marker.addEventListener('click', () => {
                // Show the corresponding artifact
                if (message.artifacts && message.artifacts[index]) {
                    const artifactData = message.artifacts[index];
                    if (window.chatArtifacts) {
                        const artifact = window.chatArtifacts.createArtifact(artifactData);
                        window.chatArtifacts.showArtifact(artifact.id);
                    }
                } else if (message.artifacts && message.artifacts.length > 0) {
                    // If no direct match, show the first artifact
                    const artifactData = message.artifacts[0];
                    if (window.chatArtifacts) {
                        const artifact = window.chatArtifacts.createArtifact(artifactData);
                        window.chatArtifacts.showArtifact(artifact.id);
                    }
                }
            });
        });
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
     * Process message content for formatting using marked.js for real markdown rendering
     */
    processMessageContent(content) {
        if (!content) return '';
        
        // Replace various artifact markers with clickable buttons
        content = content.replace(/\[([^[\]]+)\s+artifact\s+generated\]/gi, (match, artifactType) => {
            return `<span class="artifact-marker" data-artifact-type="${artifactType.toLowerCase()}">
                        <i class="fas fa-cube me-1"></i>
                        <strong>${artifactType} artifact generated</strong>
                        <small class="text-muted ms-1">(click to view)</small>
                    </span>`;
        });
        
        // Also handle other artifact marker formats
        content = content.replace(/\[Code artifact generated\]/gi, 
            `<span class="artifact-marker" data-artifact-type="code">
                <i class="fas fa-code me-1"></i>
                <strong>Code artifact generated</strong>
                <small class="text-muted ms-1">(click to view)</small>
            </span>`);
            
        content = content.replace(/\[Diagram artifact generated\]/gi, 
            `<span class="artifact-marker" data-artifact-type="diagram">
                <i class="fas fa-project-diagram me-1"></i>
                <strong>Diagram artifact generated</strong>
                <small class="text-muted ms-1">(click to view)</small>
            </span>`);
        
        // Use marked.js for proper markdown rendering if available
        if (window.marked) {
            try {
                // Configure marked.js with optimal settings for safe HTML handling
                marked.setOptions({
                    gfm: true,              // GitHub Flavored Markdown
                    breaks: true,           // Convert line breaks
                    sanitize: false,        // We'll handle sanitization ourselves
                    smartLists: true,       // Better list handling
                    smartypants: true,      // Smart quotes and punctuation
                    tables: true,           // Enable table support
                    headerIds: false,       // Don't add IDs to headers
                    mangle: false,          // Don't mangle autolinked email addresses
                    highlight: function(code, lang) {
                        // Custom syntax highlighting that properly escapes HTML
                        const escapedCode = code
                            .replace(/&/g, '&amp;')
                            .replace(/</g, '&lt;')
                            .replace(/>/g, '&gt;')
                            .replace(/"/g, '&quot;')
                            .replace(/'/g, '&#39;');
                        
                        // Add language-specific classes for Prism.js
                        if (lang && window.Prism && window.Prism.languages[lang]) {
                            return `<code class="language-${lang}">${escapedCode}</code>`;
                        }
                        return `<code>${escapedCode}</code>`;
                    }
                });
                
                // Let marked.js handle all the markdown parsing
                const htmlContent = marked.parse(content);
                
                // Post-process only for Bootstrap styling
                return this.postProcessMarkedContent(htmlContent);
                
            } catch (error) {
                console.warn('Error parsing markdown with marked.js:', error);
                // Fallback to basic processing
                return this.processBasicMarkdown(content);
            }
        } else {
            // Fallback if marked.js is not available
            console.warn('marked.js not available, using basic markdown processing');
            return this.processBasicMarkdown(content);
        }
    }

    /**
     * Post-process marked.js output for better Bootstrap styling
     */
    postProcessMarkedContent(htmlContent) {
        // Add Bootstrap classes to tables
        htmlContent = htmlContent.replace(/<table>/g, '<table class="table table-striped table-bordered mb-3">');
        htmlContent = htmlContent.replace(/<thead>/g, '<thead class="table-light">');
        
        // Add Bootstrap classes to blockquotes
        htmlContent = htmlContent.replace(/<blockquote>/g, '<blockquote class="border-start border-3 border-primary ps-3 mb-3 text-muted fst-italic">');
        
        // Add Bootstrap classes to code blocks (preserve any existing classes)
        htmlContent = htmlContent.replace(/<pre><code([^>]*)>/g, '<pre class="bg-light p-3 rounded mb-3 overflow-auto"><code class="text-dark"$1>');
        
        // Add Bootstrap classes to inline code
        htmlContent = htmlContent.replace(/<code>/g, '<code class="bg-light px-2 py-1 rounded">');
        
        // Add margin classes to headers
        htmlContent = htmlContent.replace(/<h1>/g, '<h1 class="mb-3 mt-3">');
        htmlContent = htmlContent.replace(/<h2>/g, '<h2 class="mb-2 mt-3">');
        htmlContent = htmlContent.replace(/<h3>/g, '<h3 class="mb-2 mt-3">');
        htmlContent = htmlContent.replace(/<h4>/g, '<h4 class="mb-2 mt-2">');
        htmlContent = htmlContent.replace(/<h5>/g, '<h5 class="mb-2 mt-2">');
        htmlContent = htmlContent.replace(/<h6>/g, '<h6 class="mb-2 mt-2">');
        
        // Add margin classes to paragraphs and lists
        htmlContent = htmlContent.replace(/<p>/g, '<p class="mb-3">');
        htmlContent = htmlContent.replace(/<ul>/g, '<ul class="mb-3">');
        htmlContent = htmlContent.replace(/<ol>/g, '<ol class="mb-3">');
        
        // Ensure Prism.js can highlight code if available
        if (window.Prism) {
            // Trigger Prism highlighting after content is added to DOM
            setTimeout(() => {
                if (window.Prism && window.Prism.highlightAll) {
                    window.Prism.highlightAll();
                }
            }, 100);
        }
        
        return htmlContent;
    }

    /**
     * Fallback basic markdown processing (keeping the old method as backup)
     */
    processBasicMarkdown(text) {
        // This is the old processEnhancedMarkdown method as fallback
        // First, preserve code blocks to avoid processing markdown inside them
        const codeBlocks = [];
        text = text.replace(/```[\s\S]*?```/g, (match, offset) => {
            codeBlocks.push(match);
            return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
        });
        
        // Process headers (### Header)
        text = text.replace(/^### (.*$)/gim, '<h3 class="mb-2 mt-3">$1</h3>');
        text = text.replace(/^## (.*$)/gim, '<h2 class="mb-2 mt-3">$1</h2>');
        text = text.replace(/^# (.*$)/gim, '<h1 class="mb-3 mt-3">$1</h1>');
        
        // Process markdown tables FIRST (before other formatting)
        text = this.processMarkdownTables(text);
        
        // Process bold and italic (before other formatting)
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Process inline code (before other formatting)
        text = text.replace(/`([^`]+)`/g, '<code class="bg-light px-1 py-0 rounded">$1</code>');
        
        // Process strikethrough
        text = text.replace(/~~(.*?)~~/g, '<del>$1</del>');
        
        // Process unordered lists
        text = text.replace(/^\s*[-*+]\s+(.+)$/gim, '<li>$1</li>');
        
        // Process ordered lists  
        text = text.replace(/^\s*\d+\.\s+(.+)$/gim, '<li>$1</li>');
        
        // Wrap consecutive list items in ul/ol tags
        text = text.replace(/(<li>.*?<\/li>)(?:\s*<li>.*?<\/li>)*/gs, (match) => {
            return `<ul class="mb-3">${match}</ul>`;
        });
        
        // Process blockquotes
        text = text.replace(/^>\s+(.+)$/gim, '<blockquote class="border-start border-3 border-secondary ps-3 mb-3 text-muted fst-italic">$1</blockquote>');
        
        // Process line breaks - convert double newlines to paragraph breaks
        text = text.split('\n\n').map(paragraph => {
            // Don't wrap headers, lists, blockquotes, tables in paragraphs
            if (paragraph.match(/^<(h[1-6]|ul|ol|blockquote|div|p|table)/)) {
                return paragraph;
            }
            // Don't wrap empty content
            if (!paragraph.trim()) {
                return '';
            }
            return `<p class="mb-3">${paragraph.replace(/\n/g, '<br>')}</p>`;
        }).join('\n');
        
        // Restore code blocks
        codeBlocks.forEach((block, index) => {
            const codeContent = block.replace(/```(\w+)?\n?/g, '').replace(/```$/, '').trim();
            const language = block.match(/```(\w+)/)?.[1] || '';
            const langClass = language ? ` language-${language}` : '';
            
            text = text.replace(`__CODE_BLOCK_${index}__`, 
                `<pre class="bg-light p-3 rounded mb-3 overflow-auto"><code class="text-dark${langClass}">${this.escapeHtml(codeContent)}</code></pre>`);
        });
        
        return text;
    }

    /**
     * Process markdown tables into HTML
     */
    processMarkdownTables(text) {
        // Match markdown table pattern
        const tableRegex = /(\|.*?\|(?:\r?\n|\r))+(\|[-:|]+\|(?:\r?\n|\r))(\|.*?\|(?:\r?\n|\r))*/gm;
        
        return text.replace(tableRegex, (match) => {
            const lines = match.trim().split(/\r?\n|\r/);
            
            if (lines.length < 2) return match;
            
            // First line is header
            const headerLine = lines[0];
            const separatorLine = lines[1];
            const dataLines = lines.slice(2);
            
            // Validate separator line (contains dashes and pipes)
            if (!separatorLine.includes('-')) return match;
            
            // Parse header
            const headers = headerLine.split('|')
                .map(cell => cell.trim())
                .filter(cell => cell !== '');
            
            // Parse data rows
            const rows = dataLines.map(line => 
                line.split('|')
                    .map(cell => cell.trim())
                    .filter(cell => cell !== '')
            ).filter(row => row.length > 0);
            
            // Generate HTML table
            let tableHTML = '<table class="table table-striped table-bordered mb-3">';
            
            // Generate header
            tableHTML += '<thead class="table-light"><tr>';
            headers.forEach(header => {
                tableHTML += `<th>${header}</th>`;
            });
            tableHTML += '</tr></thead>';
            
            // Generate body
            tableHTML += '<tbody>';
            rows.forEach(row => {
                tableHTML += '<tr>';
                row.forEach(cell => {
                    tableHTML += `<td>${cell}</td>`;
                });
                tableHTML += '</tr>';
            });
            tableHTML += '</tbody>';
            
            tableHTML += '</table>';
            
            return tableHTML;
        });
    }

    /**
     * Convert URLs to clickable links
     */
    linkifyUrls(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
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
        artifactsDiv.className = 'message-artifacts mt-2';
        
        artifacts.forEach(artifactData => {
            // Create artifact and get button HTML
            const artifact = window.chatArtifacts.createArtifact(artifactData);
            const buttonHtml = window.chatArtifacts.createArtifactButton(artifact);
            
            const buttonContainer = document.createElement('div');
            buttonContainer.innerHTML = buttonHtml;
            const button = buttonContainer.firstElementChild;
            
            // Add enhanced styling for better visibility
            button.classList.add('artifact-button-enhanced');
            
            artifactsDiv.appendChild(button);
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

    /**
     * Show thinking indicator with custom status
     */
    showThinkingIndicator(status = "AI is thinking...") {
        if (this.typingIndicator) {
            this.typingIndicator.classList.remove('d-none');
            
            // Update status text
            const statusElement = this.typingIndicator.querySelector('.typing-text');
            if (statusElement) {
                statusElement.textContent = status;
            }
            
            this.scrollToBottom();
        }
    }

    /**
     * Start streaming message
     */
    startStreamingMessage() {
        const message = this.createMessage('ai', '', [], []);
        
        // Add streaming class for visual indication
        const messageElement = this.renderMessage(message);
        messageElement.classList.add('streaming');
        message.element = messageElement;
        
        // Add to messages container
        if (this.messagesContainer) {
            this.messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
        }
        
        // Hide welcome screen
        if (this.messages.length === 0 && this.welcomeScreen) {
            this.welcomeScreen.classList.add('d-none');
        }
        
        this.messages.push(message);
        
        return message;
    }

    /**
     * Append content to streaming message with real-time markdown rendering
     */
    appendToStreamingMessage(message, content, isFinal = false) {
        if (!message || !message.element) return;
        
        // Accumulate content 
        message.content += content;
        
        // Get the bubble element
        const bubbleElement = message.element.querySelector('.message-bubble');
        if (!bubbleElement) return;

        // Real-time rendering without delay for true streaming experience
        // Only batch updates if we're getting very rapid chunks (< 10ms apart)
        const now = Date.now();
        const timeSinceLastUpdate = now - (message._lastUpdateTime || 0);
        
        if (timeSinceLastUpdate > 10 || isFinal) {
            // Update immediately for responsive streaming
            this._updateMessageDisplay(message, bubbleElement);
            message._lastUpdateTime = now;
            
            // Clear any pending timer
            if (message._updateTimer) {
                clearTimeout(message._updateTimer);
                message._updateTimer = null;
            }
        } else {
            // Only use minimal delay for extremely rapid updates (> 100 tokens/sec)
            if (!message._updateTimer) {
                message._updateTimer = setTimeout(() => {
                    this._updateMessageDisplay(message, bubbleElement);
                    message._updateTimer = null;
                    message._lastUpdateTime = Date.now();
                }, 5); // Reduced to 5ms for near real-time
            }
        }
        
        // If final, ensure immediate update
        if (isFinal) {
            if (message._updateTimer) {
                clearTimeout(message._updateTimer);
                message._updateTimer = null;
            }
            this._updateMessageDisplay(message, bubbleElement);
            message.element.classList.remove('streaming');
        }
    }

    /**
     * Update message display with optimized rendering
     */
    _updateMessageDisplay(message, bubbleElement) {
        // Process the accumulated content with markdown
        const processedContent = this.processMessageContent(message.content);
        
        // Use more efficient DOM update
        if (bubbleElement.innerHTML !== processedContent) {
            bubbleElement.innerHTML = processedContent;
            
            // Re-setup artifact handlers after content update
            this.setupArtifactMarkerHandlers(message.element, message);
            
            // Trigger syntax highlighting for any new code blocks
            this.triggerSyntaxHighlighting(bubbleElement);
        }
        
        this.scrollToBottom();
    }

    /**
     * Trigger syntax highlighting for code blocks
     */
    triggerSyntaxHighlighting(element) {
        if (window.Prism && window.Prism.highlightAllUnder) {
            // Highlight code blocks within the specific element
            window.Prism.highlightAllUnder(element);
        } else if (window.Prism && window.Prism.highlightAll) {
            // Fallback to highlighting all code blocks
            setTimeout(() => window.Prism.highlightAll(), 50);
        }
    }

    /**
     * Add artifact to streaming message
     */
    addArtifactToStreamingMessage(message, artifact) {
        if (!message) return;
        
        // Add artifact to message
        if (!message.artifacts) {
            message.artifacts = [];
        }
        message.artifacts.push(artifact);
        
        // Update the message display
        if (message.element) {
            const bubbleElement = message.element.querySelector('.message-bubble');
            if (bubbleElement) {
                // Add artifact button
                const artifactsDiv = this.createArtifactsDisplay([artifact]);
                bubbleElement.appendChild(artifactsDiv);
            }
        }
    }

    /**
     * Finalize streaming message
     */
    finalizeStreamingMessage(message, responseData) {
        if (!message) return;
        
        // Only update with data that wasn't streamed (artifacts, metadata)
        // DON'T overwrite content since it was already streamed token by token
        if (responseData.artifacts) {
            message.artifacts = responseData.artifacts;
        }
        if (responseData.metadata) {
            message.metadata = responseData.metadata;
        }
        
        // Remove streaming class
        if (message.element) {
            message.element.classList.remove('streaming');
            
            // Setup artifact handlers for any new artifacts
            this.setupArtifactMarkerHandlers(message.element, message);
        }
        
        this.scrollToBottom();
    }

    /**
     * Hide thinking indicator
     */
    hideThinkingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.classList.add('d-none');
        }
    }

    /**
     * Show agent thinking indicator
     */
    showAgentThinking(agent, status) {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.classList.remove('d-none');
            
            // Update with agent info
            const agentIcon = this.getAgentIcon(agent);
            indicator.innerHTML = `
                <div class="thinking-indicator">
                    <span class="agent-name">${agentIcon} ${agent}</span>
                    <span class="thinking-dots">●●●</span>
                    <span class="thinking-text">${status}</span>
                </div>
            `;
        }
    }

    /**
     * Append agent content to streaming message with real-time markdown and optimized rendering
     */
    appendAgentContent(message, agent, content, isFinal = false) {
        if (!message || !message.element) return;

        const messageElement = message.element;
        let agentSection = messageElement.querySelector(`[data-agent="${agent}"]`);
        
        if (!agentSection) {
            // Create new agent section
            agentSection = document.createElement('div');
            agentSection.className = 'agent-section';
            agentSection.setAttribute('data-agent', agent);
            
            const agentHeader = document.createElement('div');
            agentHeader.className = 'agent-header';
            agentHeader.innerHTML = `
                <span class="agent-name">${this.getAgentIcon(agent)} ${agent} Agent</span>
            `;
            
            const agentContent = document.createElement('div');
            agentContent.className = 'agent-content';
            
            agentSection.appendChild(agentHeader);
            agentSection.appendChild(agentContent);
            
            const messageBubble = messageElement.querySelector('.message-bubble');
            messageBubble.appendChild(agentSection);
        }
        
        // Update content with real-time rendering
        const contentDiv = agentSection.querySelector('.agent-content');
        if (contentDiv) {
            // Get existing content or initialize
            let existingText = contentDiv.getAttribute('data-raw-content') || '';
            existingText += content;
            contentDiv.setAttribute('data-raw-content', existingText);
            
            // Real-time updates with smart throttling (similar to main content)
            const now = Date.now();
            const timeSinceLastUpdate = now - (contentDiv._lastUpdateTime || 0);
            
            if (timeSinceLastUpdate > 10 || isFinal || content.trim()) {
                // Immediate update for responsive streaming
                this._updateAgentDisplay(agentSection, contentDiv, existingText);
                contentDiv._lastUpdateTime = now;
            }
            
            if (isFinal) {
                this._updateAgentDisplay(agentSection, contentDiv, existingText);
                agentSection.classList.add('completed');
                contentDiv.removeAttribute('data-raw-content');
            }
        }
        
        this.scrollToBottom();
    }

    /**
     * Update agent display with optimized rendering
     */
    _updateAgentDisplay(agentSection, contentDiv, text) {
        // Render markdown in real-time
        const processedContent = this.processMessageContent(text);
        
        // Only update if content actually changed
        if (contentDiv.innerHTML !== processedContent) {
            contentDiv.innerHTML = processedContent;
            
            // Force browser repaint for smoother streaming effect
            // This technique is from the Chrome developers' best practices
            if (window.requestAnimationFrame) {
                window.requestAnimationFrame(() => {
                    this.triggerSyntaxHighlighting(contentDiv);
                });
            } else {
                this.triggerSyntaxHighlighting(contentDiv);
            }
        }
    }

    /**
     * Add agent artifact to streaming message
     */
    addAgentArtifact(message, agent, artifact) {
        if (!message || !message.element) return;

        const messageElement = message.element;
        let agentSection = messageElement.querySelector(`[data-agent="${agent}"]`);
        
        if (!agentSection) {
            // Create agent section if it doesn't exist
            this.appendAgentContent(message, agent, '', false);
            agentSection = messageElement.querySelector(`[data-agent="${agent}"]`);
        }
        
        if (agentSection) {
            const artifactDiv = document.createElement('div');
            artifactDiv.className = 'agent-artifact';
            artifactDiv.setAttribute('data-artifact-id', artifact.id);
            artifactDiv.innerHTML = `
                <div class="artifact-header">
                    <span class="artifact-title">${artifact.title}</span>
                    <span class="artifact-type">${artifact.type}</span>
                </div>
                <div class="artifact-content streaming">
                    <div class="artifact-loading">Creating ${artifact.type}...</div>
                </div>
            `;
            
            agentSection.appendChild(artifactDiv);
        }
        
        this.scrollToBottom();
    }

    /**
     * Update agent artifact content
     */
    updateAgentArtifact(artifactId, content, isFinal = false) {
        const artifactDiv = document.querySelector(`[data-artifact-id="${artifactId}"]`);
        if (!artifactDiv) return;

        const contentDiv = artifactDiv.querySelector('.artifact-content');
        const loadingDiv = contentDiv.querySelector('.artifact-loading');
        
        if (loadingDiv) {
            loadingDiv.remove();
            // Create actual content container
            const actualContent = document.createElement('div');
            actualContent.className = 'artifact-actual-content';
            contentDiv.appendChild(actualContent);
        }

        const actualContentDiv = contentDiv.querySelector('.artifact-actual-content');
        if (actualContentDiv) {
            actualContentDiv.textContent = content;
            
            if (isFinal) {
                artifactDiv.classList.remove('streaming');
                artifactDiv.classList.add('completed');
                
                // Add click handler to show artifact
                artifactDiv.addEventListener('click', () => {
                    if (window.chatArtifacts) {
                        window.chatArtifacts.showArtifact(artifactId);
                    }
                });
            }
        }
        
        this.scrollToBottom();
    }

    /**
     * Show agent error
     */
    showAgentError(agent, error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'agent-error';
        errorDiv.innerHTML = `
            <div class="agent-header">
                <span class="agent-name">${this.getAgentIcon(agent)} ${agent} Agent</span>
            </div>
            <div class="error-text">❌ ${error}</div>
        `;
        
        if (this.messagesContainer) {
            this.messagesContainer.appendChild(errorDiv);
            this.scrollToBottom();
        }
    }

    /**
     * Get agent icon
     */
    getAgentIcon(agent) {
        const icons = {
            'orchestrator': '🎯',
            'Code': '👨‍💻',
            'Diagram': '📊', 
            'Document': '📝',
            'General': '🤖'
        };
        return icons[agent] || '🤖';
    }
}

// Create global instance
window.chatMessages = new ChatMessages(); 