const API_BASE = window.location.origin.includes('5500')
    ? window.location.origin.replace(':5500', ':5000')
    : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin);

function getAuthToken() {
    return sessionStorage.getItem('access_token');
}

function authHeaders() {
    const token = getAuthToken();
    return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

function initNav() {
    const token = getAuthToken();
    const navLoginBtn = document.getElementById('navLoginBtn');
    const navLogoutBtn = document.getElementById('navLogoutBtn');
    const navUserInfo = document.getElementById('navUserInfo');
    const navProfileLink = document.getElementById('navProfileLink');

    if (token) {
        if (navLoginBtn) navLoginBtn.style.display = 'none';
        if (navLogoutBtn) navLogoutBtn.style.display = 'inline';
        if (navProfileLink) navProfileLink.style.display = 'inline';

        fetch(`${API_BASE}/api/users/profile`, { headers: authHeaders() })
            .then(res => {
                if (res.status === 401) {
                    logout();
                    return null;
                }
                return res.json();
            })
            .then(data => {
                if (data && data.username && navUserInfo) {
                    navUserInfo.style.display = 'inline-flex';
                    navUserInfo.innerHTML = `<span style="background: #0ea5e9; color: white; padding: 4px 10px; border-radius: 9999px; font-size: 0.85rem; font-weight: bold;">👤 ${data.username} | ⭐ ${data.total_points}đ (Rank #${data.server_rank})</span>`;
                }
            })
            .catch(() => {});
    } else {
        if (navLoginBtn) navLoginBtn.style.display = 'inline';
        if (navLogoutBtn) navLogoutBtn.style.display = 'none';
        if (navProfileLink) navProfileLink.style.display = 'none';
        if (navUserInfo) navUserInfo.style.display = 'none';
    }
}

function logout() {
    sessionStorage.removeItem('access_token');
    localStorage.removeItem('access_token');
    window.location.href = 'login.html';
}

document.addEventListener('DOMContentLoaded', initNav);
