import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class EmailOtpService:
    def send_otp(self, to_email: str, code: str):
        # 1. Crear el contenedor del mensaje
        msg = MIMEMultipart()
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = f"Código de Verificación - {settings.APP_PUBLIC_NAME}"

        # 2. Cuerpo del mensaje (puedes usar HTML para que se vea más profesional)
        body = f"""
        Hola,
        
        Tu código de verificación para activar tu cuenta de análisis de crédito es:
        
        {code}
        
        Este código expirará en {settings.OTP_EXPIRE_MINUTES} minutos.
        Si no solicitaste este registro, puedes ignorar este correo.
        """
        msg.attach(MIMEText(body, "plain"))

        try:
            # 3. Conexión al servidor SMTP de Gmail
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.set_debuglevel(0) # Cambia a 1 si necesitas ver el log técnico
                server.starttls() # Inicia cifrado TLS obligatorio para puerto 587
                
                # 4. Autenticación
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                
                # 5. Envío
                server.send_message(msg)
                
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Error: Autenticación fallida. Verifica tu App Password.")
            raise Exception("Credenciales de correo inválidas.")
        except Exception as e:
            print(f"❌ Error al enviar email: {str(e)}")
            raise e