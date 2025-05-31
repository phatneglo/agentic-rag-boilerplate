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
        
        // Modal forms
        document.getElementById('newFolderForm').addEventListener('submit', this.createFolder.bind(this));
        document.getElementById('renameForm').addEventListener('submit', this.renameItem.bind(this));
        
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
                this.renderDirectory(data.data);
                this.updateBreadcrumbs(data.data.breadcrumbs);
                this.updateItemCount(data.data.total_items);
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
     * Render directory contents
     */
    renderDirectory(data) {
        const fileGrid = document.getElementById('fileGrid');
        const emptyState = document.getElementById('emptyState');
        
        if (data.items.length === 0) {
            fileGrid.innerHTML = '';
            emptyState.classList.remove('d-none');
            return;
        }
        
        emptyState.classList.add('d-none');
        
        // Sort items
        const sortedItems = this.sortItems(data.items);
        
        // Render items
        fileGrid.innerHTML = sortedItems.map(item => this.renderFileItem(item)).join('');
        
        // Apply view mode
        fileGrid.className = `file-grid ${this.viewMode === 'list' ? 'list-view' : ''}`;
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
        this.searchQuery = e.target.value.trim();
        await this.loadDirectory();
    }
    
    /**
     * Clear search
     */
    async clearSearch() {
        document.getElementById('searchInput').value = '';
        this.searchQuery = '';
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
     * Delete selected items
     */
    async deleteSelected() {
        if (this.selectedItems.size === 0) return;
        
        const confirmed = confirm(`Are you sure you want to delete ${this.selectedItems.size} item(s)?`);
        if (!confirmed) return;
        
        const promises = Array.from(this.selectedItems).map(path => 
            fetch(`${this.apiBase}/item?path=${encodeURIComponent(path)}`, {
                method: 'DELETE'
            })
        );
        
        try {
            await Promise.all(promises);
            this.showSuccess('Items deleted successfully');
            this.clearSelection();
            await this.loadDirectory();
        } catch (error) {
            console.error('Error deleting items:', error);
            this.showError('Failed to delete some items');
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
        
        progressContainer.classList.remove('d-none');
        
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
                
                if (!data.success) {
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
        
        progressContainer.classList.add('d-none');
        bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
        this.showSuccess('Files uploaded successfully');
        await this.loadDirectory();
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
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.uploadFiles(files);
            }
        });
        
        uploadArea.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
        
        // Main area drag and drop
        fileContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
        });
        
        fileContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.uploadFiles(files);
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
        const name = target.dataset.name;
        const isDirectory = target.dataset.type === 'folder';
        
        switch (action) {
            case 'open':
                if (isDirectory) {
                    this.navigateToPath(path);
                }
                break;
                
            case 'download':
                this.downloadItem(path, isDirectory);
                break;
                
            case 'rename':
                this.showRenameModal(path, name);
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
    downloadItem(path, isDirectory) {
        const endpoint = isDirectory ? 'download/folder' : 'download/file';
        const url = `${this.apiBase}/${endpoint}?path=${encodeURIComponent(path)}`;
        
        const link = document.createElement('a');
        link.href = url;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
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
     * Delete single item
     */
    async deleteItem(path, name) {
        const confirmed = confirm(`Are you sure you want to delete "${name}"?`);
        if (!confirmed) return;
        
        try {
            const response = await fetch(`${this.apiBase}/item?path=${encodeURIComponent(path)}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Item deleted successfully');
                await this.loadDirectory();
            } else {
                this.showError(data.message || 'Failed to delete item');
            }
        } catch (error) {
            console.error('Error deleting item:', error);
            this.showError('Failed to delete item');
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
}

// Initialize file manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.fileManager = new FileManager();
}); 