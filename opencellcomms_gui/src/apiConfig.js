const configuredUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5001';

export const API_BASE_URL = configuredUrl.replace(/\/$/, '');
export const API_ROOT_URL = `${API_BASE_URL}/api`;
