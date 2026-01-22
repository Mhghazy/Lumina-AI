/**
 * Production Environment Configuration
 * This file centralizes the backend API URL for the frontend.
 */

// If you have a specific production backend URL (e.g. from Render or Railway), 
// set it here. Otherwise, the system will try to use localhost for local development.
const PROD_BACKEND_URL = ''; // e.g. 'https://my-backend.onrender.com'

const getBackendUrl = () => {
    // If a production URL is specified, use it
    if (PROD_BACKEND_URL) return PROD_BACKEND_URL;

    // Otherwise, check if we are on localhost
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal) return 'http://localhost:5000';

    // Fallback: If no prod URL and not local, return empty (relative paths might work if proxied)
    return '';
};

window.BACKEND_API_URL = getBackendUrl();
console.log('🌐 Backend API URL:', window.BACKEND_API_URL || 'Using relative paths');
