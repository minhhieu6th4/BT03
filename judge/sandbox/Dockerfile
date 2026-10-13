# Sử dụng image python siêu nhẹ
FROM python:3.11-slim

# Tạo user không có đặc quyền để tăng tính bảo mật
RUN useradd -m -s /bin/bash sandboxuser

# Giới hạn quyền ghi
WORKDIR /sandbox

# Command mặc định sẽ bị ghi đè lúc docker run
CMD ["python", "/runner.py"]
