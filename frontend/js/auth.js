/**
 * Authentication Module
 * Handles JWT token management and authentication
 */

const Auth = (function () {
    const API_BASE = `http://${window.location.hostname}:8000/api`;
    const TOKEN_KEY = 'invoice_hub_token';
    const USER_KEY = 'invoice_hub_user';

    /**
     * Login with username and password
     */
    async function login(username, password) {
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            if (response.ok) {
                const data = await response.json();
                setToken(data.access_token);

                // Fetch user info
                await fetchUserInfo();

                return { success: true };
            } else {
                const error = await response.json();
                let message = 'Đăng nhập thất bại';

                if (response.status === 401) {
                    message = 'Tên đăng nhập hoặc mật khẩu không đúng';
                } else if (response.status === 423) {
                    message = 'Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.';
                } else if (response.status === 403) {
                    message = 'Tài khoản đã bị vô hiệu hóa';
                }

                return { success: false, error: message };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: 'Lỗi kết nối đến máy chủ' };
        }
    }

    /**
     * Fetch current user info
     */
    async function fetchUserInfo() {
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${getToken()}`,
                },
            });

            if (response.ok) {
                const user = await response.json();
                localStorage.setItem(USER_KEY, JSON.stringify(user));
                return user;
            }
        } catch (error) {
            console.error('Fetch user error:', error);
        }
        return null;
    }

    /**
     * Logout and clear tokens
     */
    function logout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        window.location.href = 'login.html';
    }

    /**
     * Get stored token
     */
    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    /**
     * Set token
     */
    function setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    }

    /**
     * Check if user is authenticated
     */
    function isAuthenticated() {
        const token = getToken();
        if (!token) return false;

        // Check if token is expired
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const exp = payload.exp * 1000; // Convert to milliseconds
            return Date.now() < exp;
        } catch (e) {
            return false;
        }
    }

    /**
     * Get current user info
     */
    function getUser() {
        const userStr = localStorage.getItem(USER_KEY);
        return userStr ? JSON.parse(userStr) : null;
    }

    /**
     * Check auth and redirect to login if not authenticated
     */
    function checkAuth() {
        if (!isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    /**
     * Get authorization header for API calls
     */
    function getAuthHeader() {
        const token = getToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    // Public API
    return {
        login,
        logout,
        getToken,
        isAuthenticated,
        checkAuth,
        getUser,
        getAuthHeader,
        fetchUserInfo,
    };
})();
