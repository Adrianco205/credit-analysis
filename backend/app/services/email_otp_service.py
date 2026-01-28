import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailOtpService:
    """
    Servicio para envío de códigos OTP por email.
    Diseñado para ser ejecutado en BackgroundTasks de FastAPI.
    """
    
    @staticmethod
    def send_otp(to_email: str, code: str) -> bool:
        """
        Envía un código OTP por correo electrónico.
        
        Args:
            to_email: Dirección de correo destino
            code: Código OTP a enviar
            
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            # 1. Crear el contenedor del mensaje
            msg = MIMEMultipart()
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            msg["Subject"] = f"Código de Verificación - {settings.APP_PUBLIC_NAME}"

            # 2. Cuerpo del mensaje con formato profesional
            body = f"""
Hola,

Tu código de verificación para activar tu cuenta de {settings.APP_PUBLIC_NAME} es:

    {code}

Este código expirará en {settings.OTP_EXPIRE_MINUTES} minutos.
Si no solicitaste este registro, puedes ignorar este correo.

---
Equipo de {settings.APP_PUBLIC_NAME}
            """
            msg.attach(MIMEText(body, "plain"))

            # 3. Conexión al servidor SMTP
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.set_debuglevel(0)
                server.starttls()  # Inicia cifrado TLS
                
                # 4. Autenticación
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                
                # 5. Envío
                server.send_message(msg)
                
            logger.info(f"✅ Email OTP enviado exitosamente a {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Error de autenticación SMTP: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Error SMTP al enviar email a {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado al enviar email a {to_email}: {str(e)}")
            return False
