import { scrollToBottom, showThinkingIndicator, hideThinkingIndicator, addOrUpdateMessage } from './chat-utils.js';

class ChatMessages {
    constructor() {
        this.messagesContainer = document.getElementById('chat-messages');
        this.currentMessage = null;
        this.isStreaming = false;
        this.currentAgents = new Map(); // Track current agent responses
        this.streamingContent = '';
        this.artifacts = [];
    }

    addUserMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(content)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    startAssistantMessage() {
        if (this.currentMessage) return;
        
        this.currentMessage = document.createElement('div');
        this.currentMessage.className = 'message assistant-message streaming';
        this.currentMessage.innerHTML = `
            <div class="message-content">
                <div class="agent-responses"></div>
                <div class="message-text"></div>
            </div>
        `;
        
        this.messagesContainer.appendChild(this.currentMessage);
        this.isStreaming = true;
        this.streamingContent = '';
        this.artifacts = [];
        this.currentAgents.clear();
        scrollToBottom();
    }

    handleAgentThinking(data) {
        const { agent, status } = data;
        
        if (!this.currentMessage) {
            this.startAssistantMessage();
        }

        // Update or create agent thinking indicator
        let agentSection = this.getOrCreateAgentSection(agent);
        let thinkingDiv = agentSection.querySelector('.agent-thinking');
        
        if (!thinkingDiv) {
            thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'agent-thinking';
            agentSection.appendChild(thinkingDiv);
        }

        thinkingDiv.innerHTML = `
            <div class="thinking-indicator">
                <span class="agent-name">${this.getAgentIcon(agent)} ${agent}</span>
                <span class="thinking-dots">●●●</span>
                <span class="thinking-text">${status}</span>
            </div>
        `;

        scrollToBottom();
    }

    handleAgentContentChunk(data) {
        const { agent, content, is_final } = data;
        
        if (!this.currentMessage) {
            this.startAssistantMessage();
        }

        let agentSection = this.getOrCreateAgentSection(agent);
        
        // Remove thinking indicator when content starts
        const thinkingDiv = agentSection.querySelector('.agent-thinking');
        if (thinkingDiv) {
            thinkingDiv.remove();
        }

        // Get or create content div
        let contentDiv = agentSection.querySelector('.agent-content');
        if (!contentDiv) {
            contentDiv = document.createElement('div');
            contentDiv.className = 'agent-content';
            agentSection.appendChild(contentDiv);
        }

        // Update content
        const currentContent = this.currentAgents.get(agent) || '';
        const newContent = currentContent + content + ' ';
        this.currentAgents.set(agent, newContent);
        
        contentDiv.innerHTML = `
            <div class="agent-header">
                <span class="agent-name">${this.getAgentIcon(agent)} ${agent} Agent</span>
            </div>
            <div class="agent-text">${this.escapeHtml(newContent.trim())}</div>
        `;

        if (is_final) {
            agentSection.classList.add('completed');
        }

        scrollToBottom();
    }

    handleAgentArtifactStart(data) {
        const { agent, artifact } = data;
        
        if (!this.currentMessage) {
            this.startAssistantMessage();
        }

        let agentSection = this.getOrCreateAgentSection(agent);
        
        // Create artifact container
        const artifactDiv = document.createElement('div');
        artifactDiv.className = 'agent-artifact streaming';
        artifactDiv.setAttribute('data-artifact-id', artifact.id);
        
        artifactDiv.innerHTML = `
            <div class="artifact-header">
                <span class="artifact-title">${artifact.title}</span>
                <span class="artifact-type">${artifact.type}</span>
            </div>
            <div class="artifact-content">
                <div class="artifact-loading">Creating ${artifact.type}...</div>
            </div>
        `;
        
        agentSection.appendChild(artifactDiv);
        scrollToBottom();
    }

    handleAgentArtifactChunk(data) {
        const { agent, artifact_id, content, is_final } = data;
        
        const artifactDiv = this.currentMessage.querySelector(`[data-artifact-id="${artifact_id}"]`);
        if (!artifactDiv) return;

        const contentDiv = artifactDiv.querySelector('.artifact-content');
        const loadingDiv = contentDiv.querySelector('.artifact-loading');
        
        if (loadingDiv) {
            loadingDiv.remove();
            // Create the actual content container
            const actualContent = document.createElement('div');
            actualContent.className = 'artifact-actual-content';
            contentDiv.appendChild(actualContent);
        }

        const actualContentDiv = contentDiv.querySelector('.artifact-actual-content');
        actualContentDiv.textContent += content;

        if (is_final) {
            artifactDiv.classList.remove('streaming');
            artifactDiv.classList.add('completed');
            // Trigger proper rendering based on type
            this.renderArtifactContent(artifactDiv, actualContentDiv.textContent);
        }

        scrollToBottom();
    }

    handleAgentError(data) {
        const { agent, error } = data;
        
        if (!this.currentMessage) {
            this.startAssistantMessage();
        }

        let agentSection = this.getOrCreateAgentSection(agent);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'agent-error';
        errorDiv.innerHTML = `
            <div class="agent-header">
                <span class="agent-name">${this.getAgentIcon(agent)} ${agent} Agent</span>
            </div>
            <div class="error-text">❌ ${error}</div>
        `;
        
        agentSection.appendChild(errorDiv);
        scrollToBottom();
    }

    getOrCreateAgentSection(agent) {
        if (!this.currentMessage) return null;

        const agentResponsesDiv = this.currentMessage.querySelector('.agent-responses');
        let agentSection = agentResponsesDiv.querySelector(`[data-agent="${agent}"]`);
        
        if (!agentSection) {
            agentSection = document.createElement('div');
            agentSection.className = 'agent-section';
            agentSection.setAttribute('data-agent', agent);
            agentResponsesDiv.appendChild(agentSection);
        }

        return agentSection;
    }

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

    renderArtifactContent(artifactDiv, content) {
        const artifactType = artifactDiv.querySelector('.artifact-type').textContent;
        const contentDiv = artifactDiv.querySelector('.artifact-actual-content');
        
        switch (artifactType) {
            case 'code':
                this.renderCodeArtifact(contentDiv, content);
                break;
            case 'mermaid':
                this.renderMermaidArtifact(contentDiv, content);
                break;
            case 'markdown':
                this.renderMarkdownArtifact(contentDiv, content);
                break;
            default:
                contentDiv.innerHTML = `<pre>${this.escapeHtml(content)}</pre>`;
        }
    }

    renderCodeArtifact(container, content) {
        container.innerHTML = `
            <div class="artifact-controls">
                <button class="toggle-view" data-view="preview">Preview</button>
                <button class="toggle-view active" data-view="code">Code</button>
            </div>
            <div class="artifact-body">
                <div class="code-view active">
                    <pre><code class="language-python">${this.escapeHtml(content)}</code></pre>
                </div>
                <div class="preview-view">
                    <div class="code-output">Ready to run Python code</div>
                </div>
            </div>
        `;
        
        // Add toggle functionality
        this.addArtifactToggleListeners(container);
        
        // Apply syntax highlighting
        if (window.Prism) {
            window.Prism.highlightAllUnder(container);
        }
    }

    renderMermaidArtifact(container, content) {
        container.innerHTML = `
            <div class="artifact-controls">
                <button class="toggle-view active" data-view="preview">Preview</button>
                <button class="toggle-view" data-view="code">Code</button>
            </div>
            <div class="artifact-body">
                <div class="preview-view active">
                    <div class="mermaid-container">
                        <div class="mermaid">${content}</div>
                    </div>
                </div>
                <div class="code-view">
                    <pre><code class="language-mermaid">${this.escapeHtml(content)}</code></pre>
                </div>
            </div>
        `;
        
        this.addArtifactToggleListeners(container);
        this.renderMermaidDiagram(container);
    }

    renderMarkdownArtifact(container, content) {
        container.innerHTML = `
            <div class="artifact-controls">
                <button class="toggle-view active" data-view="preview">Preview</button>
                <button class="toggle-view" data-view="code">Code</button>
            </div>
            <div class="artifact-body">
                <div class="preview-view active">
                    <div class="markdown-content">${this.renderMarkdown(content)}</div>
                </div>
                <div class="code-view">
                    <pre><code class="language-markdown">${this.escapeHtml(content)}</code></pre>
                </div>
            </div>
        `;
        
        this.addArtifactToggleListeners(container);
    }

    addArtifactToggleListeners(container) {
        const toggleButtons = container.querySelectorAll('.toggle-view');
        const views = container.querySelectorAll('.preview-view, .code-view');
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetView = button.getAttribute('data-view');
                
                // Update button states
                toggleButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Update view states
                views.forEach(view => {
                    view.classList.remove('active');
                    if (view.classList.contains(`${targetView}-view`)) {
                        view.classList.add('active');
                    }
                });
            });
        });
    }

    renderMermaidDiagram(container) {
        if (window.mermaid) {
            try {
                const mermaidDiv = container.querySelector('.mermaid');
                if (mermaidDiv) {
                    window.mermaid.init(undefined, mermaidDiv);
                }
            } catch (error) {
                console.error('Mermaid rendering error:', error);
                const mermaidContainer = container.querySelector('.mermaid-container');
                mermaidContainer.innerHTML = '<div class="mermaid-error">Error rendering diagram</div>';
            }
        }
    }

    renderMarkdown(content) {
        // Simple markdown renderer
        return content
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    completeAssistantMessage(data) {
        if (!this.currentMessage) return;
        
        // Remove streaming class and finalize
        this.currentMessage.classList.remove('streaming');
        this.currentMessage.classList.add('completed');
        
        // Clean up any remaining thinking indicators
        const thinkingDivs = this.currentMessage.querySelectorAll('.agent-thinking');
        thinkingDivs.forEach(div => div.remove());
        
        // Mark all agent sections as completed
        const agentSections = this.currentMessage.querySelectorAll('.agent-section');
        agentSections.forEach(section => section.classList.add('completed'));
        
        this.currentMessage = null;
        this.isStreaming = false;
        this.currentAgents.clear();
        scrollToBottom();
    }

    addErrorMessage(error) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message error';
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">❌ ${this.escapeHtml(error)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    clearMessages() {
        this.messagesContainer.innerHTML = '';
        this.currentMessage = null;
        this.isStreaming = false;
        this.currentAgents.clear();
    }
}

export default ChatMessages; 