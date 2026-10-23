import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.models.account_token import AccountToken
from backend.models.user import User


class AccountService:
    @staticmethod
    def send_token(db: Session, user: User, purpose: str) -> None:
        if not all((settings.SMTP_HOST, settings.SMTP_FROM)):
            raise HTTPException(status_code=503, detail="Chưa cấu hình dịch vụ gửi email")

        raw_token = secrets.token_urlsafe(32)
        token = AccountToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.query(AccountToken).filter(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.used_at.is_(None),
        ).update({AccountToken.used_at: datetime.utcnow()}, synchronize_session=False)
        db.add(token)
        db.commit()

        action = "verify-email" if purpose == "VERIFY_EMAIL" else "reset-password"
        url = f"{settings.FRONTEND_BASE_URL}/login.html?{action}={raw_token}"
        subject = "Xác minh email" if purpose == "VERIFY_EMAIL" else "Đặt lại mật khẩu"
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM
        message["To"] = user.email
        message.set_content(f"Mở liên kết sau trong vòng 1 giờ để hoàn tất thao tác:\n{url}")

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
        except Exception as exc:
            db.delete(token)
            db.commit()
            raise HTTPException(status_code=503, detail="Không thể gửi email lúc này") from exc

    @staticmethod
    def consume_token(db: Session, raw_token: str, purpose: str) -> AccountToken:
        digest = hashlib.sha256(raw_token.encode()).hexdigest()
        token = db.query(AccountToken).filter(
            AccountToken.token_hash == digest,
            AccountToken.purpose == purpose,
            AccountToken.used_at.is_(None),
            AccountToken.expires_at > datetime.utcnow(),
        ).first()
        if not token:
            raise HTTPException(status_code=400, detail="Liên kết không hợp lệ hoặc đã hết hạn")
        token.used_at = datetime.utcnow()
        return token