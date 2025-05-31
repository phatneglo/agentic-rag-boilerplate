/**
 * File Operations Module
 * 
 * Handles file-specific operations like upload, download, and manipulation.
 * This module is designed to be reusable across different applications.
 */

class FileOperations {
    constructor(apiBase = '/api/v1/file-manager') {
        this.apiBase = apiBase;
        this.uploadQueue = [];
        this.isUploading = false;
    }
    
    /**
     * Upload multiple files with progress tracking
     */
    async uploadFiles(files, path = '', onProgress = null, onComplete = null) {
        if (this.isUploading) {
            throw new Error('Upload already in progress');
        }
        
        this.isUploading = true;
        const results = [];
        
        try {
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                
                // Update progress
                if (onProgress) {
                    onProgress({
                        current: i + 1,
                        total: files.length,
                        fileName: file.name,
                        percentage: Math.round(((i + 1) / files.length) * 100)
                    });
                }
                
                try {
                    const result = await this.uploadSingleFile(file, path);
                    results.push({ file: file.name, success: true, result });
                } catch (error) {
                    results.push({ file: file.name, success: false, error: error.message });
                }
            }
            
            if (onComplete) {
                onComplete(results);
            }
            
            return results;
            
        } finally {
            this.isUploading = false;
        }
    }
    
    /**
     * Upload a single file
     */
    async uploadSingleFile(file, path = '') {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('path', path);
        
        const response = await fetch(`${this.apiBase}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Upload failed');
        }
        
        return data;
    }
    
    /**
     * Download a file
     */
    downloadFile(path, filename = null) {
        const url = `${this.apiBase}/download/file?path=${encodeURIComponent(path)}`;
        this.triggerDownload(url, filename);
    }
    
    /**
     * Download a folder as zip
     */
    downloadFolder(path, filename = null) {
        const url = `${this.apiBase}/download/folder?path=${encodeURIComponent(path)}`;
        this.triggerDownload(url, filename);
    }
    
    /**
     * Trigger browser download
     */
    triggerDownload(url, filename = null) {
        const link = document.createElement('a');
        link.href = url;
        if (filename) {
            link.download = filename;
        }
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    /**
     * Create a new folder
     */
    async createFolder(path, folderName) {
        const response = await fetch(`${this.apiBase}/folder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                path: path,
                folder_name: folderName
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to create folder');
        }
        
        return data;
    }
    
    /**
     * Rename an item
     */
    async renameItem(path, newName) {
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
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to rename item');
        }
        
        return data;
    }
    
    /**
     * Move an item
     */
    async moveItem(sourcePath, destinationPath) {
        const response = await fetch(`${this.apiBase}/move`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                source_path: sourcePath,
                destination_path: destinationPath
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to move item');
        }
        
        return data;
    }
    
    /**
     * Delete an item
     */
    async deleteItem(path) {
        const response = await fetch(`${this.apiBase}/item?path=${encodeURIComponent(path)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to delete item');
        }
        
        return data;
    }
    
    /**
     * Delete multiple items
     */
    async deleteItems(paths) {
        const promises = paths.map(path => this.deleteItem(path));
        const results = await Promise.allSettled(promises);
        
        const successful = [];
        const failed = [];
        
        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                successful.push(paths[index]);
            } else {
                failed.push({
                    path: paths[index],
                    error: result.reason.message
                });
            }
        });
        
        return { successful, failed };
    }
    
    /**
     * Get file information
     */
    async getFileInfo(path) {
        const response = await fetch(`${this.apiBase}/info?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to get file information');
        }
        
        return data.data;
    }
    
    /**
     * Search files
     */
    async searchFiles(query, path = '') {
        const params = new URLSearchParams({
            query: query,
            path: path
        });
        
        const response = await fetch(`${this.apiBase}/search?${params}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Search failed');
        }
        
        return data.data;
    }
    
    /**
     * List directory contents
     */
    async listDirectory(path = '', search = '') {
        const params = new URLSearchParams({
            path: path,
            search: search
        });
        
        const response = await fetch(`${this.apiBase}/?${params}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to list directory');
        }
        
        return data.data;
    }
    
    /**
     * Validate file before upload
     */
    validateFile(file, maxSizeMB = 100, allowedExtensions = []) {
        const errors = [];
        
        // Check file size
        const maxSizeBytes = maxSizeMB * 1024 * 1024;
        if (file.size > maxSizeBytes) {
            errors.push(`File size exceeds ${maxSizeMB}MB limit`);
        }
        
        // Check file extension
        if (allowedExtensions.length > 0) {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            if (!allowedExtensions.includes(extension)) {
                errors.push(`File type ${extension} is not allowed`);
            }
        }
        
        // Check file name
        if (!file.name || file.name.trim() === '') {
            errors.push('File name cannot be empty');
        }
        
        return {
            valid: errors.length === 0,
            errors: errors
        };
    }
    
    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    /**
     * Get file icon class based on extension
     */
    getFileIcon(filename, isDirectory = false) {
        if (isDirectory) {
            return 'fas fa-folder';
        }
        
        const extension = filename.split('.').pop().toLowerCase();
        const iconMap = {
            // Images
            'jpg': 'fas fa-image', 'jpeg': 'fas fa-image', 'png': 'fas fa-image',
            'gif': 'fas fa-image', 'bmp': 'fas fa-image', 'svg': 'fas fa-image',
            'webp': 'fas fa-image', 'ico': 'fas fa-image',
            
            // Documents
            'pdf': 'fas fa-file-pdf', 'doc': 'fas fa-file-word', 'docx': 'fas fa-file-word',
            'xls': 'fas fa-file-excel', 'xlsx': 'fas fa-file-excel',
            'ppt': 'fas fa-file-powerpoint', 'pptx': 'fas fa-file-powerpoint',
            'txt': 'fas fa-file-alt', 'rtf': 'fas fa-file-alt',
            
            // Code files
            'html': 'fas fa-code', 'css': 'fas fa-code', 'js': 'fas fa-code',
            'py': 'fas fa-code', 'java': 'fas fa-code', 'cpp': 'fas fa-code',
            'c': 'fas fa-code', 'php': 'fas fa-code', 'rb': 'fas fa-code',
            'go': 'fas fa-code', 'rs': 'fas fa-code', 'ts': 'fas fa-code',
            'json': 'fas fa-code', 'xml': 'fas fa-code', 'yaml': 'fas fa-code',
            'yml': 'fas fa-code',
            
            // Archives
            'zip': 'fas fa-file-archive', 'rar': 'fas fa-file-archive',
            '7z': 'fas fa-file-archive', 'tar': 'fas fa-file-archive',
            'gz': 'fas fa-file-archive', 'bz2': 'fas fa-file-archive',
            
            // Audio
            'mp3': 'fas fa-file-audio', 'wav': 'fas fa-file-audio',
            'flac': 'fas fa-file-audio', 'aac': 'fas fa-file-audio',
            'ogg': 'fas fa-file-audio', 'm4a': 'fas fa-file-audio',
            
            // Video
            'mp4': 'fas fa-file-video', 'avi': 'fas fa-file-video',
            'mkv': 'fas fa-file-video', 'mov': 'fas fa-file-video',
            'wmv': 'fas fa-file-video', 'flv': 'fas fa-file-video',
            'webm': 'fas fa-file-video',
        };
        
        return iconMap[extension] || 'fas fa-file';
    }
    
    /**
     * Check if file is previewable
     */
    isPreviewable(filename, mimeType = null) {
        const extension = filename.split('.').pop().toLowerCase();
        const previewableExtensions = [
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
            'txt', 'md', 'json', 'xml', 'html', 'css', 'js',
            'pdf'
        ];
        
        if (previewableExtensions.includes(extension)) {
            return true;
        }
        
        if (mimeType) {
            return mimeType.startsWith('image/') || 
                   mimeType.startsWith('text/') ||
                   mimeType === 'application/json' ||
                   mimeType === 'application/xml' ||
                   mimeType === 'application/pdf';
        }
        
        return false;
    }
    
    /**
     * Generate preview URL for file
     */
    getPreviewUrl(path) {
        return `${this.apiBase}/preview?path=${encodeURIComponent(path)}`;
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.FileOperations = FileOperations;
} 