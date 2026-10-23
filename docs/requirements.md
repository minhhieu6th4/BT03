# Yêu cầu chức năng bổ sung

## Tài khoản
- Người chơi có thể sửa username/email và đổi mật khẩu khi đang đăng nhập.
- Có thể yêu cầu đặt lại mật khẩu qua email. Token khôi phục chỉ dùng một lần và hết hạn sau 1 giờ.
- Có thể gửi lại và xác nhận email. Bật `EMAIL_VERIFICATION_REQUIRED=true` để yêu cầu xác minh trước khi đăng nhập.
- Tài khoản bị vô hiệu hóa không được đăng nhập hoặc gọi API cần xác thực.
- SMTP được cấu hình bằng `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`.
- `FRONTEND_BASE_URL` là URL gốc phục vụ thư mục frontend, mặc định `http://127.0.0.1:5500`.

## Hồ sơ và lịch sử
- Hồ sơ hiển thị lịch sử trận đã hoàn thành, kết quả, đối thủ, số lượt và replay.
- Lịch sử hỗ trợ lọc theo người chơi, kết quả, loại trận, trạng thái; API phân trang bằng `offset`/`limit`.
- Thống kê hồ sơ phân nhóm theo bot và giải đấu.

## Đội
- Người tạo đội là chủ đội và thành viên `OWNER`.
- Chủ đội/admin có thể thêm thành viên, loại thành viên và chuyển quyền chủ đội.
- Thành viên có thể tự rời đội; chủ đội phải chuyển quyền trước khi rời.

## Thông báo và báo cáo
- Thông báo được lưu theo tài khoản, có thể đánh dấu đã đọc từng mục hoặc toàn bộ.
- Giao diện đồng bộ số thông báo chưa đọc định kỳ.
- Người chơi đã đăng nhập có thể gửi báo cáo về người chơi hoặc trận đấu.

## Quản trị
- Chỉ tài khoản có `is_admin=true` được xem báo cáo, tìm tài khoản, khóa/mở khóa người chơi và theo dõi giải/trận.
- Tài khoản admin đầu tiên được cấp trực tiếp trong database, ví dụ: `UPDATE users SET is_admin = 1 WHERE username = 'admin';`.
- Các endpoint quản trị vẫn kiểm tra quyền ở backend; ẩn liên kết trên giao diện không được xem là cơ chế phân quyền.

## Kiểm thử nghiệm thu
- Match history trả đúng tổng số, phân trang, lọc người chơi/kết quả/loại trận.
- Thành viên ngoài đội không thể tự quản lý thành viên; người không phải chủ/admin không thể thêm hoặc xóa người khác.
- Người dùng chỉ đọc và đánh dấu được notification của chính mình.
- Người dùng thường bị từ chối ở API admin; admin có thể cập nhật trạng thái report và tài khoản.
- Token hết hạn/đã dùng không thể xác minh email hoặc đặt lại mật khẩu lần thứ hai.

## Chạy tải cao
- API chỉ enqueue trận trong production; worker riêng chạy job RQ và cập nhật trạng thái `QUEUED`, `PLAYING`, `COMPLETED` hoặc `FAILED`.
- Nếu Redis/database không khả dụng trong production, API fail fast; không được fallback SQLite hoặc chạy trận inline.
- Worker có thể scale ngang; mỗi worker phải dùng chung database, Redis và vùng lưu submissions.
- Dùng load test để xác nhận mục tiêu online, request/giây, số trận đồng thời và p95 latency; số process không được vượt ngân sách connection DB.
