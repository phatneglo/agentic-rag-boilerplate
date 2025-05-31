/**
 * Chat Artifacts Module
 * Handles creation, rendering, and management of artifacts (code, diagrams, etc.)
 */

class ChatArtifacts {
    constructor() {
        this.artifacts = new Map();
        this.currentArtifact = null;
        this.sidebar = null;
        this.sidebarContent = null;
        
        this.init();
    }

    /**
     * Initialize artifacts system
     */
    init() {
        this.sidebar = document.getElementById('artifactsSidebar');
        this.sidebarContent = document.getElementById('artifactsContent');
        
        // Initialize Mermaid
        if (window.mermaid) {
            mermaid.initialize({
                startOnLoad: false,
                theme: 'default',
                securityLevel: 'loose',
                fontFamily: 'system-ui, -apple-system, sans-serif'
            });
        }
        
        // Set up event listeners
        this.setupEventListeners();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Artifact button clicks using event delegation
        document.addEventListener('click', (e) => {
            // Handle artifact button clicks
            const artifactButton = e.target.closest('.artifact-button');
            if (artifactButton) {
                e.preventDefault();
                const artifactId = artifactButton.getAttribute('data-artifact-id');
                if (artifactId) {
                    this.showArtifact(artifactId);
                }
                return;
            }
            
            // Handle view artifact button clicks  
            const viewButton = e.target.closest('.view-artifact');
            if (viewButton) {
                e.preventDefault();
                e.stopPropagation();
                const artifactButton = viewButton.closest('.artifact-button');
                if (artifactButton) {
                    const artifactId = artifactButton.getAttribute('data-artifact-id');
                    if (artifactId) {
                        this.showArtifact(artifactId);
                    }
                }
                return;
            }
            
            // Handle sidebar close
            if (e.target.closest('.close-sidebar')) {
                this.hideSidebar();
                return;
            }
            
            // Handle preview toggle
            if (e.target.closest('.preview-toggle')) {
                const artifactId = e.target.closest('.artifact-viewer').getAttribute('data-artifact-id');
                if (artifactId) {
                    this.togglePreview(artifactId);
                }
                return;
            }
        });

        // Escape key to close sidebar
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.sidebar && !this.sidebar.classList.contains('d-none')) {
                this.hideSidebar();
            }
        });
    }

    /**
     * Create artifact from AI response
     */
    createArtifact(artifactData) {
        const artifact = {
            id: artifactData.id || this.generateId(),
            type: artifactData.type,
            title: artifactData.title || 'Untitled',
            content: artifactData.content,
            language: artifactData.language || null,
            metadata: artifactData.metadata || {},
            created: new Date(),
            updated: new Date()
        };

        this.artifacts.set(artifact.id, artifact);
        return artifact;
    }

    /**
     * Generate unique ID for artifacts
     */
    generateId() {
        return 'artifact_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Render artifact in sidebar
     */
    showArtifact(artifactId) {
        const artifact = this.artifacts.get(artifactId);
        if (!artifact) {
            console.error('Artifact not found:', artifactId);
            return;
        }

        this.currentArtifact = artifact;
        this.renderArtifact(artifact);
        this.showSidebar();
    }

    /**
     * Render artifact content based on type
     */
    renderArtifact(artifact) {
        if (!this.sidebarContent) return;

        const artifactHtml = this.createArtifactHtml(artifact);
        this.sidebarContent.innerHTML = artifactHtml;
        
        // Post-render processing based on type
        this.postRenderArtifact(artifact);
    }

    /**
     * Create HTML for artifact based on type
     */
    createArtifactHtml(artifact) {
        const header = this.createArtifactHeader(artifact);
        let content = '';

        const viewMode = artifact.viewMode || 'preview';
        const showCode = viewMode === 'code';

        switch (artifact.type) {
            case 'code':
                content = this.createCodeArtifact(artifact);
                break;
            case 'mermaid':
                if (showCode) {
                    content = this.createCodeView(artifact.content, 'mermaid');
                } else {
                    content = this.createMermaidArtifact(artifact);
                }
                break;
            case 'html':
                if (showCode) {
                    content = this.createCodeView(artifact.content, 'html');
                } else {
                    content = this.createHtmlArtifact(artifact);
                }
                break;
            case 'markdown':
                if (showCode) {
                    content = this.createCodeView(artifact.content, 'markdown');
                } else {
                    content = this.createMarkdownArtifact(artifact);
                }
                break;
            case 'json':
                content = this.createJsonArtifact(artifact);
                break;
            default:
                content = this.createTextArtifact(artifact);
        }

        return `
            <div class="artifact-viewer" data-artifact-id="${artifact.id}">
                ${header}
                <div class="artifact-content" data-view="${viewMode}">
                    ${content}
                </div>
            </div>
        `;
    }

    /**
     * Create artifact header with title, actions, and preview toggle
     */
    createArtifactHeader(artifact) {
        const hasPreview = ['html', 'mermaid', 'markdown'].includes(artifact.type);
        
        return `
            <div class="artifact-header">
                <div class="artifact-title-section">
                    <div class="artifact-title">${artifact.title}</div>
                    ${hasPreview ? `
                        <div class="artifact-view-toggle">
                            <button class="toggle-btn active" data-view="preview" onclick="chatArtifacts.switchView('${artifact.id}', 'preview')">
                                <i class="fas fa-eye"></i> Preview
                            </button>
                            <button class="toggle-btn" data-view="code" onclick="chatArtifacts.switchView('${artifact.id}', 'code')">
                                <i class="fas fa-code"></i> Code
                            </button>
                        </div>
                    ` : ''}
                </div>
                <div class="artifact-actions">
                    <button class="artifact-action-btn" onclick="chatArtifacts.copyArtifact('${artifact.id}')" title="Copy">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button class="artifact-action-btn" onclick="chatArtifacts.downloadArtifact('${artifact.id}')" title="Download">
                        <i class="fas fa-download"></i>
                    </button>
                    ${artifact.type === 'mermaid' ? `
                        <button class="artifact-action-btn" onclick="chatArtifacts.exportMermaidAsSvg('${artifact.id}')" title="Export as SVG">
                            <i class="fas fa-file-image"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create code artifact
     */
    createCodeArtifact(artifact) {
        const language = artifact.language || 'text';
        const escapedContent = this.escapeHtml(artifact.content);
        
        return `
            <pre><code class="language-${language}">${escapedContent}</code></pre>
        `;
    }

    /**
     * Create Mermaid diagram artifact
     */
    createMermaidArtifact(artifact) {
        const diagramId = `mermaid-${artifact.id}`;
        return `
            <div class="mermaid" id="${diagramId}">
                ${artifact.content}
            </div>
        `;
    }

    /**
     * Create HTML artifact
     */
    createHtmlArtifact(artifact) {
        // Sanitize HTML content for security
        const sanitizedContent = this.sanitizeHtml(artifact.content);
        return `
            <div class="html-preview">
                <iframe srcdoc="${this.escapeHtml(sanitizedContent)}" 
                        style="width: 100%; height: 400px; border: 1px solid #e2e8f0; border-radius: 4px;">
                </iframe>
            </div>
        `;
    }

    /**
     * Create Markdown artifact
     */
    createMarkdownArtifact(artifact) {
        const html = this.markdownToHtml(artifact.content);
        return `<div class="markdown-content">${html}</div>`;
    }

    /**
     * Create JSON artifact
     */
    createJsonArtifact(artifact) {
        try {
            const formatted = JSON.stringify(JSON.parse(artifact.content), null, 2);
            const escapedContent = this.escapeHtml(formatted);
            return `<pre><code class="language-json">${escapedContent}</code></pre>`;
        } catch (e) {
            return this.createTextArtifact(artifact);
        }
    }

    /**
     * Create text artifact
     */
    createTextArtifact(artifact) {
        const escapedContent = this.escapeHtml(artifact.content);
        return `<pre style="white-space: pre-wrap;">${escapedContent}</pre>`;
    }

    /**
     * Post-render processing for specific artifact types
     */
    postRenderArtifact(artifact) {
        switch (artifact.type) {
            case 'code':
            case 'json':
                this.highlightCode();
                break;
            case 'mermaid':
                this.renderMermaidDiagram(artifact);
                break;
        }
    }

    /**
     * Highlight code using Prism.js
     */
    highlightCode() {
        if (window.Prism) {
            Prism.highlightAllUnder(this.sidebarContent);
        }
    }

    /**
     * Render Mermaid diagram with improved error handling
     */
    async renderMermaidDiagram(artifact) {
        if (!window.mermaid) return;

        const diagramId = `mermaid-${artifact.id}`;
        const element = document.getElementById(diagramId);
        
        if (element) {
            try {
                // Clean and validate the mermaid content
                let cleanContent = this.cleanMermaidContent(artifact.content);
                
                const { svg } = await mermaid.render(diagramId + '_svg', cleanContent);
                element.innerHTML = svg;
            } catch (error) {
                console.error('Error rendering Mermaid diagram:', error);
                
                // Provide more helpful error message and show the raw content
                element.innerHTML = `
                    <div class="alert alert-warning">
                        <h6><i class="fas fa-exclamation-triangle me-2"></i>Diagram Rendering Error</h6>
                        <p><strong>Error:</strong> ${error.message}</p>
                        <details>
                            <summary>Show raw diagram code</summary>
                            <pre style="margin-top: 10px; font-size: 12px;"><code>${this.escapeHtml(artifact.content)}</code></pre>
                        </details>
                        <small class="text-muted">
                            <strong>Tip:</strong> Check the Mermaid syntax. Common issues include missing spaces, invalid characters, or malformed arrows.
                        </small>
                    </div>
                `;
            }
        }
    }

    /**
     * Clean and validate Mermaid diagram content
     */
    cleanMermaidContent(content) {
        // Remove leading/trailing whitespace
        let cleaned = content.trim();
        
        // Fix common arrow syntax issues
        cleaned = cleaned.replace(/-->/g, ' --> ');
        cleaned = cleaned.replace(/--->/g, ' ---> ');
        cleaned = cleaned.replace(/\|->/g, ' |-> ');
        cleaned = cleaned.replace(/==/g, ' == ');
        
        // Ensure proper spacing around operators
        cleaned = cleaned.replace(/\s+/g, ' ');
        
        // Fix line endings
        cleaned = cleaned.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        
        return cleaned;
    }

    /**
     * Show artifacts sidebar
     */
    showSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.add('show');
            this.sidebar.classList.add('slide-in-right');
            
            // Adjust main chat container
            const chatContainer = document.querySelector('.chat-messages-container');
            if (chatContainer) {
                chatContainer.classList.add('with-sidebar');
            }
        }
    }

    /**
     * Hide artifacts sidebar
     */
    hideSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.remove('show');
            this.sidebar.classList.remove('slide-in-right');
            
            // Restore main chat container
            const chatContainer = document.querySelector('.chat-messages-container');
            if (chatContainer) {
                chatContainer.classList.remove('with-sidebar');
            }
        }
        this.currentArtifact = null;
    }

    /**
     * Copy artifact content to clipboard
     */
    async copyArtifact(artifactId) {
        const artifact = this.artifacts.get(artifactId);
        if (!artifact) return;

        try {
            await navigator.clipboard.writeText(artifact.content);
            this.showToast('Copied to clipboard!', 'success');
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            this.showToast('Failed to copy to clipboard', 'error');
        }
    }

    /**
     * Download artifact as file
     */
    downloadArtifact(artifactId) {
        const artifact = this.artifacts.get(artifactId);
        if (!artifact) return;

        const filename = this.getDownloadFilename(artifact);
        const blob = new Blob([artifact.content], { type: this.getMimeType(artifact.type) });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('Downloaded successfully!', 'success');
    }

    /**
     * Export Mermaid diagram as SVG
     */
    async exportMermaidAsSvg(artifactId) {
        const artifact = this.artifacts.get(artifactId);
        if (!artifact || artifact.type !== 'mermaid') return;

        try {
            const { svg } = await mermaid.render('export_' + artifactId, artifact.content);
            const blob = new Blob([svg], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${artifact.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.svg`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showToast('SVG exported successfully!', 'success');
        } catch (error) {
            console.error('Failed to export SVG:', error);
            this.showToast('Failed to export SVG', 'error');
        }
    }

    /**
     * Get appropriate filename for download
     */
    getDownloadFilename(artifact) {
        const baseName = artifact.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
        const extension = this.getFileExtension(artifact.type, artifact.language);
        return `${baseName}.${extension}`;
    }

    /**
     * Get file extension based on artifact type and language
     */
    getFileExtension(type, language) {
        switch (type) {
            case 'code':
                return this.getCodeExtension(language);
            case 'mermaid':
                return 'mmd';
            case 'html':
                return 'html';
            case 'markdown':
                return 'md';
            case 'json':
                return 'json';
            default:
                return 'txt';
        }
    }

    /**
     * Get code file extension based on language
     */
    getCodeExtension(language) {
        const extensions = {
            'javascript': 'js',
            'typescript': 'ts',
            'python': 'py',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'csharp': 'cs',
            'php': 'php',
            'ruby': 'rb',
            'go': 'go',
            'rust': 'rs',
            'swift': 'swift',
            'kotlin': 'kt',
            'sql': 'sql',
            'css': 'css',
            'scss': 'scss',
            'html': 'html',
            'xml': 'xml',
            'yaml': 'yml',
            'json': 'json',
            'markdown': 'md',
            'bash': 'sh',
            'shell': 'sh'
        };
        
        return extensions[language] || 'txt';
    }

    /**
     * Get MIME type for artifact type
     */
    getMimeType(type) {
        const mimeTypes = {
            'code': 'text/plain',
            'mermaid': 'text/plain',
            'html': 'text/html',
            'markdown': 'text/markdown',
            'json': 'application/json'
        };
        
        return mimeTypes[type] || 'text/plain';
    }

    /**
     * Create artifact button HTML
     */
    createArtifactButton(artifact) {
        const iconClass = this.getArtifactIcon(artifact.type);
        const typeLabel = this.getArtifactTypeLabel(artifact.type);
        
        // Use the specific title from the artifact, not just a generic type
        const displayTitle = artifact.title || `${typeLabel} Artifact`;
        
        return `
            <div class="artifact-button" data-artifact-id="${artifact.id}">
                <div class="artifact-button-content">
                    <div class="artifact-icon">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="artifact-info">
                        <div class="artifact-title">${displayTitle}</div>
                        <div class="artifact-type">${typeLabel}${artifact.language ? ` (${artifact.language})` : ''}</div>
                    </div>
                    <div class="artifact-actions">
                        <button class="btn btn-sm btn-outline-primary view-artifact">
                            <i class="fas fa-eye"></i>
                            View
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get artifact type label for display
     */
    getArtifactTypeLabel(type) {
        const labels = {
            'code': 'Code',
            'document': 'Document', 
            'html': 'Web Page',
            'mermaid': 'Diagram',
            'markdown': 'Markdown',
            'text': 'Text File'
        };
        return labels[type] || 'Artifact';
    }

    /**
     * Get icon class for artifact type
     */
    getArtifactIcon(type) {
        const icons = {
            'code': 'fas fa-code',
            'mermaid': 'fas fa-project-diagram',
            'html': 'fab fa-html5',
            'markdown': 'fab fa-markdown',
            'json': 'fas fa-brackets-curly'
        };
        
        return icons[type] || 'fas fa-file-alt';
    }

    /**
     * Convert markdown to HTML with enhanced processing
     */
    markdownToHtml(markdown) {
        if (window.marked) {
            return marked.parse(markdown);
        }
        
        // Enhanced fallback markdown conversion
        let html = markdown;
        
        // Process headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Process code blocks
        html = html.replace(/```[\s\S]*?```/g, (match) => {
            const codeContent = match.replace(/```/g, '').trim();
            return `<pre><code>${this.escapeHtml(codeContent)}</code></pre>`;
        });
        
        // Process bold and italic
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Process inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Process strikethrough
        html = html.replace(/~~(.*?)~~/g, '<del>$1</del>');
        
        // Process lists
        html = html.replace(/^\s*[\*\-\+]\s+(.+)$/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
        
        // Process numbered lists
        html = html.replace(/^\s*\d+\.\s+(.+)$/gim, '<li>$1</li>');
        
        // Process blockquotes
        html = html.replace(/^>\s+(.+)$/gim, '<blockquote>$1</blockquote>');
        
        // Process line breaks
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/^/, '<p>').replace(/$/, '</p>');
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }

    /**
     * Escape HTML for safe rendering
     */
    escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }

    /**
     * Basic HTML sanitization (implement proper sanitization in production)
     */
    sanitizeHtml(html) {
        // This is a basic implementation - use a proper HTML sanitizer in production
        return html
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
            .replace(/on\w+="[^"]*"/gi, '')
            .replace(/javascript:/gi, '');
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Simple toast implementation - you might want to use a proper toast library
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
        }, 3000);
    }

    /**
     * Get all artifacts
     */
    getAllArtifacts() {
        return Array.from(this.artifacts.values());
    }

    /**
     * Clear all artifacts
     */
    clearArtifacts() {
        this.artifacts.clear();
        this.hideSidebar();
    }

    /**
     * Update streaming artifact content
     */
    updateStreamingArtifact(artifactId, content) {
        const artifact = this.artifacts.get(artifactId);
        if (!artifact) return;
        
        // Update content
        artifact.content = content;
        artifact.updated = new Date();
        
        // Re-render if currently displayed
        if (this.currentArtifact && this.currentArtifact.id === artifactId) {
            this.renderArtifact(artifact);
        }
    }

    /**
     * Switch between preview and code view
     */
    switchView(artifactId, view) {
        const artifact = this.artifacts.get(artifactId);
        if (!artifact) return;
        
        // Update artifact view mode
        artifact.viewMode = view;
        
        // Update toggle buttons
        const header = this.sidebarContent.querySelector('.artifact-header');
        if (header) {
            const toggleBtns = header.querySelectorAll('.toggle-btn');
            toggleBtns.forEach(btn => {
                btn.classList.toggle('active', btn.dataset.view === view);
            });
        }
        
        // Re-render content with new view
        this.renderArtifact(artifact);
    }

    /**
     * Create code view for any content type
     */
    createCodeView(content, language) {
        const escapedContent = this.escapeHtml(content);
        return `<pre><code class="language-${language}">${escapedContent}</code></pre>`;
    }
}

// Create global instance
window.chatArtifacts = new ChatArtifacts(); 