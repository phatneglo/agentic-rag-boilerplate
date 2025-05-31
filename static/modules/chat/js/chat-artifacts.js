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
     * Set up event listeners for artifact interactions
     */
    setupEventListeners() {
        // Close sidebar button
        const closeSidebarBtn = document.getElementById('closeSidebarBtn');
        if (closeSidebarBtn) {
            closeSidebarBtn.addEventListener('click', () => this.hideSidebar());
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.sidebar && this.sidebar.classList.contains('show')) {
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

        switch (artifact.type) {
            case 'code':
                content = this.createCodeArtifact(artifact);
                break;
            case 'mermaid':
                content = this.createMermaidArtifact(artifact);
                break;
            case 'html':
                content = this.createHtmlArtifact(artifact);
                break;
            case 'markdown':
                content = this.createMarkdownArtifact(artifact);
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
                <div class="artifact-content">
                    ${content}
                </div>
            </div>
        `;
    }

    /**
     * Create artifact header with title and actions
     */
    createArtifactHeader(artifact) {
        return `
            <div class="artifact-header">
                <div class="artifact-title">${artifact.title}</div>
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
     * Render Mermaid diagram
     */
    async renderMermaidDiagram(artifact) {
        if (!window.mermaid) return;

        const diagramId = `mermaid-${artifact.id}`;
        const element = document.getElementById(diagramId);
        
        if (element) {
            try {
                const { svg } = await mermaid.render(diagramId + '_svg', artifact.content);
                element.innerHTML = svg;
            } catch (error) {
                console.error('Error rendering Mermaid diagram:', error);
                element.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error rendering diagram: ${error.message}
                    </div>
                `;
            }
        }
    }

    /**
     * Show artifacts sidebar
     */
    showSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.add('show');
            this.sidebar.classList.add('slide-in-right');
        }
    }

    /**
     * Hide artifacts sidebar
     */
    hideSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.remove('show');
            this.sidebar.classList.remove('slide-in-right');
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
     * Create artifact button for messages
     */
    createArtifactButton(artifact) {
        const iconClass = this.getArtifactIcon(artifact.type);
        return `
            <div class="artifact-button" onclick="chatArtifacts.showArtifact('${artifact.id}')">
                <i class="${iconClass}"></i>
                <span>${artifact.title}</span>
            </div>
        `;
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
     * Convert markdown to HTML
     */
    markdownToHtml(markdown) {
        if (window.marked) {
            return marked.parse(markdown);
        }
        
        // Simple fallback markdown conversion
        return markdown
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
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
}

// Create global instance
window.chatArtifacts = new ChatArtifacts(); 