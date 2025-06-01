/**
 * Dashboard JavaScript - Agentic RAG Management Dashboard
 * Handles navigation, API health monitoring, and real-time updates
 */

class Dashboard {
    constructor() {
        this.currentSection = 'dashboard';
        this.apiEndpoint = window.location.origin;
        this.healthCheckInterval = null;
        this.activityUpdateInterval = null;
        this.fileBrowser = null;
        this.currentQuery = '';
        this.currentFilters = {};
        this.currentSort = 'created_at:desc';
        this.currentPage = 1;
        this.perPage = 12;
        this.currentViewMode = 'list';
        this.currentSearchMode = 'normal'; // 'normal' or 'smart'
        this.searchTimeout = null;
        this.facetCounts = {};
        this.isSearching = false;
        this.lastResults = null;
        
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupAPIHealthMonitoring();
        this.loadInitialData();
        this.startPeriodicUpdates();
        
        // Set initial active state
        this.showSection('dashboard');
    }

    setupNavigation() {
        // Navigation click handlers
        document.getElementById('dashboard-nav').addEventListener('click', (e) => {
            e.preventDefault();
            this.showSection('dashboard');
        });

        document.getElementById('chat-nav').addEventListener('click', (e) => {
            e.preventDefault();
            this.showSection('chat');
        });

        document.getElementById('file-manager-nav').addEventListener('click', (e) => {
            e.preventDefault();
            this.showSection('file-manager');
        });

        document.getElementById('file-browser-nav').addEventListener('click', (e) => {
            e.preventDefault();
            this.showSection('file-browser');
        });

        // Top navbar links
        document.querySelectorAll('a[href="#dashboard"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.showSection('dashboard');
            });
        });

        document.querySelectorAll('a[href="#file-manager"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.showSection('file-manager');
            });
        });
    }

    showSection(section) {
        // Hide all sections
        document.getElementById('dashboard-content').classList.add('d-none');
        document.getElementById('chat-content').classList.add('d-none');
        document.getElementById('file-manager-content').classList.add('d-none');
        document.getElementById('file-browser-content').classList.add('d-none');
        
        // Update navigation active states
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Show selected section and update nav
        switch(section) {
            case 'dashboard':
                document.getElementById('dashboard-content').classList.remove('d-none');
                document.getElementById('dashboard-nav').classList.add('active');
                break;
            case 'chat':
                document.getElementById('chat-content').classList.remove('d-none');
                document.getElementById('chat-nav').classList.add('active');
                this.loadChat();
                break;
            case 'file-manager':
                document.getElementById('file-manager-content').classList.remove('d-none');
                document.getElementById('file-manager-nav').classList.add('active');
                this.loadFileManager();
                break;
            case 'file-browser':
                document.getElementById('file-browser-content').classList.remove('d-none');
                document.getElementById('file-browser-nav').classList.add('active');
                this.loadFileBrowser();
                break;
        }
        
        this.currentSection = section;
    }

    loadFileManager() {
        const iframe = document.getElementById('file-manager-frame');
        if (iframe && !iframe.src.includes('index.html')) {
            iframe.src = '/static/modules/file-manager/index.html';
        }
    }

    loadFileBrowser() {
        // Initialize FileBrowser if not already done
        if (!this.fileBrowser) {
            this.fileBrowser = new FileBrowser();
        }
    }

    loadChat() {
        const iframe = document.getElementById('chat-frame');
        if (iframe && !iframe.src.includes('chat')) {
            iframe.src = '/chat';
        }
    }

    async setupAPIHealthMonitoring() {
        try {
            await this.checkAPIHealth();
        } catch (error) {
            console.error('Error setting up API health monitoring:', error);
            this.updateAPIStatus('offline', 'Error checking API status');
        }
    }

    async checkAPIHealth() {
        const startTime = Date.now();
        
        try {
            // Check main API health
            const response = await fetch(`${this.apiEndpoint}/health`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
                timeout: 5000
            });

            const responseTime = Date.now() - startTime;
            
            if (response.ok) {
                const healthData = await response.json();
                this.updateAPIStatus('online', `${responseTime}ms`);
                this.updateDashboardMetrics(healthData, responseTime);
                this.updateHealthStatusTable(healthData);
            } else {
                this.updateAPIStatus('warning', `${response.status}`);
            }
        } catch (error) {
            console.error('API health check failed:', error);
            this.updateAPIStatus('offline', 'Connection failed');
            this.updateDashboardMetrics(null, null);
        }
    }

    updateAPIStatus(status, message) {
        const statusElement = document.getElementById('api-status');
        
        statusElement.className = 'badge';
        statusElement.innerHTML = `<i class="fas fa-circle"></i> `;
        
        switch (status) {
            case 'online':
                statusElement.classList.add('bg-success');
                statusElement.innerHTML += `Online (${message})`;
                break;
            case 'warning':
                statusElement.classList.add('bg-warning');
                statusElement.innerHTML += `Warning (${message})`;
                break;
            case 'offline':
                statusElement.classList.add('bg-danger');
                statusElement.innerHTML += `Offline (${message})`;
                break;
            default:
                statusElement.classList.add('bg-secondary');
                statusElement.innerHTML += message;
        }
    }

    updateDashboardMetrics(healthData, responseTime) {
        // Update response time
        const responseTimeElement = document.getElementById('response-time');
        if (responseTime !== null) {
            responseTimeElement.textContent = `${responseTime}ms`;
            responseTimeElement.classList.remove('pulse');
        } else {
            responseTimeElement.textContent = '--';
            responseTimeElement.classList.add('pulse');
        }

        // Update other metrics from health data
        if (healthData) {
            this.updateMetric('file-count', healthData.file_count || '--');
            this.updateMetric('storage-used', this.formatBytes(healthData.storage_used || 0));
            // Update system uptime in health details instead
            const healthDetails = document.getElementById('health-details');
            if (healthDetails) {
                healthDetails.innerHTML = `
                    <div class="row">
                        <div class="col-sm-6">
                            <strong>Uptime:</strong> ${this.formatUptime(healthData.uptime || 0)}
                        </div>
                        <div class="col-sm-6">
                            <strong>Status:</strong> <span class="badge badge-success">Online</span>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-sm-6">
                            <strong>Files:</strong> ${healthData.file_count || 0}
                        </div>
                        <div class="col-sm-6">
                            <strong>Storage:</strong> ${this.formatBytes(healthData.storage_used || 0)}
                        </div>
                    </div>
                `;
            }
        } else {
            this.updateMetric('file-count', '--');
            this.updateMetric('storage-used', '--');
            const healthDetails = document.getElementById('health-details');
            if (healthDetails) {
                healthDetails.innerHTML = '<p class="text-danger">Unable to fetch health information</p>';
            }
        }
    }

    updateMetric(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    updateHealthStatusTable(healthData) {
        const tableBody = document.getElementById('health-status-table');
        if (!tableBody) return;

        const services = [
            {
                name: 'API Server',
                status: healthData ? 'online' : 'offline',
                lastCheck: new Date().toLocaleTimeString()
            },
            {
                name: 'File Storage',
                status: healthData?.storage_status || 'unknown',
                lastCheck: new Date().toLocaleTimeString()
            },
            {
                name: 'Database',
                status: healthData?.database_status || 'unknown',
                lastCheck: new Date().toLocaleTimeString()
            }
        ];

        tableBody.innerHTML = services.map(service => `
            <tr>
                <td>${service.name}</td>
                <td>
                    <span class="status-indicator ${service.status}">
                        <i class="fas fa-circle"></i>
                        ${service.status.charAt(0).toUpperCase() + service.status.slice(1)}
                    </span>
                </td>
                <td>${service.lastCheck}</td>
            </tr>
        `).join('');
    }

    async loadInitialData() {
        try {
            // Load recent activity
            await this.updateRecentActivity();
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async updateRecentActivity() {
        const activityContainer = document.getElementById('activity-items');
        if (!activityContainer) return;

        // Mock activity data - replace with actual API call
        const activities = [
            {
                type: 'file_upload',
                message: 'New file uploaded: document.pdf',
                time: '5 minutes ago',
                icon: 'fas fa-upload',
                color: 'success'
            },
            {
                type: 'folder_created',
                message: 'Folder created: /projects/new-project',
                time: '15 minutes ago',
                icon: 'fas fa-folder-plus',
                color: 'info'
            },
            {
                type: 'file_deleted',
                message: 'File deleted: old-backup.zip',
                time: '1 hour ago',
                icon: 'fas fa-trash',
                color: 'warning'
            },
            {
                type: 'system_start',
                message: 'System started successfully',
                time: '2 hours ago',
                icon: 'fas fa-power-off',
                color: 'primary'
            }
        ];

        activityContainer.innerHTML = activities.map(activity => `
            <div class="timeline-item">
                <div class="timeline-marker bg-${activity.color}"></div>
                <div class="timeline-content">
                    <div class="d-flex align-items-center">
                        <i class="${activity.icon} text-${activity.color} me-2"></i>
                        <div class="flex-grow-1">
                            <p class="mb-1">${activity.message}</p>
                            <small class="text-muted">${activity.time}</small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    startPeriodicUpdates() {
        // Check API health every 30 seconds
        this.healthCheckInterval = setInterval(() => {
            this.checkAPIHealth();
        }, 30000);

        // Update activity every 60 seconds
        this.activityUpdateInterval = setInterval(() => {
            this.updateRecentActivity();
        }, 60000);
    }

    stopPeriodicUpdates() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }
        if (this.activityUpdateInterval) {
            clearInterval(this.activityUpdateInterval);
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatUptime(seconds) {
        if (!seconds) return '0s';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    // Method to manually refresh dashboard
    async refresh() {
        await this.checkAPIHealth();
        await this.updateRecentActivity();
    }

    // Method to manually refresh health (for button click)
    async refreshHealth() {
        await this.checkAPIHealth();
    }

    // Cleanup method
    destroy() {
        this.stopPeriodicUpdates();
        // Remove event listeners if needed
    }
}

/**
 * FileBrowser Class - Integrated into Dashboard
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
        this.currentSearchMode = 'normal'; // 'normal' or 'smart'
        this.searchTimeout = null;
        this.facetCounts = {};
        this.isSearching = false;
        this.lastResults = null;
        
        // Clean up any invalid cached data
        this.cleanupLocalStorage();
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupViewModeToggle();
        this.setupSearchMode();
        this.setupSortingOptions();
        
        this.showBrowseByCategories(); // Show folder view initially instead of empty state
        this.loadInitialFilters();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                // If user starts typing and we're in browse mode, switch to search mode
                if (e.target.value && document.getElementById('categoryFolders')) {
                    this.showSidebarAndSearch();
                }
                this.debounceSearch();
            });
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.performSearch();
                }
            });
        }

        // Search mode dropdown
        document.querySelectorAll('[data-search-mode]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const mode = item.dataset.searchMode;
                this.setSearchMode(mode);
                
                // Close the dropdown after selection
                const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('searchModeDropdown'));
                if (dropdown) {
                    dropdown.hide();
                }
            });
        });

        // Search clear button
        const searchClear = document.getElementById('searchClear');
        if (searchClear) {
            searchClear.addEventListener('click', this.clearSearch.bind(this));
        }

        // Browse all button
        const browseAll = document.getElementById('browseAll');
        if (browseAll) {
            browseAll.addEventListener('click', this.browseAllDocuments.bind(this));
        }

        // Filter management
        const clearFilters = document.getElementById('clearFilters');
        if (clearFilters) {
            clearFilters.addEventListener('click', this.clearFilters.bind(this));
        }

        const clearAllFilters = document.getElementById('clearAllFilters');
        if (clearAllFilters) {
            clearAllFilters.addEventListener('click', this.clearAllFilters.bind(this));
        }

        // View mode toggles
        const listView = document.getElementById('listView');
        const gridView = document.getElementById('gridView');
        if (listView) {
            listView.addEventListener('change', () => {
                if (listView.checked) this.setViewMode('list');
            });
        }
        if (gridView) {
            gridView.addEventListener('change', () => {
                if (gridView.checked) this.setViewMode('grid');
            });
        }

        // Sort options
        document.querySelectorAll('#sortOptions .dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.setSortOrder(item.dataset.sort);
            });
        });

        // Show/hide clear button based on search input
        if (searchInput && searchClear) {
            searchInput.addEventListener('input', (e) => {
                searchClear.style.display = e.target.value ? 'block' : 'none';
            });
        }

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
            // Escape to clear search
            if (e.key === 'Escape') {
                if (document.activeElement === searchInput) {
                    this.clearSearch();
                }
            }
        });
    }

    setupViewModeToggle() {
        // Load saved preference
        const savedViewMode = localStorage.getItem('fileBrowser_viewMode') || 'list';
        this.setViewMode(savedViewMode);
    }

    setupSearchMode() {
        // Load saved preference
        const savedSearchMode = localStorage.getItem('fileBrowser_searchMode') || 'normal';
        this.setSearchMode(savedSearchMode);
    }

    setSearchMode(mode) {
        this.currentSearchMode = mode;
        
        // Update dropdown button text and icon
        const searchModeDropdown = document.getElementById('searchModeDropdown');
        
        if (searchModeDropdown) {
            if (mode === 'smart') {
                searchModeDropdown.className = 'btn btn-success dropdown-toggle';
                searchModeDropdown.innerHTML = '<i class="fas fa-brain me-1"></i><span id="searchModeText" class="d-none d-sm-inline">Smart Search</span>';
            } else {
                searchModeDropdown.className = 'btn btn-primary dropdown-toggle';
                searchModeDropdown.innerHTML = '<i class="fas fa-search me-1"></i><span id="searchModeText" class="d-none d-sm-inline">Search</span>';
            }
        }
        
        // Save preference
        localStorage.setItem('fileBrowser_searchMode', mode);
        
        // Show notification about search mode change
        this.showSearchModeNotification(mode);
        
        // Re-perform current search with new mode if there's an active search
        if (this.currentQuery && this.currentQuery !== '*') {
            this.performSearch();
        }
    }

    setViewMode(mode) {
        this.currentViewMode = mode;
        
        const listView = document.getElementById('listView');
        const gridView = document.getElementById('gridView');
        
        if (listView && gridView) {
            listView.checked = (mode === 'list');
            gridView.checked = (mode === 'grid');
        }
        
        // Save preference
        localStorage.setItem('fileBrowser_viewMode', mode);
        
        // Re-render current results
        this.renderDocuments();
    }

    showSearchModeNotification(mode) {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        const modeInfo = mode === 'smart' 
            ? '<i class="fas fa-brain me-2"></i><strong>Smart Search</strong> - AI-powered semantic search enabled'
            : '<i class="fas fa-search me-2"></i><strong>Normal Search</strong> - Fast text-based search enabled';
            
        notification.innerHTML = `
            ${modeInfo}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }

    setupSortingOptions() {
        // Valid sort options based on Typesense schema
        const validSortOptions = [
            'created_at:desc', 'created_at:asc',
            'updated_at:desc', 'updated_at:asc', 
            'word_count:desc', 'word_count:asc',
            'page_count:desc', 'page_count:asc'
        ];
        
        // Load saved sorting preference
        const savedSort = localStorage.getItem('fileBrowser_sortOrder') || 'created_at:desc';
        
        // Validate the saved sort option
        if (validSortOptions.includes(savedSort)) {
            this.setSortOrder(savedSort);
        } else {
            // Invalid sort option - clear it and use default
            localStorage.removeItem('fileBrowser_sortOrder');
            this.setSortOrder('created_at:desc');
        }
    }

    setSortOrder(sortOrder) {
        // Valid sort options based on Typesense schema
        const validSortOptions = [
            'created_at:desc', 'created_at:asc',
            'updated_at:desc', 'updated_at:asc', 
            'word_count:desc', 'word_count:asc',
            'page_count:desc', 'page_count:asc'
        ];
        
        // Validate the sort order
        if (!validSortOptions.includes(sortOrder)) {
            console.warn(`Invalid sort order: ${sortOrder}. Using default: created_at:desc`);
            sortOrder = 'created_at:desc';
        }
        
        this.currentSort = sortOrder;
        
        // Update dropdown display
        const sortButton = document.querySelector('#sortOptions').parentElement.querySelector('[data-bs-toggle="dropdown"]');
        const selectedOption = document.querySelector(`[data-sort="${sortOrder}"]`);
        
        if (selectedOption && sortButton) {
            sortButton.innerHTML = `<i class="fas fa-sort me-1"></i><span class="d-none d-lg-inline">${selectedOption.textContent}</span>`;
        }
        
        // Save preference
        localStorage.setItem('fileBrowser_sortOrder', sortOrder);
        
        // Perform search with new sort order
        if (this.currentQuery || Object.keys(this.currentFilters).length > 0) {
            this.performSearch();
        }
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
        const query = searchInput ? searchInput.value.trim() : '';
        
        // Set current query - use '*' for empty queries to browse all documents
        this.currentQuery = query || '*';
        this.currentPage = 1;
        
        // If no query and no filters, show empty state instead of searching
        if (!query && Object.keys(this.currentFilters).length === 0) {
            this.showEmptyState();
            return;
        }
        
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
        // Use the current search mode setting
        const useVectorSearch = this.currentSearchMode === 'smart';
        
        const params = new URLSearchParams({
            q: this.currentQuery,
            query_by: 'title,description,summary,original_filename',  // Only searchable text fields
            facet_by: 'type,category,language,authors,tags',          // Only facetable fields
            sort_by: this.currentSort,
            page: this.currentPage,
            per_page: this.perPage,
            include_facet_counts: true,
            highlight_full_fields: 'title,description,summary',       // Only highlightable text fields
            use_vector_search: useVectorSearch
        });
        
        // Add active filters
        if (Object.keys(this.currentFilters).length > 0) {
            const filterConditions = [];
            for (const [field, values] of Object.entries(this.currentFilters)) {
                if (values.length > 0) {
                    if (field === 'created_at' || field === 'updated_at') {
                        // Handle year filtering by converting to timestamp ranges
                        const yearConditions = values.map(year => this.getYearFilterCondition(field, year));
                        filterConditions.push(`(${yearConditions.join(' || ')})`);
                    } else {
                        // Use exact match for faceted fields
                        const valueList = values.map(v => `"${v}"`).join(',');
                        filterConditions.push(`${field}:[${valueList}]`);
                    }
                }
            }
            if (filterConditions.length > 0) {
                params.append('filter_by', filterConditions.join(' && '));
            }
        }
        
        const response = await fetch(`${this.apiEndpoint}/api/v1/documents/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    getYearFilterCondition(field, year) {
        // Convert year to timestamp range (start and end of year)
        const startOfYear = new Date(year, 0, 1).getTime() / 1000; // Unix timestamp
        const endOfYear = new Date(year, 11, 31, 23, 59, 59).getTime() / 1000; // Unix timestamp
        return `${field}:>=${startOfYear} && ${field}:<=${endOfYear}`;
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
                    // Process years from dates if this is a date field
                    if (facet.field_name === 'created_at' || facet.field_name === 'updated_at') {
                        processed[facet.field_name] = this.processDateFacetsToYears(facet.counts);
                    } else if (facet.field_name === 'authors') {
                        // Limit to top 10 authors for cleaner display
                        processed[facet.field_name] = this.limitTopAuthors(facet.counts, 10);
                    } else {
                        processed[facet.field_name] = facet.counts.map(count => ({
                            value: count.value,
                            count: count.count
                        }));
                    }
                }
            });
        }
        
        return processed;
    }

    processDateFacetsToYears(dateCounts) {
        const yearCounts = {};
        
        // Group timestamps by year
        dateCounts.forEach(dateCount => {
            if (dateCount.value) {
                const year = new Date(dateCount.value * 1000).getFullYear();
                if (!yearCounts[year]) {
                    yearCounts[year] = 0;
                }
                yearCounts[year] += dateCount.count;
            }
        });
        
        // Convert to array format and sort by year descending
        return Object.entries(yearCounts)
            .map(([year, count]) => ({ value: year, count }))
            .sort((a, b) => parseInt(b.value) - parseInt(a.value));
    }

    limitTopAuthors(authorCounts, limit = 10) {
        return authorCounts
            .sort((a, b) => b.count - a.count) // Sort by count descending
            .slice(0, limit) // Take top N
            .map(count => ({
                value: count.value,
                count: count.count
            }));
    }

    updateSearchStats(results) {
        const searchStats = document.getElementById('searchStats');
        const searchStatsText = document.getElementById('searchStatsText');
        const searchTime = document.getElementById('searchTime');
        
        if (results.found !== undefined && searchStats && searchStatsText && searchTime) {
            const foundText = results.found === 1 ? '1 document found' : `${results.found.toLocaleString()} documents found`;
            const modeText = this.currentSearchMode === 'smart' ? ' (Smart Search)' : ' (Normal Search)';
            
            searchStatsText.textContent = foundText + modeText;
            searchTime.textContent = results.search_time_ms || 0;
            searchStats.classList.remove('d-none');
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
            container.innerHTML = '<p class="text-muted small mb-0">No options available</p>';
            return;
        }
        
        counts.forEach(item => {
            const isActive = this.currentFilters[fieldName]?.includes(item.value) || false;
            
            const filterOption = document.createElement('div');
            filterOption.className = `d-flex justify-content-between align-items-center p-2 rounded mb-1 cursor-pointer ${isActive ? 'bg-primary text-white' : 'hover-bg-light'}`;
            filterOption.style.cursor = 'pointer';
            filterOption.innerHTML = `
                <span class="small">${this.formatFilterValue(fieldName, item.value)}</span>
                <span class="badge ${isActive ? 'bg-light text-primary' : 'bg-secondary'}">${item.count}</span>
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
        
        if (!activeFilters || !activeFiltersList) return;
        
        const hasActiveFilters = Object.keys(this.currentFilters).length > 0;
        
        if (hasActiveFilters) {
            activeFilters.classList.remove('d-none');
        } else {
            activeFilters.classList.add('d-none');
            return;
        }
        
        activeFiltersList.innerHTML = '';
        
        for (const [fieldName, values] of Object.entries(this.currentFilters)) {
            values.forEach(value => {
                const pill = document.createElement('span');
                pill.className = 'badge bg-primary me-1 mb-1 d-inline-flex align-items-center';
                pill.style.cursor = 'pointer';
                pill.innerHTML = `
                    <span class="me-1">${this.formatFilterValue(fieldName, value)}</span>
                    <i class="fas fa-times" data-field="${fieldName}" data-value="${value}"></i>
                `;
                
                // Add click handler to the X icon specifically
                const removeIcon = pill.querySelector('.fa-times');
                removeIcon.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.removeFilter(fieldName, value);
                });
                
                activeFiltersList.appendChild(pill);
            });
        }
    }

    removeFilter(fieldName, value) {
        if (this.currentFilters[fieldName]) {
            const index = this.currentFilters[fieldName].indexOf(value);
            if (index > -1) {
                this.currentFilters[fieldName].splice(index, 1);
                if (this.currentFilters[fieldName].length === 0) {
                    delete this.currentFilters[fieldName];
                }
            }
        }
        
        // Update active filters display immediately
        this.updateActiveFiltersDisplay();
        
        // Check if we have any filters or search query remaining
        const hasFilters = Object.keys(this.currentFilters).length > 0;
        const hasSearchQuery = this.currentQuery && this.currentQuery !== '*' && this.currentQuery !== '';
        
        // If no filters and no search query, return to folder view
        if (!hasFilters && !hasSearchQuery) {
            console.log('No filters or search query remaining, returning to folder view');
            this.showBrowseByCategories();
        } else {
            // If there are still filters or search query, perform search
            if (!this.currentQuery || this.currentQuery === '') {
                this.currentQuery = '*'; // Browse all with remaining filters
            }
            this.performSearch();
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
        const colClass = this.currentViewMode === 'grid' ? 'col-md-6 col-lg-4' : 'col-12';
        const cardWrapper = document.createElement('div');
        cardWrapper.className = `${colClass} mb-3`;
        
        const typeIcon = this.getTypeIcon(doc.type);
        const formattedDate = this.formatDate(doc.created_at);
        const highlights = this.processHighlights(doc.highlights);
        
        cardWrapper.innerHTML = `
            <div class="card h-100 document-card" style="cursor: pointer;">
                <div class="card-body">
                    <div class="d-flex ${this.currentViewMode === 'list' ? '' : 'flex-column'}">
                        <div class="flex-shrink-0 ${this.currentViewMode === 'list' ? 'me-3' : 'mb-3 align-self-start'}">
                            <div class="rounded p-2 text-white text-center ${this.getTypeColorClass(doc.type)}" style="width: 3rem; height: 3rem; display: flex; align-items: center; justify-content: center;">
                                <i class="fas ${typeIcon}"></i>
                            </div>
                        </div>
                        <div class="flex-grow-1">
                            <h5 class="card-title">${highlights.title || doc.title}</h5>
                            <p class="card-text text-muted small">${highlights.description || doc.description}</p>
                            <div class="d-flex flex-wrap gap-2 mb-2">
                                <small class="text-muted">
                                    <i class="fas fa-calendar me-1"></i>${formattedDate}
                                </small>
                                <small class="text-muted">
                                    <i class="fas fa-file-word me-1"></i>${doc.word_count.toLocaleString()} words
                                </small>
                                ${doc.page_count ? `<small class="text-muted"><i class="fas fa-file-alt me-1"></i>${doc.page_count} pages</small>` : ''}
                                ${doc.score > 0 ? `<small class="badge bg-success">${Math.round(doc.score * 100)}% match</small>` : ''}
                            </div>
                            ${doc.tags.length > 0 ? `
                                <div class="d-flex flex-wrap gap-1">
                                    ${doc.tags.slice(0, 3).map(tag => `
                                        <span class="badge bg-light text-primary border tag-badge" data-tag="${tag}" style="cursor: pointer;">${tag}</span>
                                    `).join('')}
                                    ${doc.tags.length > 3 ? `<span class="badge bg-light text-muted">+${doc.tags.length - 3} more</span>` : ''}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add click handlers
        const card = cardWrapper.querySelector('.document-card');
        card.addEventListener('click', () => this.openDocumentPreview(doc));
        
        // Add tag click handlers
        cardWrapper.querySelectorAll('.tag-badge[data-tag]').forEach(tagElement => {
            tagElement.addEventListener('click', (e) => {
                e.stopPropagation();
                this.searchByTag(tagElement.dataset.tag);
            });
        });
        
        return cardWrapper;
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

    getTypeColorClass(type) {
        const colorMap = {
            'document': 'bg-primary',
            'academic_paper': 'bg-purple',
            'report': 'bg-danger',
            'manual': 'bg-warning',
            'presentation': 'bg-success',
            'policy': 'bg-secondary'
        };
        return colorMap[type] || 'bg-primary';
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
        
        if (!paginationContainer || !pagination) return;
        
        if (results.total_pages <= 1) {
            paginationContainer.classList.add('d-none');
            return;
        }
        
        paginationContainer.classList.remove('d-none');
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
        
        for (let i = startPage; i <= endPage; i++) {
            const pageItem = document.createElement('li');
            pageItem.className = `page-item ${i === currentPage ? 'active' : ''}`;
            pageItem.innerHTML = `<a class="page-link" href="#">${i}</a>`;
            
            if (i !== currentPage) {
                pageItem.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.goToPage(i);
                });
            }
            
            pagination.appendChild(pageItem);
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

    goToPage(page) {
        this.currentPage = page;
        this.performSearch();
        
        // Scroll to top of results
        const searchStats = document.getElementById('searchStats');
        if (searchStats) {
            searchStats.scrollIntoView({ behavior: 'smooth' });
        }
    }

    openDocumentPreview(doc) {
        const modal = new bootstrap.Modal(document.getElementById('documentModal'));
        const modalTitle = document.getElementById('documentModalTitle');
        const modalBody = document.getElementById('documentModalBody');
        
        if (modalTitle && modalBody) {
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
    }

    searchByTag(tag) {
        this.toggleFilter('tags', tag);
    }

    clearSearch() {
        const searchInput = document.getElementById('searchInput');
        const searchClear = document.getElementById('searchClear');
        
        if (searchInput && searchClear) {
            searchInput.value = '';
            searchClear.style.display = 'none';
        }
        
        this.currentQuery = '';
        
        // If no active filters, return to folder browse view
        if (Object.keys(this.currentFilters).length === 0) {
            this.showBrowseByCategories();
        } else {
            // If there are filters, show results with just the filters applied
            this.currentQuery = '*';
            this.performSearch();
        }
    }

    clearFilters() {
        this.currentFilters = {};
        this.updateActiveFiltersDisplay();
        
        // Check if we have a search query
        const hasSearchQuery = this.currentQuery && this.currentQuery !== '*' && this.currentQuery !== '';
        
        // If no search query, return to folder view
        if (!hasSearchQuery) {
            console.log('No search query, returning to folder view after clearing filters');
            this.showBrowseByCategories();
        } else {
            this.performSearch();
        }
    }

    clearAllFilters() {
        const searchInput = document.getElementById('searchInput');
        const searchClear = document.getElementById('searchClear');
        
        // Clear search input
        if (searchInput) {
            searchInput.value = '';
        }
        if (searchClear) {
            searchClear.style.display = 'none';
        }
        
        // Clear query and filters
        this.currentQuery = '';
        this.currentFilters = {};
        this.updateActiveFiltersDisplay();
        
        // Always return to folder browse view when clearing everything
        console.log('Clearing all filters and search, returning to folder view');
        this.showBrowseByCategories();
    }

    browseAllDocuments() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = ''; // Clear the search input
        }
        this.currentQuery = '*';
        this.currentFilters = {}; // Clear any active filters
        this.updateActiveFiltersDisplay();
        this.performSearch();
    }

    // State management methods
    showEmptyState() {
        this.hideAllStates();
        const emptyState = document.getElementById('emptyState');
        if (emptyState) {
            emptyState.classList.remove('d-none');
        }
    }

    showLoadingState() {
        this.hideAllStates();
        const loadingState = document.getElementById('loadingState');
        if (loadingState) {
            loadingState.classList.remove('d-none');
        }
    }

    showNoResultsState() {
        this.hideAllStates();
        const noResultsState = document.getElementById('noResultsState');
        if (noResultsState) {
            noResultsState.classList.remove('d-none');
        }
    }

    showResults() {
        this.hideAllStates();
        const resultsContainer = document.getElementById('resultsContainer');
        if (resultsContainer) {
            resultsContainer.classList.remove('d-none');
        }
    }

    showErrorState(message) {
        this.hideAllStates();
        console.error('FileBrowser Error:', message);
        this.showEmptyState();
    }

    hideAllStates() {
        const states = ['emptyState', 'loadingState', 'noResultsState', 'resultsContainer', 'searchStats'];
        states.forEach(stateId => {
            const element = document.getElementById(stateId);
            if (element) {
                element.classList.add('d-none');
            }
        });
    }

    cleanupLocalStorage() {
        // Clean up invalid sort order from localStorage
        const validSortOptions = [
            'created_at:desc', 'created_at:asc',
            'updated_at:desc', 'updated_at:asc', 
            'word_count:desc', 'word_count:asc',
            'page_count:desc', 'page_count:asc'
        ];
        
        const savedSort = localStorage.getItem('fileBrowser_sortOrder');
        if (savedSort && !validSortOptions.includes(savedSort)) {
            console.log(`Removing invalid sort order from cache: ${savedSort}`);
            localStorage.removeItem('fileBrowser_sortOrder');
        }
    }

    showBrowseByCategories() {
        console.log('Showing browse by categories view');
        
        // Hide sidebar initially
        const sidebar = document.querySelector('.col-md-3');
        if (sidebar) {
            sidebar.style.display = 'none';
        }
        
        // Expand main content to full width
        const mainContent = document.querySelector('.col-md-9');
        if (mainContent) {
            mainContent.className = 'col-12';
        }
        
        // Hide search stats when returning to folder view
        const searchStats = document.getElementById('searchStats');
        if (searchStats) {
            searchStats.classList.add('d-none');
        }
        
        // Clear the current state
        this.currentQuery = '';
        this.currentFilters = {};
        this.updateActiveFiltersDisplay();
        
        // Hide all states and show the browse categories view
        this.hideAllStates();
        this.showCategoriesView();
        
        // Reload the folder data to ensure fresh display
        this.loadInitialFilters();
    }

    showCategoriesView() {
        // Show the main container for categories
        const resultsContainer = document.getElementById('resultsContainer');
        if (resultsContainer) {
            resultsContainer.classList.remove('d-none');
            
            // Replace document results with category browsing
            const documentResults = document.getElementById('documentResults');
            if (documentResults) {
                documentResults.innerHTML = this.renderCategoryBrowsing();
            }
        }
        
        // Hide search stats and pagination for browse mode
        const searchStats = document.getElementById('searchStats');
        const pagination = document.getElementById('paginationContainer');
        if (searchStats) searchStats.classList.add('d-none');
        if (pagination) pagination.classList.add('d-none');
    }

    renderCategoryBrowsing() {
        return `
            <div class="row">
                <div class="col-12 mb-4">
                    <div class="text-center">
                        <h3 class="text-muted mb-3">
                            <i class="fas fa-folder-open text-primary me-2"></i>
                            Browse Your Knowledge Base
                        </h3>
                        <p class="text-muted mb-4">Choose a category to explore your documents</p>
                        <div class="d-flex justify-content-center gap-3 mb-4">
                            <button class="btn btn-outline-primary" id="browseAllFromFolder">
                                <i class="fas fa-list me-2"></i>View All Documents
                            </button>
                            <button class="btn btn-outline-secondary" id="searchFromFolder">
                                <i class="fas fa-search me-2"></i>Start Searching
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="categoryFolders">
                <div class="d-flex justify-content-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading categories...</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderCategoryFolders(facetCounts) {
        const categoryFolders = document.getElementById('categoryFolders');
        if (!categoryFolders) return;
        
        const sections = [
            { 
                key: 'type', 
                title: 'Document Types', 
                icon: 'fas fa-folder',
                description: 'Browse by document format'
            },
            { 
                key: 'category', 
                title: 'Categories', 
                icon: 'fas fa-folder',
                description: 'Browse by subject area'
            },
            { 
                key: 'authors', 
                title: 'Authors', 
                icon: 'fas fa-folder',
                description: 'Browse by document authors'
            },
            { 
                key: 'created_at', 
                title: 'Years', 
                icon: 'fas fa-folder',
                description: 'Browse by publication year'
            },
            { 
                key: 'tags', 
                title: 'Tags', 
                icon: 'fas fa-folder',
                description: 'Browse by document tags'
            }
        ];
        
        let html = '';
        
        sections.forEach(section => {
            if (facetCounts[section.key] && facetCounts[section.key].length > 0) {
                html += this.renderFolderSection(section, facetCounts[section.key]);
            }
        });
        
        categoryFolders.innerHTML = html;
        
        // Add click handlers for folder items
        this.setupFolderClickHandlers();
    }

    renderFolderSection(section, items) {
        // Limit items to prevent overcrowding
        const maxItems = section.key === 'tags' ? 15 : (section.key === 'authors' ? 10 : items.length);
        const displayItems = items.slice(0, maxItems);
        const hasMore = items.length > maxItems;
        
        // Get section-specific icon
        const sectionIcon = this.getSectionIcon(section.key);
        
        return `
            <div class="row mb-5">
                <div class="col-12">
                    <div class="d-flex align-items-center mb-3">
                        <i class="${sectionIcon} text-primary me-3" style="font-size: 2rem;"></i>
                        <div>
                            <h4 class="mb-1">${section.title}</h4>
                            <p class="text-muted mb-0 small">${section.description}</p>
                        </div>
                    </div>
                    <hr class="mb-4">
                    <div class="row g-3">
                        ${displayItems.map(item => this.renderFolderCard(section.key, item)).join('')}
                        ${hasMore ? `
                            <div class="col-md-2 col-sm-3 col-4">
                                <div class="card folder-card text-center h-100" data-action="show-all" data-field="${section.key}">
                                    <div class="card-body d-flex flex-column justify-content-center p-3 position-relative">
                                        <div class="d-flex justify-content-center align-items-center mb-auto">
                                            <i class="fas fa-ellipsis-h text-muted" style="font-size: 2rem;"></i>
                                        </div>
                                        <small class="text-muted mt-2">+${items.length - maxItems} more</small>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    getSectionIcon(sectionKey) {
        const iconMap = {
            'type': 'fa-file-alt',
            'category': 'fa-tags',
            'authors': 'fa-users',
            'created_at': 'fa-calendar-alt',
            'tags': 'fa-tag'
        };
        return iconMap[sectionKey] || 'fa-folder';
    }

    renderFolderCard(fieldName, item) {
        const displayValue = this.formatFolderValue(fieldName, item.value);
        const icon = this.getFolderIcon(fieldName, item.value);
        
        return `
            <div class="col-md-2 col-sm-3 col-4">
                <div class="card folder-card h-100" data-filter-field="${fieldName}" data-filter-value="${item.value}">
                    <div class="card-body text-center d-flex flex-column justify-content-between p-3 position-relative">
                        <!-- Badge in top corner -->
                        <span class="badge bg-primary position-absolute top-0 end-0 m-1 rounded-pill" style="transform: translate(10px, -10px);">${item.count}</span>
                        
                        <!-- Large Mac-style folder icon -->
                        <div class="d-flex justify-content-center align-items-center mb-auto">
                            <i class="fas ${icon} text-primary" style="font-size: 3.5rem;"></i>
                        </div>
                        
                        <!-- Title at bottom -->
                        <h6 class="card-title mb-0 small text-truncate mt-2" title="${displayValue}">${displayValue}</h6>
                    </div>
                </div>
            </div>
        `;
    }

    formatFolderValue(fieldName, value) {
        if (fieldName === 'type') {
            return value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        if (fieldName === 'created_at') {
            return value; // Already processed as year
        }
        if (fieldName === 'authors' && value.length > 20) {
            return value.substring(0, 17) + '...';
        }
        return value;
    }

    getFolderIcon(fieldName, value) {
        // Use consistent folder icons for all categories
        if (fieldName === 'type') return 'fa-folder';
        if (fieldName === 'category') return 'fa-folder';
        if (fieldName === 'authors') return 'fa-folder';
        if (fieldName === 'created_at') return 'fa-folder';
        if (fieldName === 'tags') return 'fa-folder';
        return 'fa-folder';
    }

    setupFolderClickHandlers() {
        // Handle folder card clicks
        document.querySelectorAll('.folder-card[data-filter-field]').forEach(card => {
            card.addEventListener('click', () => {
                const field = card.dataset.filterField;
                const value = card.dataset.filterValue;
                this.activateFolderFilter(field, value);
            });
        });
        
        // Handle "show all" clicks
        document.querySelectorAll('.folder-card[data-action="show-all"]').forEach(card => {
            card.addEventListener('click', () => {
                const field = card.dataset.field;
                this.showAllInField(field);
            });
        });
        
        // Handle browse all button
        const browseAllBtn = document.getElementById('browseAllFromFolder');
        if (browseAllBtn) {
            browseAllBtn.addEventListener('click', () => {
                this.showSidebarAndSearch();
                this.browseAllDocuments();
            });
        }
        
        // Handle search button
        const searchBtn = document.getElementById('searchFromFolder');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                this.showSidebarAndSearch();
                const searchInput = document.getElementById('searchInput');
                if (searchInput) {
                    searchInput.focus();
                }
            });
        }
    }

    activateFolderFilter(field, value) {
        // Show sidebar and switch to search mode
        this.showSidebarAndSearch();
        
        // Set the filter
        this.currentFilters[field] = [value];
        this.currentQuery = '*'; // Browse all with filter
        
        // Perform search
        this.performSearch();
    }

    showAllInField(field) {
        // Show sidebar and expand the specific field
        this.showSidebarAndSearch();
        
        // Expand the specific filter section
        const targetFilter = document.getElementById(`${field}Filter`);
        if (targetFilter && !targetFilter.classList.contains('show')) {
            targetFilter.classList.add('show');
        }
        
        // Scroll to the field
        setTimeout(() => {
            const filterSection = document.querySelector(`[data-bs-target="#${field}Filter"]`);
            if (filterSection) {
                filterSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    }

    showSidebarAndSearch() {
        // Show sidebar
        const sidebar = document.querySelector('.col-md-3');
        if (sidebar) {
            sidebar.style.display = 'block';
        }
        
        // Restore main content width
        const mainContent = document.querySelector('.col-12');
        if (mainContent) {
            mainContent.className = 'col-md-9';
        }
        
        // Focus search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }

    async loadInitialFilters() {
        try {
            // Load facet counts to populate filters and folder view
            const results = await this.searchDocuments();
            if (results.success && results.facet_counts) {
                this.facetCounts = this.processFacetCounts(results.facet_counts);
                
                // If we're in browse mode, render the folder view
                if (document.getElementById('categoryFolders')) {
                    this.renderCategoryFolders(this.facetCounts);
                } else {
                    // Otherwise update the sidebar filters
                    this.updateFacetFilters(this.facetCounts);
                }
            }
        } catch (error) {
            console.warn('Could not load initial filter options:', error);
            // Show error in folder view if we're in browse mode
            const categoryFolders = document.getElementById('categoryFolders');
            if (categoryFolders) {
                categoryFolders.innerHTML = `
                    <div class="text-center">
                        <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 3rem;"></i>
                        <h4 class="text-muted">Unable to load categories</h4>
                        <p class="text-muted">Please try refreshing the page</p>
                        <button class="btn btn-primary" onclick="location.reload()">
                            <i class="fas fa-refresh me-2"></i>Refresh
                        </button>
                    </div>
                `;
            }
        }
    }
}

// Create health endpoint mock for development
async function createHealthEndpoint() {
    // Check if health endpoint exists
    try {
        const response = await fetch('/health');
        if (!response.ok) {
            console.warn('Health endpoint not available, using mock data');
        }
    } catch (error) {
        console.warn('Health endpoint not available, using mock data');
        
        // If health endpoint doesn't exist, we'll provide mock responses
        const originalFetch = window.fetch;
        window.fetch = function(url, options) {
            if (url.includes('/health')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        status: 'healthy',
                        file_count: Math.floor(Math.random() * 1000) + 100,
                        storage_used: Math.floor(Math.random() * 1000000000) + 100000000,
                        uptime: Math.floor(Math.random() * 86400) + 3600,
                        storage_status: 'online',
                        database_status: 'online'
                    })
                });
            }
            return originalFetch.apply(this, arguments);
        };
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', async function() {
    // Create health endpoint mock if needed
    await createHealthEndpoint();
    
    // Initialize dashboard
    window.dashboard = new Dashboard();
    
    // Add global refresh button functionality
    const refreshButton = document.querySelector('[data-card-widget="refresh"]');
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            window.dashboard.refresh();
        });
    }
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
}); 