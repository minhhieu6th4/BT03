const API_BASE = window.location.origin.includes('5500')
    ? window.location.origin.replace(':5500', ':5000')
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
            alert("Đăng ký thành công! Bạn có thể đăng nhập ngay bây giờ.");
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
