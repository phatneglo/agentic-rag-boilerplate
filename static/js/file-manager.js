/**
 * File Manager - Main JavaScript Module
 * 
 * Handles core file manager functionality including navigation,
 * file operations, and UI interactions.
 */

class FileManager {
    constructor() {
        this.currentPath = '';
        this.selectedItems = new Set();
        this.viewMode = 'grid'; // 'grid' or 'list'
        this.sortBy = 'name'; // 'name', 'date', 'size'
        this.sortOrder = 'asc'; // 'asc' or 'desc'
        this.searchQuery = '';
        this.isLoading = false;
        
        // Pagination and performance
        this.itemsPerPage = 50;
        this.currentPage = 1;
        this.totalItems = 0;
        this.allItems = [];
        this.displayedItems = [];
        
        // API base URL
        this.apiBase = '/api/v1/file-manager';
        
        // Initialize the file manager
        this.init();
    }
    
    /**
     * Initialize the file manager
     */
    init() {
        this.bindEvents();
        this.loadDirectory();
        this.setupDragAndDrop();
        this.setupContextMenu();
        this.setupKeyboardShortcuts();
    }
    
    /**
     * Bind event listeners
     */
    bindEvents() {
        // Navigation events
        document.addEventListener('click', this.handleNavigation.bind(this));
        
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        const clearSearch = document.getElementById('clearSearch');
        
        searchInput.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        clearSearch.addEventListener('click', this.clearSearch.bind(this));
        
        // Toolbar buttons
        document.getElementById('uploadBtn').addEventListener('click', () => this.showUploadModal());
        document.getElementById('emptyUploadBtn').addEventListener('click', () => this.showUploadModal());
        document.getElementById('newFolderBtn').addEventListener('click', () => this.showNewFolderModal());
        document.getElementById('refreshBtn').addEventListener('click', () => this.loadDirectory());
        
        // View mode toggles
        document.getElementById('viewModeGrid').addEventListener('click', () => this.setViewMode('grid'));
        document.getElementById('viewModeList').addEventListener('click', () => this.setViewMode('list'));
        
        // Sort buttons
        document.getElementById('sortName').addEventListener('click', () => this.setSortBy('name'));
        document.getElementById('sortDate').addEventListener('click', () => this.setSortBy('date'));
        document.getElementById('sortSize').addEventListener('click', () => this.setSortBy('size'));
        
        // Selection
        document.getElementById('selectAllBtn').addEventListener('click', this.toggleSelectAll.bind(this));
        document.getElementById('deleteSelectedBtn').addEventListener('click', this.deleteSelected.bind(this));
        document.getElementById('moveSelectedBtn').addEventListener('click', this.moveSelected.bind(this));
        
        // Modal forms
        document.getElementById('newFolderForm').addEventListener('submit', this.createFolder.bind(this));
        document.getElementById('renameForm').addEventListener('submit', this.renameItem.bind(this));
        document.getElementById('moveForm').addEventListener('submit', this.moveItem.bind(this));
        
        // Delete confirmation modal
        document.getElementById('confirmDeleteBtn').addEventListener('click', this.executeDelete.bind(this));
        document.getElementById('confirmFolderName').addEventListener('input', this.validateFolderName.bind(this));
        
        // Upload functionality
        document.getElementById('browseBtn').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
        document.getElementById('fileInput').addEventListener('change', this.handleFileSelect.bind(this));
        
        // Sidebar navigation
        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const path = link.dataset.path;
                this.navigateToPath(path);
                
                // Update active state
                document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
        
        // Move modal functionality
        document.getElementById('moveUpBtn').addEventListener('click', this.moveUpDirectory.bind(this));
        document.getElementById('copyInsteadOfMove').addEventListener('change', this.toggleMoveMode.bind(this));
    }
    
    /**
     * Handle navigation clicks (breadcrumbs, folders)
     */
    handleNavigation(e) {
        // Breadcrumb navigation
        if (e.target.closest('.breadcrumb-item a')) {
            e.preventDefault();
            const path = e.target.closest('.breadcrumb-item a').dataset.path || '';
            this.navigateToPath(path);
            return;
        }
        
        // File item clicks
        if (e.target.closest('.file-item')) {
            const fileItem = e.target.closest('.file-item');
            const path = fileItem.dataset.path;
            const isDirectory = fileItem.dataset.type === 'folder';
            
            // Handle checkbox clicks
            if (e.target.type === 'checkbox') {
                this.toggleItemSelection(path, e.target.checked);
                return;
            }
            
            // Handle double-click for folders
            if (isDirectory && e.detail === 2) {
                this.navigateToPath(path);
                return;
            }
            
            // Handle single click selection
            if (!e.ctrlKey && !e.metaKey) {
                this.clearSelection();
            }
            this.toggleItemSelection(path, true);
        }
    }
    
    /**
     * Navigate to a specific path
     */
    async navigateToPath(path) {
        this.currentPath = path;
        this.clearSelection();
        await this.loadDirectory();
    }
    
    /**
     * Load directory contents
     */
    async loadDirectory() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const params = new URLSearchParams({
                path: this.currentPath,
                search: this.searchQuery
            });
            
            const response = await fetch(`${this.apiBase}/?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.allItems = data.data.items;
                this.totalItems = data.data.total_items;
                this.currentPage = 1;
                
                this.renderDirectory(data.data);
                this.updateBreadcrumbs(data.data.breadcrumbs);
                this.updateItemCount(this.totalItems);
                this.setupInfiniteScroll();
            } else {
                this.showError('Failed to load directory');
            }
        } catch (error) {
            console.error('Error loading directory:', error);
            this.showError('Failed to load directory');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    /**
     * Setup infinite scroll for large directories
     */
    setupInfiniteScroll() {
        const fileGrid = document.getElementById('fileGrid');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && this.hasMoreItems()) {
                    this.loadMoreItems();
                }
            });
        }, {
            rootMargin: '100px'
        });
        
        // Create a sentinel element at the bottom
        const sentinel = document.createElement('div');
        sentinel.id = 'scroll-sentinel';
        sentinel.style.height = '1px';
        fileGrid.appendChild(sentinel);
        
        observer.observe(sentinel);
    }
    
    /**
     * Check if there are more items to load
     */
    hasMoreItems() {
        return this.displayedItems.length < this.allItems.length;
    }
    
    /**
     * Load more items (pagination)
     */
    loadMoreItems() {
        if (this.isLoading || !this.hasMoreItems()) return;
        
        const startIndex = this.displayedItems.length;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.allItems.length);
        const newItems = this.allItems.slice(startIndex, endIndex);
        
        this.displayedItems.push(...newItems);
        this.renderNewItems(newItems);
    }
    
    /**
     * Render new items (for infinite scroll)
     */
    renderNewItems(items) {
        const fileGrid = document.getElementById('fileGrid');
        const sentinel = document.getElementById('scroll-sentinel');
        
        // Sort new items
        const sortedItems = this.sortItems(items);
        
        // Create document fragment for better performance
        const fragment = document.createDocumentFragment();
        
        sortedItems.forEach(item => {
            const itemElement = document.createElement('div');
            itemElement.innerHTML = this.renderFileItem(item);
            fragment.appendChild(itemElement.firstElementChild);
        });
        
        // Insert before sentinel
        fileGrid.insertBefore(fragment, sentinel);
    }
    
    /**
     * Render directory contents
     */
    renderDirectory(data) {
        const fileGrid = document.getElementById('fileGrid');
        const emptyState = document.getElementById('emptyState');
        
        // Clear previous content
        fileGrid.innerHTML = '';
        
        if (this.allItems.length === 0) {
            emptyState.classList.remove('d-none');
            return;
        }
        
        emptyState.classList.add('d-none');
        
        // Sort all items
        this.allItems = this.sortItems(this.allItems);
        
        // Load initial batch
        const initialItems = this.allItems.slice(0, this.itemsPerPage);
        this.displayedItems = [...initialItems];
        
        // Render initial items
        fileGrid.innerHTML = this.displayedItems.map(item => this.renderFileItem(item)).join('');
        
        // Apply view mode
        fileGrid.className = `file-grid ${this.viewMode === 'list' ? 'list-view' : ''}`;
        
        // Show load more button if there are more items
        if (this.hasMoreItems()) {
            this.addLoadMoreButton();
        }
    }
    
    /**
     * Add load more button
     */
    addLoadMoreButton() {
        const fileGrid = document.getElementById('fileGrid');
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.className = 'load-more-container text-center mt-3';
        loadMoreBtn.innerHTML = `
            <button class="btn btn-outline-primary" id="loadMoreBtn">
                <i class="fas fa-chevron-down me-2"></i>Load More Files
            </button>
        `;
        
        fileGrid.appendChild(loadMoreBtn);
        
        // Add click handler
        document.getElementById('loadMoreBtn').addEventListener('click', () => {
            this.loadMoreItems();
            if (!this.hasMoreItems()) {
                loadMoreBtn.remove();
            }
        });
    }
    
    /**
     * Render a single file item
     */
    renderFileItem(item) {
        const isSelected = this.selectedItems.has(item.path);
        const selectedClass = isSelected ? 'selected' : '';
        const folderClass = item.is_directory ? 'folder' : '';
        
        if (this.viewMode === 'list') {
            return `
                <div class="file-item ${selectedClass} ${folderClass}" 
                     data-path="${item.path}" 
                     data-type="${item.type}"
                     data-name="${item.name}">
                    <input type="checkbox" class="form-check-input selection-checkbox" 
                           ${isSelected ? 'checked' : ''}>
                    <i class="${item.icon} file-icon"></i>
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(item.name)}</div>
                    </div>
                    <div class="file-meta">
                        <div>${item.size_formatted}</div>
                        <div class="text-muted">${this.formatDate(item.modified)}</div>
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="file-item ${selectedClass} ${folderClass}" 
                     data-path="${item.path}" 
                     data-type="${item.type}"
                     data-name="${item.name}">
                    <input type="checkbox" class="form-check-input selection-checkbox" 
                           ${isSelected ? 'checked' : ''}>
                    <i class="${item.icon} file-icon"></i>
                    <div class="file-name">${this.escapeHtml(item.name)}</div>
                    <div class="file-meta">
                        ${item.size_formatted} • ${this.formatDate(item.modified)}
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * Sort items based on current sort settings
     */
    sortItems(items) {
        return items.sort((a, b) => {
            // Always put directories first
            if (a.is_directory !== b.is_directory) {
                return a.is_directory ? -1 : 1;
            }
            
            let comparison = 0;
            
            switch (this.sortBy) {
                case 'name':
                    comparison = a.name.localeCompare(b.name);
                    break;
                case 'date':
                    comparison = new Date(a.modified) - new Date(b.modified);
                    break;
                case 'size':
                    comparison = a.size - b.size;
                    break;
            }
            
            return this.sortOrder === 'desc' ? -comparison : comparison;
        });
    }
    
    /**
     * Update breadcrumb navigation
     */
    updateBreadcrumbs(breadcrumbs) {
        const breadcrumbNav = document.getElementById('breadcrumbNav');
        
        breadcrumbNav.innerHTML = breadcrumbs.map((crumb, index) => {
            const isLast = index === breadcrumbs.length - 1;
            const icon = index === 0 ? '<i class="fas fa-home me-1"></i>' : '';
            
            if (isLast) {
                return `<li class="breadcrumb-item active">${icon}${this.escapeHtml(crumb.name)}</li>`;
            } else {
                return `
                    <li class="breadcrumb-item">
                        <a href="#" data-path="${crumb.path}">${icon}${this.escapeHtml(crumb.name)}</a>
                    </li>
                `;
            }
        }).join('');
    }
    
    /**
     * Update item count display
     */
    updateItemCount(count) {
        document.getElementById('itemCount').textContent = `${count} item${count !== 1 ? 's' : ''}`;
    }
    
    /**
     * Handle search input
     */
    async handleSearch(e) {
        const query = e.target.value.trim();
        this.searchQuery = query;
        
        // Clear search if query is empty
        if (!query) {
            await this.loadDirectory();
            return;
        }
        
        // Debounced search for better performance
        this.performSearch();
    }
    
    /**
     * Perform search with debouncing
     */
    performSearch = this.debounce(async () => {
        if (this.searchQuery.length < 2) {
            await this.loadDirectory();
            return;
        }
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const params = new URLSearchParams({
                query: this.searchQuery,
                path: this.currentPath
            });
            
            const response = await fetch(`${this.apiBase}/search?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.allItems = data.data.results;
                this.totalItems = data.data.total_results;
                this.currentPage = 1;
                
                this.renderSearchResults(data.data);
                this.updateItemCount(this.totalItems);
            } else {
                this.showError('Search failed');
            }
        } catch (error) {
            console.error('Error searching:', error);
            this.showError('Search failed');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }, 300);
    
    /**
     * Render search results
     */
    renderSearchResults(data) {
        const fileGrid = document.getElementById('fileGrid');
        const emptyState = document.getElementById('emptyState');
        
        // Clear previous content
        fileGrid.innerHTML = '';
        
        if (this.allItems.length === 0) {
            emptyState.classList.remove('d-none');
            emptyState.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-search text-muted mb-3" style="font-size: 3rem;"></i>
                    <h5>No results found</h5>
                    <p class="text-muted">No files or folders match your search for "${this.escapeHtml(this.searchQuery)}"</p>
                </div>
            `;
            return;
        }
        
        emptyState.classList.add('d-none');
        
        // Load initial batch
        const initialItems = this.allItems.slice(0, this.itemsPerPage);
        this.displayedItems = [...initialItems];
        
        // Render initial items with search highlighting
        fileGrid.innerHTML = this.displayedItems.map(item => this.renderSearchItem(item)).join('');
        
        // Apply view mode
        fileGrid.className = `file-grid ${this.viewMode === 'list' ? 'list-view' : ''}`;
        
        // Show load more button if there are more items
        if (this.hasMoreItems()) {
            this.addLoadMoreButton();
        }
    }
    
    /**
     * Render search item with highlighting
     */
    renderSearchItem(item) {
        const isSelected = this.selectedItems.has(item.path);
        const selectedClass = isSelected ? 'selected' : '';
        const folderClass = item.is_directory ? 'folder' : '';
        
        // Highlight search terms
        const highlightedName = this.highlightSearchTerm(item.name, this.searchQuery);
        
        if (this.viewMode === 'list') {
            return `
                <div class="file-item ${selectedClass} ${folderClass}" 
                     data-path="${item.path}" 
                     data-type="${item.type}"
                     data-name="${item.name}">
                    <input type="checkbox" class="form-check-input selection-checkbox" 
                           ${isSelected ? 'checked' : ''}>
                    <i class="${item.icon} file-icon"></i>
                    <div class="file-info">
                        <div class="file-name">${highlightedName}</div>
                        ${item.relative_path ? `<small class="text-muted">in ${this.escapeHtml(item.relative_path)}</small>` : ''}
                    </div>
                    <div class="file-meta">
                        <div>${item.size_formatted}</div>
                        <div class="text-muted">${this.formatDate(item.modified)}</div>
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="file-item ${selectedClass} ${folderClass}" 
                     data-path="${item.path}" 
                     data-type="${item.type}"
                     data-name="${item.name}">
                    <input type="checkbox" class="form-check-input selection-checkbox" 
                           ${isSelected ? 'checked' : ''}>
                    <i class="${item.icon} file-icon"></i>
                    <div class="file-name">${highlightedName}</div>
                    <div class="file-meta">
                        ${item.size_formatted} • ${this.formatDate(item.modified)}
                        ${item.relative_path ? `<br><small class="text-muted">in ${this.escapeHtml(item.relative_path)}</small>` : ''}
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * Highlight search terms in text
     */
    highlightSearchTerm(text, searchTerm) {
        if (!searchTerm) return this.escapeHtml(text);
        
        const escapedText = this.escapeHtml(text);
        const escapedTerm = this.escapeHtml(searchTerm);
        const regex = new RegExp(`(${escapedTerm})`, 'gi');
        
        return escapedText.replace(regex, '<mark>$1</mark>');
    }
    
    /**
     * Clear search
     */
    async clearSearch() {
        document.getElementById('searchInput').value = '';
        this.searchQuery = '';
        
        // Reset pagination
        this.currentPage = 1;
        this.allItems = [];
        this.displayedItems = [];
        
        // Reload directory
        await this.loadDirectory();
    }
    
    /**
     * Set view mode
     */
    setViewMode(mode) {
        this.viewMode = mode;
        const fileGrid = document.getElementById('fileGrid');
        fileGrid.className = `file-grid ${mode === 'list' ? 'list-view' : ''}`;
        
        // Update button states
        document.getElementById('viewModeGrid').classList.toggle('active', mode === 'grid');
        document.getElementById('viewModeList').classList.toggle('active', mode === 'list');
    }
    
    /**
     * Set sort criteria
     */
    setSortBy(criteria) {
        if (this.sortBy === criteria) {
            this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortBy = criteria;
            this.sortOrder = 'asc';
        }
        
        // Update button states
        document.querySelectorAll('[id^="sort"]').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`sort${criteria.charAt(0).toUpperCase() + criteria.slice(1)}`).classList.add('active');
        
        // Re-render current directory
        this.loadDirectory();
    }
    
    /**
     * Toggle item selection
     */
    toggleItemSelection(path, selected) {
        if (selected) {
            this.selectedItems.add(path);
        } else {
            this.selectedItems.delete(path);
        }
        
        // Update UI
        const fileItem = document.querySelector(`[data-path="${path}"]`);
        if (fileItem) {
            fileItem.classList.toggle('selected', selected);
            const checkbox = fileItem.querySelector('.selection-checkbox');
            if (checkbox) checkbox.checked = selected;
        }
        
        this.updateSelectionUI();
    }
    
    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedItems.clear();
        document.querySelectorAll('.file-item.selected').forEach(item => {
            item.classList.remove('selected');
            const checkbox = item.querySelector('.selection-checkbox');
            if (checkbox) checkbox.checked = false;
        });
        this.updateSelectionUI();
    }
    
    /**
     * Toggle select all
     */
    toggleSelectAll() {
        const allItems = document.querySelectorAll('.file-item');
        const allSelected = allItems.length > 0 && this.selectedItems.size === allItems.length;
        
        if (allSelected) {
            this.clearSelection();
        } else {
            allItems.forEach(item => {
                const path = item.dataset.path;
                this.toggleItemSelection(path, true);
            });
        }
    }
    
    /**
     * Update selection-related UI elements
     */
    updateSelectionUI() {
        const selectedCount = this.selectedItems.size;
        const selectedActions = document.querySelector('.selected-actions');
        const selectAllBtn = document.getElementById('selectAllBtn');
        
        if (selectedCount > 0) {
            selectedActions.classList.remove('d-none');
            selectAllBtn.innerHTML = `<i class="fas fa-check-square me-1"></i>Selected (${selectedCount})`;
        } else {
            selectedActions.classList.add('d-none');
            selectAllBtn.innerHTML = '<i class="fas fa-check-square me-1"></i>Select All';
        }
    }
    
    /**
     * Show loading state
     */
    showLoading() {
        document.getElementById('loadingSpinner').classList.remove('d-none');
        document.getElementById('fileGrid').style.opacity = '0.5';
    }
    
    /**
     * Hide loading state
     */
    hideLoading() {
        document.getElementById('loadingSpinner').classList.add('d-none');
        document.getElementById('fileGrid').style.opacity = '1';
    }
    
    /**
     * Show upload modal
     */
    showUploadModal() {
        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        modal.show();
    }
    
    /**
     * Show new folder modal
     */
    showNewFolderModal() {
        const modal = new bootstrap.Modal(document.getElementById('newFolderModal'));
        document.getElementById('folderName').value = '';
        modal.show();
    }
    
    /**
     * Create new folder
     */
    async createFolder(e) {
        e.preventDefault();
        
        const folderName = document.getElementById('folderName').value.trim();
        if (!folderName) return;
        
        try {
            const response = await fetch(`${this.apiBase}/folder`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: this.currentPath,
                    folder_name: folderName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Folder created successfully');
                bootstrap.Modal.getInstance(document.getElementById('newFolderModal')).hide();
                await this.loadDirectory();
            } else {
                this.showError(data.message || 'Failed to create folder');
            }
        } catch (error) {
            console.error('Error creating folder:', error);
            this.showError('Failed to create folder');
        }
    }
    
    /**
     * Delete single item
     */
    async deleteItem(path, name) {
        this.showDeleteModal([{ path, name }], false);
    }
    
    /**
     * Delete selected items
     */
    async deleteSelected() {
        if (this.selectedItems.size === 0) return;
        
        const items = Array.from(this.selectedItems).map(path => {
            const fileItem = document.querySelector(`[data-path="${path}"]`);
            const name = fileItem ? fileItem.dataset.name : path.split('/').pop();
            const isDirectory = fileItem ? fileItem.dataset.type === 'folder' : false;
            return { path, name, isDirectory };
        });
        
        // If only one item selected and it's a folder, use single folder delete modal
        if (items.length === 1 && items[0].isDirectory) {
            this.showDeleteModal(items, false); // false = not bulk, single folder
        } else {
            this.showDeleteModal(items, true); // true = bulk operation
        }
    }
    
    /**
     * Handle file selection for upload
     */
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.uploadFiles(files);
        }
    }
    
    /**
     * Upload files
     */
    async uploadFiles(files) {
        const progressContainer = document.getElementById('uploadProgress');
        const progressBar = progressContainer.querySelector('.progress-bar');
        
        // Reset and show progress
        progressBar.style.width = '0%';
        progressContainer.classList.remove('d-none');
        
        let successCount = 0;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('path', this.currentPath);
            
            try {
                const response = await fetch(`${this.apiBase}/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    successCount++;
                } else {
                    this.showError(`Failed to upload ${file.name}: ${data.message}`);
                }
                
                // Update progress
                const progress = ((i + 1) / files.length) * 100;
                progressBar.style.width = `${progress}%`;
                
            } catch (error) {
                console.error('Error uploading file:', error);
                this.showError(`Failed to upload ${file.name}`);
            }
        }
        
        // Hide progress and close modal
        progressContainer.classList.add('d-none');
        const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
        if (modal) {
            modal.hide();
        }
        
        // Reset file input
        document.getElementById('fileInput').value = '';
        
        // Show success message
        if (successCount > 0) {
            this.showSuccess(`${successCount} file(s) uploaded successfully`);
            await this.loadDirectory();
        }
    }
    
    /**
     * Setup drag and drop functionality
     */
    setupDragAndDrop() {
        const uploadArea = document.getElementById('uploadArea');
        const fileContainer = document.getElementById('fileContainer');
        
        // Upload modal drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            // Only remove dragover if we're leaving the upload area entirely
            if (!uploadArea.contains(e.relatedTarget)) {
                uploadArea.classList.remove('dragover');
            }
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.uploadFiles(files);
            }
        });
        
        // Main area drag and drop
        fileContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileContainer.classList.add('drag-over');
        });
        
        fileContainer.addEventListener('dragleave', (e) => {
            if (!fileContainer.contains(e.relatedTarget)) {
                fileContainer.classList.remove('drag-over');
            }
        });
        
        fileContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            fileContainer.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                // Show upload modal with files
                this.showUploadModal();
                // Auto-upload the dropped files
                setTimeout(() => this.uploadFiles(files), 100);
            }
        });
    }
    
    /**
     * Setup context menu
     */
    setupContextMenu() {
        const contextMenu = document.getElementById('contextMenu');
        let currentTarget = null;
        
        // Show context menu
        document.addEventListener('contextmenu', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (fileItem) {
                e.preventDefault();
                currentTarget = fileItem;
                
                contextMenu.style.left = `${e.pageX}px`;
                contextMenu.style.top = `${e.pageY}px`;
                contextMenu.classList.remove('d-none');
            }
        });
        
        // Hide context menu
        document.addEventListener('click', () => {
            contextMenu.classList.add('d-none');
        });
        
        // Handle context menu actions
        contextMenu.addEventListener('click', (e) => {
            e.preventDefault();
            const action = e.target.closest('.context-item')?.dataset.action;
            if (action && currentTarget) {
                this.handleContextAction(action, currentTarget);
            }
            contextMenu.classList.add('d-none');
        });
    }
    
    /**
     * Handle context menu actions
     */
    async handleContextAction(action, target) {
        const path = target.dataset.path;
        let name = target.dataset.name;
        const isDirectory = target.dataset.type === 'folder';
        const icon = target.querySelector('.file-icon').className;
        
        // Fallback: extract name from path if data-name is missing
        if (!name) {
            name = path.split('/').pop() || path;
        }
        
        switch (action) {
            case 'open':
                if (isDirectory) {
                    this.navigateToPath(path);
                } else {
                    // For files, open in new tab (download)
                    this.downloadItem(path, false);
                }
                break;
                
            case 'download':
                this.downloadItem(path, isDirectory);
                break;
                
            case 'rename':
                this.showRenameModal(path, name);
                break;
                
            case 'move':
                this.showMoveModal(path, name, icon);
                break;
                
            case 'share':
                this.shareItem(path, name);
                break;
                
            case 'delete':
                this.deleteItem(path, name);
                break;
                
            case 'info':
                this.showFileInfo(path);
                break;
        }
    }
    
    /**
     * Download item
     */
    async downloadItem(path, isDirectory) {
        try {
            if (isDirectory) {
                // For folders, download as zip
                const response = await fetch(`${this.apiBase}/download/folder?path=${encodeURIComponent(path)}`, {
                    method: 'GET'
                });
                
                if (response.ok) {
                    // Get the blob and create download link
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    
                    // Extract filename from Content-Disposition header or use default
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'folder.zip';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                        if (filenameMatch && filenameMatch[1]) {
                            filename = filenameMatch[1].replace(/['"]/g, '');
                        }
                    }
                    
                    // Create download link and trigger download
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                    
                    this.showSuccess('Folder download started');
                } else {
                    const errorData = await response.json();
                    this.showError(errorData.message || 'Failed to download folder');
                }
            } else {
                // For files, get the download URL from the API
                const response = await fetch(`${this.apiBase}/download/file?path=${encodeURIComponent(path)}`, {
                    method: 'GET',
                    redirect: 'manual' // Don't follow redirects automatically
                });
                
                if (response.status === 302 || response.status === 301) {
                    // Get the redirect URL (presigned URL)
                    const downloadUrl = response.headers.get('Location');
                    
                    if (downloadUrl) {
                        // Open in new tab/window for download
                        window.open(downloadUrl, '_blank');
                        this.showSuccess('Download started');
                    } else {
                        this.showError('Failed to get download URL');
                    }
                } else if (response.ok) {
                    // Direct response - shouldn't happen with object storage but handle it
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = path.split('/').pop();
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                    this.showSuccess('Download started');
                } else {
                    const errorData = await response.json();
                    this.showError(errorData.message || 'Failed to download file');
                }
            }
        } catch (error) {
            console.error('Error downloading item:', error);
            this.showError('Failed to download item');
        }
    }
    
    /**
     * Open item (navigate to folder or open file in new window)
     */
    async openItem(path, isDirectory) {
        try {
            if (isDirectory) {
                // Navigate to folder
                this.navigateToPath(path);
            } else {
                // For files, get signed URL and open in new window
                const response = await fetch(`${this.apiBase}/download/file?path=${encodeURIComponent(path)}`, {
                    method: 'GET',
                    redirect: 'manual' // Don't follow redirects automatically
                });
                
                if (response.status === 302 || response.status === 301) {
                    // Get the redirect URL (presigned URL)
                    const fileUrl = response.headers.get('Location');
                    
                    if (fileUrl) {
                        // Open file in new window/tab
                        window.open(fileUrl, '_blank');
                        this.showSuccess('File opened in new window');
                    } else {
                        this.showError('Failed to get file URL');
                    }
                } else {
                    const errorData = await response.json();
                    this.showError(errorData.message || 'Failed to open file');
                }
            }
        } catch (error) {
            console.error('Error opening item:', error);
            this.showError('Failed to open item');
        }
    }
    
    /**
     * Show rename modal
     */
    showRenameModal(path, currentName) {
        const modal = new bootstrap.Modal(document.getElementById('renameModal'));
        const newNameInput = document.getElementById('newName');
        
        newNameInput.value = currentName;
        newNameInput.dataset.path = path;
        
        modal.show();
        
        // Focus and select text
        setTimeout(() => {
            newNameInput.focus();
            newNameInput.select();
        }, 100);
    }
    
    /**
     * Rename item
     */
    async renameItem(e) {
        e.preventDefault();
        
        const newNameInput = document.getElementById('newName');
        const path = newNameInput.dataset.path;
        const newName = newNameInput.value.trim();
        
        if (!newName) return;
        
        try {
            const response = await fetch(`${this.apiBase}/rename`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: path,
                    new_name: newName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Item renamed successfully');
                bootstrap.Modal.getInstance(document.getElementById('renameModal')).hide();
                await this.loadDirectory();
            } else {
                this.showError(data.message || 'Failed to rename item');
            }
        } catch (error) {
            console.error('Error renaming item:', error);
            this.showError('Failed to rename item');
        }
    }
    
    /**
     * Show file information modal
     */
    async showFileInfo(path) {
        try {
            const response = await fetch(`${this.apiBase}/info?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            
            if (data.success) {
                const info = data.data;
                const content = `
                    <div class="row">
                        <div class="col-4"><strong>Name:</strong></div>
                        <div class="col-8">${this.escapeHtml(info.name)}</div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-4"><strong>Type:</strong></div>
                        <div class="col-8">${info.is_directory ? 'Folder' : 'File'}</div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-4"><strong>Size:</strong></div>
                        <div class="col-8">${info.size_formatted}</div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-4"><strong>Modified:</strong></div>
                        <div class="col-8">${this.formatDate(info.modified)}</div>
                    </div>
                    ${info.mime_type ? `
                    <div class="row mt-2">
                        <div class="col-4"><strong>MIME Type:</strong></div>
                        <div class="col-8">${info.mime_type}</div>
                    </div>
                    ` : ''}
                    ${info.checksum ? `
                    <div class="row mt-2">
                        <div class="col-4"><strong>Checksum:</strong></div>
                        <div class="col-8"><code>${info.checksum}</code></div>
                    </div>
                    ` : ''}
                `;
                
                document.getElementById('fileInfoContent').innerHTML = content;
                const modal = new bootstrap.Modal(document.getElementById('fileInfoModal'));
                modal.show();
            } else {
                this.showError('Failed to get file information');
            }
        } catch (error) {
            console.error('Error getting file info:', error);
            this.showError('Failed to get file information');
        }
    }
    
    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + A - Select all
            if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                e.preventDefault();
                this.toggleSelectAll();
            }
            
            // Delete key - Delete selected
            if (e.key === 'Delete' && this.selectedItems.size > 0) {
                e.preventDefault();
                this.deleteSelected();
            }
            
            // F2 - Rename (if single item selected)
            if (e.key === 'F2' && this.selectedItems.size === 1) {
                e.preventDefault();
                const path = Array.from(this.selectedItems)[0];
                const item = document.querySelector(`[data-path="${path}"]`);
                if (item) {
                    this.showRenameModal(path, item.dataset.name);
                }
            }
            
            // Escape - Clear selection
            if (e.key === 'Escape') {
                this.clearSelection();
            }
        });
    }
    
    /**
     * Show success toast
     */
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    /**
     * Show error toast
     */
    showError(message) {
        this.showToast(message, 'danger');
    }
    
    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toastId = 'toast-' + Date.now();
        
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${this.escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    /**
     * Utility: Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Utility: Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Utility: Format date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    /**
     * Show move modal
     */
    showMoveModal(path, name, icon) {
        const modal = new bootstrap.Modal(document.getElementById('moveModal'));
        
        // Set item info
        document.getElementById('moveItemIcon').className = icon;
        document.getElementById('moveItemName').textContent = name;
        document.getElementById('moveNewName').value = '';
        document.getElementById('moveNewName').disabled = false; // Enable for single items
        document.getElementById('copyInsteadOfMove').checked = false;
        
        // Store current item data
        this.moveItemData = { path, name, icon, isBulk: false };
        this.moveCurrentPath = '';
        
        // Load root folders
        this.loadMoveFolders('');
        
        modal.show();
    }
    
    /**
     * Load folders for move modal
     */
    async loadMoveFolders(path) {
        const folderList = document.getElementById('moveFolderList');
        
        // Show loading
        folderList.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted mt-2 mb-0">Loading folders...</p>
            </div>
        `;
        
        try {
            const params = new URLSearchParams({ path });
            const response = await fetch(`${this.apiBase}/?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderMoveFolders(data.data.items, path);
                this.updateMoveBreadcrumbs(data.data.breadcrumbs);
                this.moveCurrentPath = path;
            } else {
                folderList.innerHTML = `
                    <div class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-triangle mb-2"></i>
                        <p class="mb-0">Failed to load folders</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading folders:', error);
            folderList.innerHTML = `
                <div class="text-center py-4 text-danger">
                    <i class="fas fa-exclamation-triangle mb-2"></i>
                    <p class="mb-0">Error loading folders</p>
                </div>
            `;
        }
    }
    
    /**
     * Render folders in move modal
     */
    renderMoveFolders(items, currentPath) {
        const folderList = document.getElementById('moveFolderList');
        const folders = items.filter(item => item.is_directory);
        
        if (folders.length === 0) {
            folderList.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-folder-open mb-2"></i>
                    <p class="mb-0">No folders in this location</p>
                </div>
            `;
            return;
        }
        
        const folderHtml = folders.map(folder => {
            // Don't show the folder we're moving
            if (this.moveItemData && folder.path === this.moveItemData.path) {
                return '';
            }
            
            return `
                <div class="folder-item d-flex align-items-center p-2 rounded hover-bg" 
                     data-path="${folder.path}" style="cursor: pointer;">
                    <i class="${folder.icon} me-2 text-warning"></i>
                    <span class="flex-grow-1">${this.escapeHtml(folder.name)}</span>
                    <small class="text-muted">${this.formatDate(folder.modified)}</small>
                </div>
            `;
        }).join('');
        
        folderList.innerHTML = folderHtml;
        
        // Add click handlers
        folderList.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                this.loadMoveFolders(path);
            });
        });
    }
    
    /**
     * Update move breadcrumbs
     */
    updateMoveBreadcrumbs(breadcrumbs) {
        const breadcrumbNav = document.getElementById('moveBreadcrumb');
        
        breadcrumbNav.innerHTML = breadcrumbs.map((crumb, index) => {
            const isLast = index === breadcrumbs.length - 1;
            const icon = index === 0 ? '<i class="fas fa-home me-1"></i>' : '';
            
            if (isLast) {
                return `<li class="breadcrumb-item active">${icon}${this.escapeHtml(crumb.name)}</li>`;
            } else {
                return `
                    <li class="breadcrumb-item">
                        <a href="#" data-path="${crumb.path}">${icon}${this.escapeHtml(crumb.name)}</a>
                    </li>
                `;
            }
        }).join('');
        
        // Add click handlers to breadcrumb links
        breadcrumbNav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const path = link.dataset.path;
                this.loadMoveFolders(path);
            });
        });
    }
    
    /**
     * Move up one directory
     */
    moveUpDirectory() {
        if (!this.moveCurrentPath) return;
        
        const pathParts = this.moveCurrentPath.split('/');
        pathParts.pop();
        const parentPath = pathParts.join('/');
        
        this.loadMoveFolders(parentPath);
    }
    
    /**
     * Toggle between move and copy mode
     */
    toggleMoveMode() {
        const checkbox = document.getElementById('copyInsteadOfMove');
        const submitBtn = document.getElementById('moveSubmitBtn');
        
        if (checkbox.checked) {
            submitBtn.innerHTML = '<i class="fas fa-copy me-1"></i>Copy';
        } else {
            submitBtn.innerHTML = '<i class="fas fa-arrows-alt me-1"></i>Move';
        }
    }
    
    /**
     * Handle move/copy form submission
     */
    async moveItem(e) {
        e.preventDefault();
        
        const newName = document.getElementById('moveNewName').value.trim();
        const isCopy = document.getElementById('copyInsteadOfMove').checked;
        const destinationPath = this.moveCurrentPath;
        
        try {
            if (this.moveItemData.isBulk) {
                // Handle bulk move
                if (isCopy) {
                    this.showError('Bulk copy operation not yet implemented');
                    return;
                }
                
                // Move multiple items
                const promises = this.moveItemData.paths.map(path => 
                    fetch(`${this.apiBase}/move`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            source_path: path,
                            destination_path: destinationPath
                        })
                    })
                );
                
                const responses = await Promise.all(promises);
                const results = await Promise.all(responses.map(r => r.json()));
                
                const successCount = results.filter(r => r.success).length;
                const failCount = results.length - successCount;
                
                if (successCount > 0) {
                    this.showSuccess(`${successCount} item(s) moved successfully`);
                }
                if (failCount > 0) {
                    this.showError(`${failCount} item(s) failed to move`);
                }
                
                this.clearSelection();
            } else {
                // Handle single item move
                if (isCopy) {
                    this.showError('Copy operation not yet implemented');
                    return;
                }
                
                const response = await fetch(`${this.apiBase}/move`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        source_path: this.moveItemData.path,
                        destination_path: destinationPath,
                        new_name: newName || undefined
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showSuccess('Item moved successfully');
                } else {
                    this.showError(data.message || 'Failed to move item');
                }
            }
            
            bootstrap.Modal.getInstance(document.getElementById('moveModal')).hide();
            await this.loadDirectory();
            
        } catch (error) {
            console.error('Error moving item(s):', error);
            this.showError('Failed to move item(s)');
        }
    }
    
    /**
     * Move selected items
     */
    async moveSelected() {
        if (this.selectedItems.size === 0) return;
        
        if (this.selectedItems.size === 1) {
            // Single item - use the regular move modal
            const path = Array.from(this.selectedItems)[0];
            const item = document.querySelector(`[data-path="${path}"]`);
            if (item) {
                const name = item.dataset.name;
                const icon = item.querySelector('.file-icon').className;
                this.showMoveModal(path, name, icon);
            }
        } else {
            // Multiple items - show simplified move modal
            this.showBulkMoveModal();
        }
    }
    
    /**
     * Show bulk move modal for multiple items
     */
    showBulkMoveModal() {
        const modal = new bootstrap.Modal(document.getElementById('moveModal'));
        
        // Set item info for multiple items
        document.getElementById('moveItemIcon').className = 'fas fa-files';
        document.getElementById('moveItemName').textContent = `${this.selectedItems.size} items`;
        document.getElementById('moveNewName').value = '';
        document.getElementById('moveNewName').disabled = true; // Can't rename multiple items
        document.getElementById('copyInsteadOfMove').checked = false;
        
        // Store bulk move data
        this.moveItemData = { 
            paths: Array.from(this.selectedItems),
            isBulk: true
        };
        this.moveCurrentPath = '';
        
        // Load root folders
        this.loadMoveFolders('');
        
        modal.show();
    }
    
    /**
     * Share item (generate shareable link)
     */
    async shareItem(path, name) {
        try {
            // Get download URL which is a presigned URL that can be shared
            const response = await fetch(`${this.apiBase}/download/file?path=${encodeURIComponent(path)}`, {
                method: 'GET',
                redirect: 'manual' // Don't follow redirects automatically
            });
            
            if (response.status === 302 || response.status === 301) {
                // Get the redirect URL (presigned URL)
                const shareUrl = response.headers.get('Location');
                
                if (shareUrl) {
                    // Show share modal with the URL
                    this.showShareModal(name, shareUrl);
                } else {
                    this.showError('Failed to generate share link');
                }
            } else {
                const errorData = await response.json();
                this.showError(errorData.message || 'Failed to generate share link');
            }
        } catch (error) {
            console.error('Error generating share link:', error);
            this.showError('Failed to generate share link');
        }
    }
    
    /**
     * Show share modal with shareable link
     */
    showShareModal(fileName, shareUrl) {
        // Create a simple modal to show the share link
        const modalHtml = `
            <div class="modal fade" id="shareModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-share me-2"></i>Share File
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p><strong>File:</strong> ${this.escapeHtml(fileName)}</p>
                            <p class="text-muted">Share this link to allow others to download the file:</p>
                            <div class="input-group">
                                <input type="text" class="form-control" id="shareUrl" value="${shareUrl}" readonly>
                                <button class="btn btn-outline-primary" type="button" id="copyShareUrl">
                                    <i class="fas fa-copy"></i> Copy
                                </button>
                            </div>
                            <small class="text-muted mt-2 d-block">
                                <i class="fas fa-clock me-1"></i>This link will expire in 1 hour
                            </small>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing share modal if any
        const existingModal = document.getElementById('shareModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('shareModal'));
        modal.show();
        
        // Add copy functionality
        document.getElementById('copyShareUrl').addEventListener('click', () => {
            const urlInput = document.getElementById('shareUrl');
            urlInput.select();
            urlInput.setSelectionRange(0, 99999); // For mobile devices
            
            try {
                document.execCommand('copy');
                this.showSuccess('Link copied to clipboard');
            } catch (err) {
                // Fallback for modern browsers
                navigator.clipboard.writeText(shareUrl).then(() => {
                    this.showSuccess('Link copied to clipboard');
                }).catch(() => {
                    this.showError('Failed to copy link');
                });
            }
        });
        
        // Clean up modal when hidden
        document.getElementById('shareModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('shareModal').remove();
        });
    }
    
    /**
     * Show delete confirmation modal
     */
    showDeleteModal(items, isBulk = false) {
        const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
        
        // Hide all content sections
        document.getElementById('deleteFileContent').classList.add('d-none');
        document.getElementById('deleteFolderContent').classList.add('d-none');
        document.getElementById('deleteBulkContent').classList.add('d-none');
        
        // Reset form
        document.getElementById('confirmFolderName').value = '';
        document.getElementById('confirmDeleteBtn').disabled = true;
        
        if (isBulk) {
            // Bulk delete
            document.getElementById('deleteBulkContent').classList.remove('d-none');
            document.getElementById('bulkItemCount').textContent = items.length;
            document.getElementById('confirmDeleteBtn').disabled = false;
            this.deleteData = { type: 'bulk', items };
        } else {
            // Single item delete
            const item = items[0];
            const fileItem = document.querySelector(`[data-path="${item.path}"]`);
            const isDirectory = fileItem ? fileItem.dataset.type === 'folder' : false;
            
            if (isDirectory) {
                // Folder delete with name confirmation
                document.getElementById('deleteFolderContent').classList.remove('d-none');
                
                // Set folder name in both places with proper escaping
                const folderNameElement = document.getElementById('deleteFolderName');
                const folderNameToTypeElement = document.getElementById('folderNameToType');
                
                // Use the item name, with fallback to path extraction
                const folderName = item.name || item.path.split('/').pop() || item.path;
                
                folderNameElement.textContent = folderName;
                folderNameToTypeElement.textContent = folderName;
                
                this.deleteData = { type: 'folder', item, requiredName: folderName };
            } else {
                // File delete
                document.getElementById('deleteFileContent').classList.remove('d-none');
                const fileName = item.name || item.path.split('/').pop() || item.path;
                document.getElementById('deleteFileName').textContent = fileName;
                document.getElementById('confirmDeleteBtn').disabled = false;
                this.deleteData = { type: 'file', item };
            }
        }
        
        modal.show();
    }
    
    /**
     * Validate folder name input
     */
    validateFolderName() {
        const input = document.getElementById('confirmFolderName');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        
        if (this.deleteData && this.deleteData.type === 'folder') {
            const isValid = input.value === this.deleteData.requiredName;
            confirmBtn.disabled = !isValid;
            
            // Visual feedback
            if (input.value.length > 0) {
                if (isValid) {
                    input.classList.remove('is-invalid');
                    input.classList.add('is-valid');
                } else {
                    input.classList.remove('is-valid');
                    input.classList.add('is-invalid');
                }
            } else {
                input.classList.remove('is-valid', 'is-invalid');
            }
        }
    }
    
    /**
     * Execute the confirmed delete operation
     */
    async executeDelete() {
        if (!this.deleteData) return;
        
        try {
            if (this.deleteData.type === 'bulk') {
                await this.performBulkDelete(this.deleteData.items);
            } else {
                await this.performSingleDelete(this.deleteData.item);
            }
            
            // Close modal and refresh
            bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
            this.showSuccess('Item(s) deleted successfully');
            
            if (this.deleteData.type === 'bulk') {
                this.clearSelection();
            }
            
            await this.loadDirectory();
            
        } catch (error) {
            console.error('Error deleting items:', error);
            this.showError('Failed to delete item(s)');
        } finally {
            this.deleteData = null;
        }
    }
    
    /**
     * Perform single item delete
     */
    async performSingleDelete(item) {
        const fileItem = document.querySelector(`[data-path="${item.path}"]`);
        const isDirectory = fileItem ? fileItem.dataset.type === 'folder' : false;
        const deletePath = isDirectory && !item.path.endsWith('/') ? item.path + '/' : item.path;
        
        const response = await fetch(`${this.apiBase}/item?path=${encodeURIComponent(deletePath)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to delete item');
        }
    }
    
    /**
     * Perform bulk delete
     */
    async performBulkDelete(items) {
        const promises = items.map(item => {
            const fileItem = document.querySelector(`[data-path="${item.path}"]`);
            const isDirectory = fileItem ? fileItem.dataset.type === 'folder' : false;
            const deletePath = isDirectory && !item.path.endsWith('/') ? item.path + '/' : item.path;
            
            return fetch(`${this.apiBase}/item?path=${encodeURIComponent(deletePath)}`, {
                method: 'DELETE'
            });
        });
        
        const responses = await Promise.all(promises);
        const results = await Promise.all(responses.map(r => r.json()));
        
        const failedItems = results.filter(r => !r.success);
        if (failedItems.length > 0) {
            throw new Error(`Failed to delete ${failedItems.length} item(s)`);
        }
    }
}

// Initialize file manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.fileManager = new FileManager();
}); 