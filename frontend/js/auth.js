const API_BASE = ['5500', '5501'].includes(window.location.port)
    ? `${window.location.protocol}//${window.location.hostname}:5000`
    : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin);

function toggleForm() {
    const loginBox = document.getElementById('loginBox');
    const registerBox = document.getElementById('registerBox');
    if (loginBox.style.display === 'none') {
        loginBox.style.display = 'block';
        registerBox.style.display = 'none';
    } else {
        loginBox.style.display = 'none';
        registerBox.style.display = 'block';
    }
}

// Xử lý sự kiện Đăng Ký
document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('r_email').value;
    const username = document.getElementById('r_user').value;
    const password = document.getElementById('r_pass').value;

    try {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email, username, password })
        });
        const data = await res.json();
        
        if (res.ok) {
            const verifyResponse = await fetch(`${API_BASE}/api/auth/verification/request`, {
                method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({email})
            });
            const verifyData = await verifyResponse.json();
            document.getElementById('authStatus').textContent = verifyResponse.ok
                ? "Đăng ký thành công. " + verifyData.message
                : "Đăng ký thành công nhưng chưa gửi được email xác minh: " + (verifyData.detail || 'Lỗi gửi email');
            toggleForm();
        } else {
            alert("Lỗi: " + (data.detail || "Đăng ký thất bại"));
        }
    } catch (err) {
        alert("Không thể kết nối đến Máy chủ (Backend đang tắt?)");
    }
});

// Xử lý sự kiện Đăng Nhập
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('l_user').value;
    const password = document.getElementById('l_pass').value;

    try {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);

        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: params
        });
        
        const data = await res.json();
        
        if (res.ok) {
            alert("Đăng nhập thành công!");
            sessionStorage.setItem('access_token', data.access_token);
            window.location.href = 'index.html';
        } else {
            alert("Lỗi: " + (data.detail || "Sai tên đăng nhập hoặc mật khẩu"));
        }
    } catch (err) {
        alert("Không thể kết nối đến Máy chủ (Backend đang tắt?)");
    }
});

document.getElementById('resetRequestForm')?.addEventListener('submit', async event => {
    event.preventDefault();
    const response = await fetch(`${API_BASE}/api/auth/password-reset/request`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email:document.getElementById('resetEmail').value.trim()})
    });
    const data = await response.json();
    document.getElementById('authStatus').textContent = data.message || data.detail || 'Không thể gửi liên kết.';
});

document.getElementById('verificationRequestForm')?.addEventListener('submit', async event => {
    event.preventDefault();
    const response = await fetch(`${API_BASE}/api/auth/verification/request`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email:document.getElementById('verificationEmail').value.trim()})
    });
    const data = await response.json();
    document.getElementById('authStatus').textContent = data.message || data.detail || 'Không thể gửi email xác minh.';
});

document.getElementById('resetConfirmForm')?.addEventListener('submit', async event => {
    event.preventDefault();
    const token = new URLSearchParams(window.location.search).get('reset-password');
    const response = await fetch(`${API_BASE}/api/auth/password-reset/confirm`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({token, new_password:document.getElementById('resetNewPassword').value})
    });
    const data = await response.json();
    document.getElementById('authStatus').textContent = data.message || data.detail || 'Không thể đổi mật khẩu.';
    if (response.ok) {
        window.history.replaceState({}, '', window.location.pathname);
        document.getElementById('resetConfirmBox').style.display = 'none';
        document.getElementById('loginBox').style.display = 'block';
        event.target.reset();
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const verifyToken = params.get('verify-email');
    const resetToken = params.get('reset-password');
    if (verifyToken) {
        const response = await fetch(`${API_BASE}/api/auth/verification/confirm`, {
            method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token:verifyToken})
        });
        const data = await response.json();
        document.getElementById('authStatus').textContent = data.message || data.detail || 'Không thể xác minh email.';
        window.history.replaceState({}, '', window.location.pathname);
    }
    if (resetToken) {
        document.getElementById('loginBox').style.display = 'none';
        document.getElementById('registerBox').style.display = 'none';
        document.getElementById('resetRequestBox').style.display = 'none';
        document.getElementById('resetConfirmBox').style.display = 'block';
    }
});
