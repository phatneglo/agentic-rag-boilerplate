/**
 * Authentication Configuration for File Manager
 * 
 * Global JWT token configuration and utilities for authenticated API requests.
 */

// Global JWT Token - Replace with actual token from your authentication system
// This is a sample token for testing - userid: "user123", username: "sampleuser"
window.EW_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyaWQiOiJ1c2VyMTIzIiwidXNlcm5hbWUiOiJzYW1wbGV1c2VyIiwiZW1haWwiOiJzYW1wbGVAZXhhbXBsZS5jb20iLCJpYXQiOjE3NDg2NDc3MzksImV4cCI6MTc0ODczNDEzOX0.h5Hal8VsOD6sOLFZVBG_UpLdV5D1FVy_j-bSdRgEDpE";

// Authentication utility functions
window.AuthUtils = {
    
    /**
     * Get the current JWT token
     * @returns {string} JWT token
     */
    getToken() {
        return window.EW_TOKEN;
    },
    
    /**
     * Set a new JWT token
     * @param {string} token - JWT token
     */
    setToken(token) {
        window.EW_TOKEN = token;
    },
    
    /**
     * Get Authorization header for API requests
     * @returns {Object} Headers object with Authorization
     */
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.getToken()}`,
            'Content-Type': 'application/json'
        };
    },
    
    /**
     * Get Authorization header for form data requests
     * @returns {Object} Headers object with Authorization (no Content-Type for FormData)
     */
    getAuthHeadersForFormData() {
        return {
            'Authorization': `Bearer ${this.getToken()}`
        };
    },
    
    /**
     * Decode JWT token to get user information (basic decode, no verification)
     * @returns {Object|null} Decoded token payload or null if invalid
     */
    decodeToken() {
        try {
            const token = this.getToken();
            if (!token) return null;
            
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
                atob(base64)
                    .split('')
                    .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
            );
            
            return JSON.parse(jsonPayload);
        } catch (e) {
            console.error('Error decoding token:', e);
            return null;
        }
    },
    
    /**
     * Get current user information from token
     * @returns {Object|null} User info or null if no valid token
     */
    getCurrentUser() {
        const decoded = this.decodeToken();
        if (!decoded) return null;
        
        return {
            userid: decoded.userid,
            username: decoded.username,
            email: decoded.email
        };
    },
    
    /**
     * Check if token is expired
     * @returns {boolean} True if token is expired
     */
    isTokenExpired() {
        const decoded = this.decodeToken();
        if (!decoded || !decoded.exp) return true;
        
        const currentTime = Math.floor(Date.now() / 1000);
        return decoded.exp < currentTime;
    },
    
    /**
     * Check if user is authenticated with valid token
     * @returns {boolean} True if authenticated
     */
    isAuthenticated() {
        const token = this.getToken();
        return token && !this.isTokenExpired();
    }
};

// Display current user info in console for development
console.log('🔐 Authentication Configuration Loaded');
console.log('Current User:', window.AuthUtils.getCurrentUser());
console.log('Token Valid:', window.AuthUtils.isAuthenticated());

// Show user info in the UI if elements exist
document.addEventListener('DOMContentLoaded', () => {
    const user = window.AuthUtils.getCurrentUser();
    if (user) {
        // Try to display user info in the navbar if elements exist
        const userInfoElements = document.querySelectorAll('.user-info, #userInfo');
        userInfoElements.forEach(element => {
            element.textContent = `👤 ${user.username} (${user.userid})`;
        });
        
        // Add user info to the navbar brand if it exists
        const navbarBrand = document.querySelector('.navbar-brand');
        if (navbarBrand) {
            const userSpan = document.createElement('small');
            userSpan.className = 'text-muted ms-2';
            userSpan.textContent = `👤 ${user.username}`;
            navbarBrand.appendChild(userSpan);
        }
    }
}); 