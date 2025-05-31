/**
 * Chat Service Module
 * Handles API calls, file uploads, and backend communication
 */

class ChatService {
    constructor() {
        this.baseUrl = window.location.origin;
        this.apiUrl = `${this.baseUrl}/api/v1`;
        this.uploadUrl = `${this.baseUrl}/api/v1/files/upload`;
        
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.allowedFileTypes = [
            'text/plain',
            'text/markdown',
            'application/pdf',
            'application/json',
            'text/csv',
            'image/png',
            'image/jpeg',
            'image/jpg',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
    }

    /**
     * Upload files to server
     */
    async uploadFiles(files) {
        const formData = new FormData();
        const validFiles = [];
        
        // Validate files
        for (const file of files) {
            if (!this.validateFile(file)) {
                throw new Error(`Invalid file: ${file.name}`);
            }
            formData.append('files', file);
            validFiles.push({
                name: file.name,
                size: file.size,
                type: this.getFileType(file.type),
                lastModified: file.lastModified
            });
        }
        
        try {
            const response = await fetch(this.uploadUrl, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            return {
                success: true,
                files: validFiles,
                uploadPaths: result.file_paths || [],
                message: result.message || 'Files uploaded successfully'
            };
            
        } catch (error) {
            console.error('Upload error:', error);
            throw new Error(`Failed to upload files: ${error.message}`);
        }
    }

    /**
     * Validate file before upload
     */
    validateFile(file) {
        // Check file size
        if (file.size > this.maxFileSize) {
            throw new Error(`File "${file.name}" is too large. Maximum size is ${this.formatFileSize(this.maxFileSize)}`);
        }
        
        // Check file type
        if (!this.allowedFileTypes.includes(file.type)) {
            throw new Error(`File type "${file.type}" is not allowed for "${file.name}"`);
        }
        
        return true;
    }

    /**
     * Get file type category
     */
    getFileType(mimeType) {
        const typeMap = {
            'text/plain': 'text',
            'text/markdown': 'text',
            'application/pdf': 'pdf',
            'application/json': 'json',
            'text/csv': 'document',
            'image/png': 'image',
            'image/jpeg': 'image',
            'image/jpg': 'image',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document'
        };
        
        return typeMap[mimeType] || 'document';
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Send chat message to AI service
     * For now, this will use the WebSocket, but can be adapted for HTTP API
     */
    async sendMessage(content, attachments = []) {
        // This method will be primarily handled by the WebSocket
        // But we can add HTTP fallback here if needed
        
        try {
            // For now, delegate to WebSocket instance from chat app
            // The WebSocket should be handled by the main chat app
            return { success: true };
            
        } catch (error) {
            console.error('Send message error:', error);
            throw error;
        }
    }

    /**
     * Get chat history
     */
    async getChatHistory(limit = 50, offset = 0) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/history?limit=${limit}&offset=${offset}`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch chat history: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Get chat history error:', error);
            
            // Return empty history as fallback
            return {
                success: true,
                messages: [],
                total: 0
            };
        }
    }

    /**
     * Save chat session
     */
    async saveChatSession(messages, title = null) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title || `Chat Session ${new Date().toLocaleDateString()}`,
                    messages: messages,
                    created: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to save chat session: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Save chat session error:', error);
            throw error;
        }
    }

    /**
     * Load chat session
     */
    async loadChatSession(sessionId) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/sessions/${sessionId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load chat session: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Load chat session error:', error);
            throw error;
        }
    }

    /**
     * List chat sessions
     */
    async listChatSessions(limit = 20, offset = 0) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/sessions?limit=${limit}&offset=${offset}`);
            
            if (!response.ok) {
                throw new Error(`Failed to list chat sessions: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('List chat sessions error:', error);
            
            // Return empty list as fallback
            return {
                success: true,
                sessions: [],
                total: 0
            };
        }
    }

    /**
     * Delete chat session
     */
    async deleteChatSession(sessionId) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/sessions/${sessionId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`Failed to delete chat session: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Delete chat session error:', error);
            throw error;
        }
    }

    /**
     * Get system health/status
     */
    async getSystemHealth() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            
            if (!response.ok) {
                throw new Error(`Health check failed: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Health check error:', error);
            return {
                status: 'error',
                message: error.message
            };
        }
    }

    /**
     * Process file for chat context
     */
    async processFileForChat(filePath) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/process-file`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_path: filePath
                })
            });
            
            if (!response.ok) {
                throw new Error(`File processing failed: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('File processing error:', error);
            throw error;
        }
    }

    /**
     * Generate download link for file
     */
    getDownloadUrl(filePath) {
        return `${this.baseUrl}/api/files/download/${encodeURIComponent(filePath)}`;
    }

    /**
     * Export chat data
     */
    async exportChat(format = 'json', sessionId = null) {
        try {
            const url = sessionId 
                ? `${this.apiUrl}/chat/export/${sessionId}?format=${format}`
                : `${this.apiUrl}/chat/export?format=${format}`;
                
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            const downloadUrl = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `chat_export_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
            
            return { success: true };
            
        } catch (error) {
            console.error('Export error:', error);
            throw error;
        }
    }

    /**
     * Search chat history
     */
    async searchChatHistory(query, limit = 20) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    limit: limit
                })
            });
            
            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Search error:', error);
            throw error;
        }
    }

    /**
     * Get suggested responses
     */
    async getSuggestedResponses(context) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/suggestions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    context: context
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to get suggestions: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Suggestions error:', error);
            return {
                success: true,
                suggestions: []
            };
        }
    }

    /**
     * Update user preferences
     */
    async updatePreferences(preferences) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/preferences`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(preferences)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to update preferences: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Update preferences error:', error);
            throw error;
        }
    }

    /**
     * Get user preferences
     */
    async getPreferences() {
        try {
            const response = await fetch(`${this.apiUrl}/chat/preferences`);
            
            if (!response.ok) {
                throw new Error(`Failed to get preferences: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Get preferences error:', error);
            
            // Return default preferences
            return {
                success: true,
                preferences: {
                    theme: 'light',
                    language: 'en',
                    notifications: true,
                    auto_save: true
                }
            };
        }
    }
}

// Create global instance
window.chatService = new ChatService(); 