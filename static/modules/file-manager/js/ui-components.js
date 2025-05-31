/**
 * UI Components Module
 * 
 * Provides reusable UI components and utilities for the file manager.
 * This module is designed to be framework-agnostic and easily portable.
 */

class UIComponents {
    constructor() {
        this.toastContainer = null;
        this.modalInstances = new Map();
        this.init();
    }
    
    /**
     * Initialize UI components
     */
    init() {
        this.toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        this.setupGlobalEventListeners();
    }
    
    /**
     * Create toast container if it doesn't exist
     */
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }
    
    /**
     * Setup global event listeners
     */
    setupGlobalEventListeners() {
        // Close modals on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeTopModal();
            }
        });
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown')) {
                this.closeAllDropdowns();
            }
        });
    }
    
    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 5000) {
        const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const iconMap = {
            'success': 'fas fa-check-circle',
            'danger': 'fas fa-exclamation-circle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        };
        
        const icon = iconMap[type] || iconMap['info'];
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center">
                    <i class="${icon} me-2"></i>
                    ${this.escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Initialize Bootstrap toast if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, { delay: duration });
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        } else {
            // Fallback for non-Bootstrap environments
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
        
        return toastId;
    }
    
    /**
     * Show success toast
     */
    showSuccess(message, duration = 5000) {
        return this.showToast(message, 'success', duration);
    }
    
    /**
     * Show error toast
     */
    showError(message, duration = 8000) {
        return this.showToast(message, 'danger', duration);
    }
    
    /**
     * Show warning toast
     */
    showWarning(message, duration = 6000) {
        return this.showToast(message, 'warning', duration);
    }
    
    /**
     * Show info toast
     */
    showInfo(message, duration = 5000) {
        return this.showToast(message, 'info', duration);
    }
    
    /**
     * Show confirmation dialog
     */
    showConfirmDialog(title, message, onConfirm, onCancel = null) {
        const modalId = 'confirmModal-' + Date.now();
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = modalId;
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-question-circle text-warning me-2"></i>
                            ${this.escapeHtml(title)}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>${this.escapeHtml(message)}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-danger" id="${modalId}-confirm">Confirm</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Handle confirm button
        document.getElementById(`${modalId}-confirm`).addEventListener('click', () => {
            if (onConfirm) onConfirm();
            this.closeModal(modalId);
        });
        
        // Handle cancel
        modal.addEventListener('hidden.bs.modal', () => {
            if (onCancel) onCancel();
            modal.remove();
        });
        
        this.showModal(modalId);
        return modalId;
    }
    
    /**
     * Show input dialog
     */
    showInputDialog(title, placeholder, defaultValue = '', onSubmit, onCancel = null) {
        const modalId = 'inputModal-' + Date.now();
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = modalId;
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-edit me-2"></i>
                            ${this.escapeHtml(title)}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="${modalId}-form">
                            <div class="mb-3">
                                <input type="text" class="form-control" id="${modalId}-input" 
                                       placeholder="${this.escapeHtml(placeholder)}" 
                                       value="${this.escapeHtml(defaultValue)}" required>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="submit" form="${modalId}-form" class="btn btn-primary">Submit</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const input = document.getElementById(`${modalId}-input`);
        const form = document.getElementById(`${modalId}-form`);
        
        // Handle form submission
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const value = input.value.trim();
            if (value && onSubmit) {
                onSubmit(value);
                this.closeModal(modalId);
            }
        });
        
        // Handle cancel
        modal.addEventListener('hidden.bs.modal', () => {
            if (onCancel) onCancel();
            modal.remove();
        });
        
        this.showModal(modalId);
        
        // Focus and select input
        setTimeout(() => {
            input.focus();
            input.select();
        }, 100);
        
        return modalId;
    }
    
    /**
     * Show loading overlay
     */
    showLoading(message = 'Loading...', target = null) {
        const loadingId = 'loading-' + Date.now();
        
        const overlay = document.createElement('div');
        overlay.id = loadingId;
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">${this.escapeHtml(message)}</p>
            </div>
        `;
        
        // Add CSS if not already present
        if (!document.getElementById('loading-overlay-styles')) {
            const style = document.createElement('style');
            style.id = 'loading-overlay-styles';
            style.textContent = `
                .loading-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(255, 255, 255, 0.9);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                }
                .loading-content {
                    text-align: center;
                }
            `;
            document.head.appendChild(style);
        }
        
        (target || document.body).appendChild(overlay);
        return loadingId;
    }
    
    /**
     * Hide loading overlay
     */
    hideLoading(loadingId) {
        const overlay = document.getElementById(loadingId);
        if (overlay) {
            overlay.remove();
        }
    }
    
    /**
     * Show modal
     */
    showModal(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = new bootstrap.Modal(modalElement);
                this.modalInstances.set(modalId, modal);
                modal.show();
            } else {
                // Fallback for non-Bootstrap environments
                modalElement.style.display = 'block';
                modalElement.classList.add('show');
            }
        }
    }
    
    /**
     * Close modal
     */
    closeModal(modalId) {
        const modal = this.modalInstances.get(modalId);
        if (modal) {
            modal.hide();
            this.modalInstances.delete(modalId);
        } else {
            const modalElement = document.getElementById(modalId);
            if (modalElement) {
                modalElement.style.display = 'none';
                modalElement.classList.remove('show');
            }
        }
    }
    
    /**
     * Close top modal
     */
    closeTopModal() {
        const modals = document.querySelectorAll('.modal.show');
        if (modals.length > 0) {
            const topModal = modals[modals.length - 1];
            const modalId = topModal.id;
            this.closeModal(modalId);
        }
    }
    
    /**
     * Close all dropdowns
     */
    closeAllDropdowns() {
        document.querySelectorAll('.dropdown-menu.show').forEach(dropdown => {
            dropdown.classList.remove('show');
        });
    }
    
    /**
     * Create progress bar
     */
    createProgressBar(container, label = '') {
        const progressId = 'progress-' + Date.now();
        
        const progressHtml = `
            <div class="progress-container mb-3" id="${progressId}">
                ${label ? `<label class="form-label">${this.escapeHtml(label)}</label>` : ''}
                <div class="progress">
                    <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                </div>
                <small class="text-muted progress-text">0%</small>
            </div>
        `;
        
        if (typeof container === 'string') {
            container = document.getElementById(container);
        }
        
        container.insertAdjacentHTML('beforeend', progressHtml);
        
        return {
            id: progressId,
            update: (percentage, text = null) => {
                const progressBar = document.querySelector(`#${progressId} .progress-bar`);
                const progressText = document.querySelector(`#${progressId} .progress-text`);
                
                if (progressBar) {
                    progressBar.style.width = `${percentage}%`;
                    progressBar.setAttribute('aria-valuenow', percentage);
                }
                
                if (progressText) {
                    progressText.textContent = text || `${percentage}%`;
                }
            },
            remove: () => {
                const element = document.getElementById(progressId);
                if (element) element.remove();
            }
        };
    }
    
    /**
     * Create context menu
     */
    createContextMenu(items, x, y) {
        // Remove existing context menus
        document.querySelectorAll('.custom-context-menu').forEach(menu => menu.remove());
        
        const menu = document.createElement('div');
        menu.className = 'custom-context-menu';
        menu.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 0.5rem;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            padding: 0.5rem 0;
            min-width: 180px;
            z-index: 1050;
        `;
        
        items.forEach(item => {
            if (item.separator) {
                const separator = document.createElement('hr');
                separator.className = 'my-1';
                menu.appendChild(separator);
            } else {
                const menuItem = document.createElement('a');
                menuItem.href = '#';
                menuItem.className = 'context-menu-item';
                menuItem.style.cssText = `
                    display: block;
                    padding: 0.5rem 1rem;
                    color: #212529;
                    text-decoration: none;
                    font-size: 0.875rem;
                    transition: background-color 0.2s ease;
                `;
                
                menuItem.innerHTML = `
                    ${item.icon ? `<i class="${item.icon} me-2"></i>` : ''}
                    ${this.escapeHtml(item.label)}
                `;
                
                menuItem.addEventListener('mouseenter', () => {
                    menuItem.style.backgroundColor = '#f8f9fa';
                });
                
                menuItem.addEventListener('mouseleave', () => {
                    menuItem.style.backgroundColor = 'transparent';
                });
                
                menuItem.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (item.action) item.action();
                    menu.remove();
                });
                
                menu.appendChild(menuItem);
            }
        });
        
        document.body.appendChild(menu);
        
        // Close menu when clicking outside
        const closeMenu = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        
        setTimeout(() => {
            document.addEventListener('click', closeMenu);
        }, 0);
        
        return menu;
    }
    
    /**
     * Format date for display
     */
    formatDate(dateString, options = {}) {
        const date = new Date(dateString);
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
    }
    
    /**
     * Format relative time
     */
    formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSecs < 60) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        
        return this.formatDate(dateString);
    }
    
    /**
     * Debounce function
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
     * Throttle function
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
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
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showSuccess('Copied to clipboard');
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.showSuccess('Copied to clipboard');
                return true;
            } catch (fallbackErr) {
                this.showError('Failed to copy to clipboard');
                return false;
            } finally {
                document.body.removeChild(textArea);
            }
        }
    }
    
    /**
     * Animate element
     */
    animate(element, animation, duration = 300) {
        return new Promise(resolve => {
            element.style.animation = `${animation} ${duration}ms ease`;
            
            const handleAnimationEnd = () => {
                element.style.animation = '';
                element.removeEventListener('animationend', handleAnimationEnd);
                resolve();
            };
            
            element.addEventListener('animationend', handleAnimationEnd);
        });
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.UIComponents = UIComponents;
} 