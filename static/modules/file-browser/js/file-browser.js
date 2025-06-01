/**
 * File Browser JavaScript - Modern Knowledge Base Browser
 * Integrates with Typesense search API for intelligent document discovery
 */

class FileBrowser {
    constructor() {
        this.apiEndpoint = window.location.origin;
        this.currentQuery = '';
        this.currentFilters = {};
        this.currentSort = 'created_at:desc';
        this.currentPage = 1;
        this.perPage = 12;
        this.currentViewMode = 'list';
        this.searchTimeout = null;
        this.facetCounts = {};
        this.isSearching = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupViewModeToggle();
        this.setupSortingOptions();
        this.setupSearchFunctionality();
        this.showEmptyState();
        this.loadInitialFilters();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', this.debounceSearch.bind(this));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.performSearch();
            }
        });

        // Search clear button
        document.getElementById('searchClear').addEventListener('click', this.clearSearch.bind(this));

        // Browse all button
        document.getElementById('browseAll').addEventListener('click', this.browseAllDocuments.bind(this));

        // Filter management
        document.getElementById('clearFilters').addEventListener('click', this.clearFilters.bind(this));
        document.getElementById('clearAllFilters').addEventListener('click', this.clearAllFilters.bind(this));

        // Vector search toggle
        document.getElementById('vectorSearchToggle').addEventListener('change', this.performSearch.bind(this));

        // View mode toggles
        document.getElementById('gridView').addEventListener('click', () => this.setViewMode('grid'));
        document.getElementById('listView').addEventListener('click', () => this.setViewMode('list'));

        // Sort options
        document.querySelectorAll('#sortOptions .dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.setSortOrder(item.dataset.sort);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
    }

    handleKeyboardShortcuts(e) {
        // Focus search on Ctrl/Cmd + K
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('searchInput').focus();
        }
        
        // Clear search on Escape
        if (e.key === 'Escape') {
            this.clearSearch();
        }
    }

    setupViewModeToggle() {
        const gridView = document.getElementById('gridView');
        const listView = document.getElementById('listView');
        
        // Load saved preference
        const savedViewMode = localStorage.getItem('fileBrowser_viewMode') || 'list';
        this.setViewMode(savedViewMode);
    }

    setViewMode(mode) {
        this.currentViewMode = mode;
        
        const gridView = document.getElementById('gridView');
        const listView = document.getElementById('listView');
        const resultsContainer = document.getElementById('documentResults');
        
        // Update button states
        gridView.classList.toggle('active', mode === 'grid');
        listView.classList.toggle('active', mode === 'list');
        
        // Update results display
        if (resultsContainer) {
            resultsContainer.className = `document-results ${mode}-view`;
        }
        
        // Save preference
        localStorage.setItem('fileBrowser_viewMode', mode);
        
        // Re-render current results
        this.renderDocuments();
    }

    setupSortingOptions() {
        // Load saved sorting preference
        const savedSort = localStorage.getItem('fileBrowser_sortOrder') || 'created_at:desc';
        this.setSortOrder(savedSort);
    }

    setSortOrder(sortOrder) {
        this.currentSort = sortOrder;
        
        // Update dropdown display
        const sortButton = document.querySelector('[data-bs-toggle="dropdown"]');
        const selectedOption = document.querySelector(`[data-sort="${sortOrder}"]`);
        
        if (selectedOption) {
            sortButton.innerHTML = `<i class="fas fa-sort me-1"></i>${selectedOption.textContent}`;
        }
        
        // Save preference
        localStorage.setItem('fileBrowser_sortOrder', sortOrder);
        
        // Perform search with new sort order
        if (this.currentQuery || Object.keys(this.currentFilters).length > 0) {
            this.performSearch();
        }
    }

    setupSearchFunctionality() {
        const searchInput = document.getElementById('searchInput');
        const searchClear = document.getElementById('searchClear');
        
        // Show/hide clear button based on input
        searchInput.addEventListener('input', (e) => {
            searchClear.style.display = e.target.value ? 'block' : 'none';
        });
    }

    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch();
        }, 300);
    }

    async performSearch() {
        if (this.isSearching) return;
        
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();
        
        // Don't search if query is empty and no filters are active
        if (!query && Object.keys(this.currentFilters).length === 0) {
            this.showEmptyState();
            return;
        }
        
        this.currentQuery = query || '*';
        this.currentPage = 1;
        
        this.showLoadingState();
        
        try {
            this.isSearching = true;
            const results = await this.searchDocuments();
            
            if (results.success) {
                this.handleSearchResults(results);
            } else {
                this.showErrorState('Search failed. Please try again.');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showErrorState('An error occurred while searching. Please try again.');
        } finally {
            this.isSearching = false;
        }
    }

    async searchDocuments() {
        const vectorSearch = document.getElementById('vectorSearchToggle').checked;
        
        const params = new URLSearchParams({
            q: this.currentQuery,
            query_by: 'title,description,summary',
            facet_by: 'type,category,language,authors,tags',
            sort_by: this.currentSort,
            page: this.currentPage,
            per_page: this.perPage,
            include_facet_counts: true,
            highlight_full_fields: 'title,description,summary',
            use_vector_search: vectorSearch
        });
        
        // Add active filters
        if (Object.keys(this.currentFilters).length > 0) {
            const filterConditions = [];
            for (const [field, values] of Object.entries(this.currentFilters)) {
                if (values.length > 0) {
                    if (values.length === 1) {
                        filterConditions.push(`${field}:=${values[0]}`);
                    } else {
                        filterConditions.push(`${field}:[${values.join(',')}]`);
                    }
                }
            }
            if (filterConditions.length > 0) {
                params.set('filter_by', filterConditions.join(' && '));
            }
        }
        
        const response = await fetch(`${this.apiEndpoint}/api/v1/documents/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    handleSearchResults(results) {
        this.lastResults = results;
        this.facetCounts = this.processFacetCounts(results.facet_counts);
        
        this.updateSearchStats(results);
        this.updateFacetFilters(this.facetCounts);
        this.renderDocuments();
        this.renderPagination(results);
        
        // Show results container
        this.showResults();
    }

    processFacetCounts(facetCounts) {
        const processed = {};
        
        if (Array.isArray(facetCounts)) {
            facetCounts.forEach(facet => {
                if (facet.field_name && facet.counts) {
                    processed[facet.field_name] = facet.counts.map(count => ({
                        value: count.value,
                        count: count.count
                    }));
                }
            });
        }
        
        return processed;
    }

    updateSearchStats(results) {
        const searchStats = document.getElementById('searchStats');
        const searchStatsText = document.getElementById('searchStatsText');
        const searchTime = document.getElementById('searchTime');
        
        if (results.found !== undefined) {
            const foundText = results.found === 1 ? '1 document found' : `${results.found.toLocaleString()} documents found`;
            searchStatsText.textContent = foundText;
            searchTime.textContent = results.search_time_ms || 0;
            searchStats.style.display = 'block';
        }
    }

    updateFacetFilters(facetCounts) {
        // Update each filter section
        this.updateFilterSection('type', 'typeFilterOptions', facetCounts.type || []);
        this.updateFilterSection('category', 'categoryFilterOptions', facetCounts.category || []);
        this.updateFilterSection('language', 'languageFilterOptions', facetCounts.language || []);
        this.updateFilterSection('authors', 'authorFilterOptions', facetCounts.authors || []);
        this.updateFilterSection('tags', 'tagsFilterOptions', facetCounts.tags || []);
        
        this.updateActiveFiltersDisplay();
    }

    updateFilterSection(fieldName, containerId, counts) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = '';
        
        if (counts.length === 0) {
            container.innerHTML = '<p class="text-muted small">No options available</p>';
            return;
        }
        
        counts.forEach(item => {
            const isActive = this.currentFilters[fieldName]?.includes(item.value) || false;
            
            const filterOption = document.createElement('div');
            filterOption.className = `filter-option ${isActive ? 'active' : ''}`;
            filterOption.innerHTML = `
                <span class="filter-option-label">${this.formatFilterValue(fieldName, item.value)}</span>
                <span class="filter-option-count">${item.count}</span>
            `;
            
            filterOption.addEventListener('click', () => {
                this.toggleFilter(fieldName, item.value);
            });
            
            container.appendChild(filterOption);
        });
    }

    formatFilterValue(fieldName, value) {
        // Format filter values for better display
        if (fieldName === 'type') {
            return value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        return value;
    }

    toggleFilter(fieldName, value) {
        if (!this.currentFilters[fieldName]) {
            this.currentFilters[fieldName] = [];
        }
        
        const index = this.currentFilters[fieldName].indexOf(value);
        if (index > -1) {
            this.currentFilters[fieldName].splice(index, 1);
            if (this.currentFilters[fieldName].length === 0) {
                delete this.currentFilters[fieldName];
            }
        } else {
            this.currentFilters[fieldName].push(value);
        }
        
        this.performSearch();
    }

    updateActiveFiltersDisplay() {
        const activeFilters = document.getElementById('activeFilters');
        const activeFiltersList = document.getElementById('activeFiltersList');
        
        const hasActiveFilters = Object.keys(this.currentFilters).length > 0;
        activeFilters.style.display = hasActiveFilters ? 'block' : 'none';
        
        if (!hasActiveFilters) return;
        
        activeFiltersList.innerHTML = '';
        
        for (const [fieldName, values] of Object.entries(this.currentFilters)) {
            values.forEach(value => {
                const pill = document.createElement('span');
                pill.className = 'active-filter-pill';
                pill.innerHTML = `
                    ${this.formatFilterValue(fieldName, value)}
                    <i class="fas fa-times remove-filter" data-field="${fieldName}" data-value="${value}"></i>
                `;
                
                pill.querySelector('.remove-filter').addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleFilter(fieldName, value);
                });
                
                activeFiltersList.appendChild(pill);
            });
        }
    }

    renderDocuments() {
        const container = document.getElementById('documentResults');
        if (!container || !this.lastResults) return;
        
        container.innerHTML = '';
        
        if (this.lastResults.documents.length === 0) {
            this.showNoResultsState();
            return;
        }
        
        this.lastResults.documents.forEach((doc, index) => {
            const documentCard = this.createDocumentCard(doc, index);
            container.appendChild(documentCard);
        });
    }

    createDocumentCard(doc, index) {
        const card = document.createElement('div');
        card.className = `document-card ${this.currentViewMode}-view`;
        
        const typeIcon = this.getTypeIcon(doc.type);
        const formattedDate = this.formatDate(doc.created_at);
        const highlights = this.processHighlights(doc.highlights);
        
        card.innerHTML = `
            <div class="document-icon type-${doc.type}">
                <i class="fas ${typeIcon}"></i>
            </div>
            <div class="document-content">
                <h5 class="document-title">${highlights.title || doc.title}</h5>
                <p class="document-description">${highlights.description || doc.description}</p>
                <div class="document-meta">
                    <span class="document-meta-item">
                        <i class="fas fa-calendar"></i>
                        ${formattedDate}
                    </span>
                    <span class="document-meta-item">
                        <i class="fas fa-file-word"></i>
                        ${doc.word_count.toLocaleString()} words
                    </span>
                    ${doc.page_count ? `
                        <span class="document-meta-item">
                            <i class="fas fa-file-alt"></i>
                            ${doc.page_count} pages
                        </span>
                    ` : ''}
                    ${doc.language !== 'en' ? `
                        <span class="document-meta-item">
                            <i class="fas fa-globe"></i>
                            ${doc.language.toUpperCase()}
                        </span>
                    ` : ''}
                    ${doc.score > 0 ? `
                        <span class="document-score">${Math.round(doc.score * 100)}% match</span>
                    ` : ''}
                </div>
                ${doc.tags.length > 0 ? `
                    <div class="document-tags">
                        ${doc.tags.slice(0, 5).map(tag => `
                            <span class="document-tag" data-tag="${tag}">${tag}</span>
                        `).join('')}
                        ${doc.tags.length > 5 ? `<span class="document-tag">+${doc.tags.length - 5} more</span>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
        
        // Add click handlers
        card.addEventListener('click', () => this.openDocumentPreview(doc));
        
        // Add tag click handlers
        card.querySelectorAll('.document-tag[data-tag]').forEach(tagElement => {
            tagElement.addEventListener('click', (e) => {
                e.stopPropagation();
                this.searchByTag(tagElement.dataset.tag);
            });
        });
        
        return card;
    }

    getTypeIcon(type) {
        const iconMap = {
            'document': 'fa-file-alt',
            'academic_paper': 'fa-graduation-cap',
            'report': 'fa-chart-line',
            'manual': 'fa-book',
            'presentation': 'fa-presentation',
            'policy': 'fa-gavel',
            'webpage': 'fa-globe'
        };
        return iconMap[type] || 'fa-file';
    }

    formatDate(timestamp) {
        if (!timestamp) return 'Unknown date';
        
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
        if (diffDays < 365) return `${Math.ceil(diffDays / 30)} months ago`;
        
        return date.toLocaleDateString();
    }

    processHighlights(highlights) {
        const processed = {};
        
        if (Array.isArray(highlights)) {
            highlights.forEach(highlight => {
                if (highlight.field && highlight.snippet) {
                    processed[highlight.field] = highlight.snippet;
                }
            });
        }
        
        return processed;
    }

    renderPagination(results) {
        const paginationContainer = document.getElementById('paginationContainer');
        const pagination = document.getElementById('pagination');
        
        if (results.total_pages <= 1) {
            paginationContainer.style.display = 'none';
            return;
        }
        
        paginationContainer.style.display = 'block';
        pagination.innerHTML = '';
        
        const totalPages = results.total_pages;
        const currentPage = this.currentPage;
        
        // Previous button
        const prevItem = document.createElement('li');
        prevItem.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevItem.innerHTML = `<a class="page-link" href="#" aria-label="Previous">
            <i class="fas fa-chevron-left"></i>
        </a>`;
        if (currentPage > 1) {
            prevItem.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToPage(currentPage - 1);
            });
        }
        pagination.appendChild(prevItem);
        
        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            pagination.appendChild(this.createPageItem(1));
            if (startPage > 2) {
                const ellipsis = document.createElement('li');
                ellipsis.className = 'page-item disabled';
                ellipsis.innerHTML = '<span class="page-link">...</span>';
                pagination.appendChild(ellipsis);
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            pagination.appendChild(this.createPageItem(i, i === currentPage));
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                const ellipsis = document.createElement('li');
                ellipsis.className = 'page-item disabled';
                ellipsis.innerHTML = '<span class="page-link">...</span>';
                pagination.appendChild(ellipsis);
            }
            pagination.appendChild(this.createPageItem(totalPages));
        }
        
        // Next button
        const nextItem = document.createElement('li');
        nextItem.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextItem.innerHTML = `<a class="page-link" href="#" aria-label="Next">
            <i class="fas fa-chevron-right"></i>
        </a>`;
        if (currentPage < totalPages) {
            nextItem.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToPage(currentPage + 1);
            });
        }
        pagination.appendChild(nextItem);
    }

    createPageItem(pageNumber, isActive = false) {
        const item = document.createElement('li');
        item.className = `page-item ${isActive ? 'active' : ''}`;
        item.innerHTML = `<a class="page-link" href="#">${pageNumber}</a>`;
        
        if (!isActive) {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToPage(pageNumber);
            });
        }
        
        return item;
    }

    goToPage(page) {
        this.currentPage = page;
        this.performSearch();
        
        // Scroll to top of results
        document.getElementById('searchStats').scrollIntoView({ behavior: 'smooth' });
    }

    openDocumentPreview(doc) {
        const modal = new bootstrap.Modal(document.getElementById('documentModal'));
        const modalTitle = document.getElementById('documentModalTitle');
        const modalBody = document.getElementById('documentModalBody');
        
        modalTitle.textContent = doc.title;
        
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Document Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Type:</strong></td><td>${this.formatFilterValue('type', doc.type)}</td></tr>
                        <tr><td><strong>Category:</strong></td><td>${doc.category}</td></tr>
                        <tr><td><strong>Language:</strong></td><td>${doc.language.toUpperCase()}</td></tr>
                        <tr><td><strong>Word Count:</strong></td><td>${doc.word_count.toLocaleString()}</td></tr>
                        ${doc.page_count ? `<tr><td><strong>Pages:</strong></td><td>${doc.page_count}</td></tr>` : ''}
                        <tr><td><strong>Created:</strong></td><td>${this.formatDate(doc.created_at)}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Description</h6>
                    <p>${doc.description}</p>
                    ${doc.summary ? `
                        <h6>Summary</h6>
                        <p>${doc.summary}</p>
                    ` : ''}
                </div>
            </div>
            ${doc.authors.length > 0 ? `
                <div class="mt-3">
                    <h6>Authors</h6>
                    <p>${doc.authors.join(', ')}</p>
                </div>
            ` : ''}
            ${doc.tags.length > 0 ? `
                <div class="mt-3">
                    <h6>Tags</h6>
                    <div class="d-flex flex-wrap gap-1">
                        ${doc.tags.map(tag => `<span class="badge bg-primary">${tag}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        
        modal.show();
    }

    searchByTag(tag) {
        this.toggleFilter('tags', tag);
    }

    clearSearch() {
        const searchInput = document.getElementById('searchInput');
        const searchClear = document.getElementById('searchClear');
        
        searchInput.value = '';
        searchClear.style.display = 'none';
        this.currentQuery = '';
        
        if (Object.keys(this.currentFilters).length === 0) {
            this.showEmptyState();
        } else {
            this.performSearch();
        }
    }

    clearFilters() {
        this.currentFilters = {};
        this.updateActiveFiltersDisplay();
        
        if (this.currentQuery) {
            this.performSearch();
        } else {
            this.showEmptyState();
        }
    }

    clearAllFilters() {
        this.clearSearch();
        this.clearFilters();
    }

    browseAllDocuments() {
        this.currentQuery = '*';
        this.performSearch();
    }

    async loadInitialFilters() {
        try {
            // Load facet counts to populate filters even before search
            const results = await this.searchDocuments();
            if (results.success && results.facet_counts) {
                this.facetCounts = this.processFacetCounts(results.facet_counts);
                this.updateFacetFilters(this.facetCounts);
            }
        } catch (error) {
            console.warn('Could not load initial filter options:', error);
        }
    }

    // State management methods
    showEmptyState() {
        this.hideAllStates();
        document.getElementById('emptyState').style.display = 'block';
    }

    showLoadingState() {
        this.hideAllStates();
        document.getElementById('loadingState').style.display = 'block';
    }

    showNoResultsState() {
        this.hideAllStates();
        document.getElementById('noResultsState').style.display = 'block';
    }

    showResults() {
        this.hideAllStates();
        document.getElementById('resultsContainer').style.display = 'block';
    }

    showErrorState(message) {
        this.hideAllStates();
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger text-center';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button class="btn btn-outline-danger btn-sm ms-3" onclick="location.reload()">
                <i class="fas fa-sync-alt me-1"></i>Retry
            </button>
        `;
        
        const main = document.querySelector('main');
        main.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
            this.showEmptyState();
        }, 5000);
    }

    hideAllStates() {
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('noResultsState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'none';
        document.getElementById('searchStats').style.display = 'none';
    }
}

// Initialize the File Browser when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.fileBrowser = new FileBrowser();
    
    // Expose some methods globally for debugging
    window.FB = {
        search: (query) => {
            document.getElementById('searchInput').value = query;
            window.fileBrowser.performSearch();
        },
        filter: (field, value) => window.fileBrowser.toggleFilter(field, value),
        clear: () => window.fileBrowser.clearAllFilters(),
        browse: () => window.fileBrowser.browseAllDocuments()
    };
    
    console.log('🔍 File Browser initialized! Try window.FB for debugging.');
}); 