const API_BASE = ['5500', '5501'].includes(window.location.port)
    ? `${window.location.protocol}//${window.location.hostname}:5000`
    : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin);

function getAuthToken() {
    return sessionStorage.getItem('access_token');
}

function authHeaders() {
    const token = getAuthToken();
    return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

function addNavLink(id, href, label) {
    const nav = document.querySelector('header nav');
    if (!nav || document.getElementById(id)) return;
    const link = document.createElement('a');
    link.id = id;
    link.href = href;
    link.textContent = label;
    nav.appendChild(link);
}

async function refreshNotificationBadge() {
    if (!getAuthToken()) return;
    try {
        const response = await fetch(`${API_BASE}/api/notifications/?limit=1`, { headers: authHeaders() });
        if (!response.ok) return;
        const data = await response.json();
        const link = document.getElementById('navNotificationsLink');
        if (link) link.textContent = data.unread_count ? `Thông báo (${data.unread_count})` : 'Thông báo';
    } catch (_) {}
}

function connectNotificationStream() {
    const token = getAuthToken();
    if (!token || window.notificationSocket) return;
    const socketUrl = `${API_BASE.replace(/^http/, 'ws')}/api/notifications/ws`;
    const socket = new WebSocket(socketUrl);
    window.notificationSocket = socket;
    socket.addEventListener('open', () => socket.send(JSON.stringify({token})));
    socket.addEventListener('message', event => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'notification') refreshNotificationBadge();
        } catch (_) {}
    });
    socket.addEventListener('close', () => {
        window.notificationSocket = null;
        if (getAuthToken()) window.setTimeout(connectNotificationStream, 5000);
    });
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
        addNavLink('navTeamsLink', 'teams.html', 'Đội của tôi');
        addNavLink('navNotificationsLink', 'notifications.html', 'Thông báo');
        refreshNotificationBadge();
        connectNotificationStream();
        window.setInterval(refreshNotificationBadge, 15000);

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
                    navUserInfo.textContent = `👤 ${data.username} | ⭐ ${data.total_points}đ (Rank #${data.server_rank})`;
                }
            })
            .catch(() => {});
        fetch(`${API_BASE}/api/users/me`, { headers: authHeaders() })
            .then(res => res.ok ? res.json() : null)
            .then(user => {
                if (user?.is_admin) addNavLink('navAdminLink', 'admin.html', 'Quản trị');
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
