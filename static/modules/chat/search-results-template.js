/**
 * Search Results Template - Modular component for rendering document search results
 * Supports the artifact format from TypeSense agent
 */

class SearchResultsTemplate {
    constructor() {
        this.templates = {
            'search_results_grid': this.renderSearchResultsGrid.bind(this),
            'document_search_results': this.renderDocumentSearchResults.bind(this)
        };
    }

    /**
     * Render search results based on template type
     */
    render(artifactData, templateType = 'search_results_grid') {
        const renderer = this.templates[templateType];
        if (!renderer) {
            console.warn(`Unknown template type: ${templateType}`);
            return this.renderFallback(artifactData);
        }

        return renderer(artifactData);
    }

    /**
     * Main search results grid template
     */
    renderSearchResultsGrid(data) {
        const { query, totalResults, resultsShown, searchTime, results, facets } = data;

        const container = document.createElement('div');
        container.className = 'search-results-container';

        // Header with search info
        const header = this.createSearchHeader(query, totalResults, resultsShown, searchTime);
        container.appendChild(header);

        // Facets/filters (if available)
        if (facets && Object.keys(facets).length > 0) {
            const facetsContainer = this.createFacetsContainer(facets);
            container.appendChild(facetsContainer);
        }

        // Results grid
        const resultsGrid = this.createResultsGrid(results);
        container.appendChild(resultsGrid);

        return container;
    }

    /**
     * Alternative document search results template
     */
    renderDocumentSearchResults(data) {
        return this.renderSearchResultsGrid(data);
    }

    /**
     * Create search header with query info
     */
    createSearchHeader(query, totalResults, resultsShown, searchTime) {
        const header = document.createElement('div');
        header.className = 'search-header';
        header.innerHTML = `
            <div class="search-summary">
                <h3 class="search-query">
                    <i class="fas fa-search"></i>
                    Search: "${query}"
                </h3>
                <div class="search-stats">
                    <span class="results-count">${totalResults.toLocaleString()} results</span>
                    ${resultsShown < totalResults ? `<span class="results-shown">(showing ${resultsShown})</span>` : ''}
                    <span class="search-time">${searchTime}ms</span>
                </div>
            </div>
        `;
        return header;
    }

    /**
     * Create facets/filters container
     */
    createFacetsContainer(facets) {
        const container = document.createElement('div');
        container.className = 'facets-container';
        
        const facetsHtml = Object.entries(facets).map(([fieldName, counts]) => {
            if (!counts || counts.length === 0) return '';
            
            const facetItems = counts.slice(0, 5).map(item => 
                `<button class="facet-item" data-field="${fieldName}" data-value="${item.value}">
                    ${item.value} (${item.count})
                </button>`
            ).join('');

            return `
                <div class="facet-group">
                    <h4 class="facet-title">${this.formatFieldName(fieldName)}</h4>
                    <div class="facet-items">${facetItems}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div class="facets-header">
                <h4><i class="fas fa-filter"></i> Filters</h4>
                <button class="facets-toggle" onclick="this.parentElement.parentElement.classList.toggle('collapsed')">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
            <div class="facets-content">${facetsHtml}</div>
        `;

        return container;
    }

    /**
     * Create the main results grid
     */
    createResultsGrid(results) {
        const grid = document.createElement('div');
        grid.className = 'results-grid';

        if (!results || results.length === 0) {
            grid.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <h3>No documents found</h3>
                    <p>Try adjusting your search terms or check if documents are properly indexed.</p>
                </div>
            `;
            return grid;
        }

        results.forEach(result => {
            const resultCard = this.createResultCard(result);
            grid.appendChild(resultCard);
        });

        return grid;
    }

    /**
     * Create individual result card
     */
    createResultCard(result) {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.setAttribute('data-result-id', result.id);

        // Determine file icon based on type
        const icon = this.getFileIcon(result.fileType);
        
        // Format date
        const dateStr = this.formatDate(result.createdAt);
        
        // Create tags HTML
        const tagsHtml = result.tags && result.tags.length > 0 
            ? result.tags.slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join('')
            : '';

        card.innerHTML = `
            <div class="result-header">
                <div class="result-icon">
                    <i class="${icon}"></i>
                </div>
                <div class="result-meta">
                    <span class="result-category">${result.category}</span>
                    <span class="result-score">Score: ${(result.score * 100).toFixed(0)}%</span>
                </div>
            </div>
            
            <div class="result-body">
                <h4 class="result-title" ${result.titleHighlight ? `data-highlight="${result.titleHighlight}"` : ''}>
                    ${result.title}
                </h4>
                
                <p class="result-description">
                    ${result.description}
                </p>
                
                ${result.contentSnippet ? `
                    <div class="result-snippet">
                        <i class="fas fa-quote-left"></i>
                        ${result.contentSnippet}
                    </div>
                ` : ''}
                
                ${tagsHtml ? `<div class="result-tags">${tagsHtml}</div>` : ''}
            </div>
            
            <div class="result-footer">
                <div class="result-info">
                    <span class="result-date">
                        <i class="fas fa-calendar"></i>
                        ${dateStr}
                    </span>
                    ${result.metadata.author ? `
                        <span class="result-author">
                            <i class="fas fa-user"></i>
                            ${result.metadata.author}
                        </span>
                    ` : ''}
                    ${result.metadata.size ? `
                        <span class="result-size">
                            <i class="fas fa-file"></i>
                            ${this.formatFileSize(result.metadata.size)}
                        </span>
                    ` : ''}
                </div>
                
                <div class="result-actions">
                    ${result.url ? `
                        <button class="action-button primary" onclick="window.open('${result.url}', '_blank')">
                            <i class="fas fa-external-link-alt"></i>
                            Open
                        </button>
                    ` : ''}
                    ${result.filePath ? `
                        <button class="action-button secondary" onclick="this.copyToClipboard('${result.filePath}')">
                            <i class="fas fa-copy"></i>
                            Copy Path
                        </button>
                    ` : ''}
                    <button class="action-button secondary" onclick="this.showDetails('${result.id}')">
                        <i class="fas fa-info-circle"></i>
                        Details
                    </button>
                </div>
            </div>
        `;

        // Add click handler for card
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.action-button')) {
                this.handleCardClick(result);
            }
        });

        return card;
    }

    /**
     * Get appropriate icon for file type
     */
    getFileIcon(fileType) {
        const iconMap = {
            'pdf': 'fas fa-file-pdf',
            'doc': 'fas fa-file-word',
            'docx': 'fas fa-file-word',
            'txt': 'fas fa-file-alt',
            'md': 'fas fa-file-alt',
            'xls': 'fas fa-file-excel',
            'xlsx': 'fas fa-file-excel',
            'ppt': 'fas fa-file-powerpoint',
            'pptx': 'fas fa-file-powerpoint',
            'image': 'fas fa-file-image',
            'video': 'fas fa-file-video',
            'audio': 'fas fa-file-audio',
            'code': 'fas fa-file-code',
            'html': 'fas fa-file-code',
            'css': 'fas fa-file-code',
            'js': 'fas fa-file-code',
            'json': 'fas fa-file-code',
            'xml': 'fas fa-file-code'
        };

        return iconMap[fileType] || 'fas fa-file';
    }

    /**
     * Format date string
     */
    formatDate(dateStr) {
        if (!dateStr) return 'Unknown date';
        
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (e) {
            return 'Invalid date';
        }
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '';
        
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Format field name for display
     */
    formatFieldName(fieldName) {
        return fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Handle card click - open document
     */
    handleCardClick(result) {
        if (result.url) {
            window.open(result.url, '_blank');
        } else {
            console.log('Opening document:', result);
            // Could trigger a modal or other action
        }
    }

    /**
     * Copy to clipboard functionality
     */
    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copied to clipboard');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showToast('Copied to clipboard');
        });
    }

    /**
     * Show details modal/popup
     */
    showDetails(resultId) {
        console.log('Showing details for:', resultId);
        // Could trigger a modal with full document details
    }

    /**
     * Show toast notification
     */
    showToast(message) {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 2000);
    }

    /**
     * Fallback renderer for unknown templates
     */
    renderFallback(data) {
        const container = document.createElement('div');
        container.className = 'artifact-fallback';
        container.innerHTML = `
            <div class="fallback-header">
                <h3>Search Results</h3>
            </div>
            <pre class="fallback-content">${JSON.stringify(data, null, 2)}</pre>
        `;
        return container;
    }
}

// Global instance for use in chat
window.searchResultsTemplate = new SearchResultsTemplate(); 