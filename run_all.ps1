# PowerShell launcher cho UET Algorithm Battle
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "     KHỞI ĐỘNG HỆ THỐNG UET ALGORITHM BATTLE" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot
Write-Host "Thư mục dự án: $PSScriptRoot"

# Lấy địa chỉ IP mạng nội bộ (LAN / Wi-Fi)
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*", "Ethernet*" -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress

Write-Host "`nĐang khởi động Backend API trên cổng 5000..." -ForegroundColor Yellow
Write-Host "  - Backend API:          http://127.0.0.1:5000/" -ForegroundColor Green
Write-Host "  - Giao diện Web (Live): http://127.0.0.1:5500/frontend/index.html" -ForegroundColor Cyan
if ($lanIp) {
    Write-Host "  - Máy khác cùng Wi-Fi:  http://${lanIp}:5500/frontend/index.html" -ForegroundColor Cyan
}
Write-Host "  - Tài liệu API Docs:    http://127.0.0.1:5000/docs" -ForegroundColor Green
Write-Host ""

Start-Process "http://127.0.0.1:5500/frontend/index.html"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 5000
