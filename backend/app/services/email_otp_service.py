import smtplib
from email.mime.text import MIMEText
from app.core.config import settings


class EmailOtpService:
    def send_otp(self, to_email: str, code: str):
        subject = f"{settings.APP_PUBLIC_NAME} - Código de verificación"
        body = f"Tu código OTP es: {code}\n\nVence en {settings.OTP_EXPIRE_MINUTES} minutos."

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
