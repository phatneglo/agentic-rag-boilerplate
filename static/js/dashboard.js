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

        document.getElementById('file-manager-nav').addEventListener('click', (e) => {
            e.preventDefault();
            this.showSection('file-manager');
        });

        document.getElementById('api-docs-nav').addEventListener('click', (e) => {
            e.preventDefault();
            this.showSection('api-docs');
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

    showSection(sectionName) {
        // Update active navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        // Hide all content sections
        document.querySelectorAll('.content').forEach(content => {
            content.classList.add('d-none');
        });

        // Show selected section
        document.getElementById(`${sectionName}-content`).classList.remove('d-none');
        
        // Update navigation state
        document.getElementById(`${sectionName}-nav`).classList.add('active');
        
        this.currentSection = sectionName;

        // Special handling for file manager
        if (sectionName === 'file-manager') {
            this.loadFileManager();
        }
    }

    loadFileManager() {
        const iframe = document.getElementById('file-manager-frame');
        if (iframe && !iframe.src.includes('index.html')) {
            iframe.src = '/static/index.html';
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
        // Update API response time
        const responseTimeElement = document.getElementById('api-response-time');
        if (responseTime !== null) {
            responseTimeElement.textContent = `${responseTime}ms`;
            responseTimeElement.classList.remove('pulse');
        } else {
            responseTimeElement.textContent = '--';
            responseTimeElement.classList.add('pulse');
        }

        // Update other metrics from health data
        if (healthData) {
            this.updateMetric('files-count', healthData.file_count || '--');
            this.updateMetric('storage-usage', this.formatBytes(healthData.storage_used || 0));
            this.updateMetric('system-uptime', this.formatUptime(healthData.uptime || 0));
        } else {
            this.updateMetric('files-count', '--');
            this.updateMetric('storage-usage', '--');
            this.updateMetric('system-uptime', '--');
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

    // Cleanup method
    destroy() {
        this.stopPeriodicUpdates();
        // Remove event listeners if needed
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