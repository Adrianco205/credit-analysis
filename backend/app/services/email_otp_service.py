import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailOtpService:
    """
    Servicio para envío de emails de autenticación.
    Diseñado para ejecutarse en BackgroundTasks de FastAPI.
    """

    @staticmethod
    def send_otp(to_email: str, code: str) -> bool:
        subject = f"Código de verificación - {settings.APP_PUBLIC_NAME}"
        text_body = f"""
Hola,

Tu código de verificación para activar tu cuenta en {settings.APP_PUBLIC_NAME} es:

{code}

Este código expirará en {settings.OTP_EXPIRE_MINUTES} minutos.
Si no solicitaste este registro, puedes ignorar este correo.

Equipo de {settings.APP_PUBLIC_NAME}
        """.strip()

        html_body = f"""
<!doctype html>
<html lang="es">
  <body style="margin:0;padding:0;background:#f3f7f4;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f7f4;padding:24px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e5e7eb;">
            <tr>
              <td style="background:#1f6f43;padding:22px 24px;color:#ffffff;">
                <h1 style="margin:0;font-size:22px;line-height:1.2;">PerFinanzas</h1>
                <p style="margin:6px 0 0;font-size:14px;opacity:0.95;">Verificación de cuenta</p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <p style="margin:0 0 14px;font-size:15px;">Hola,</p>
                <p style="margin:0 0 18px;font-size:15px;line-height:1.5;">Tu código para activar tu cuenta es:</p>
                <div style="margin:0 0 18px;padding:14px 18px;border:1px dashed #9ca3af;border-radius:10px;background:#f9fafb;text-align:center;">
                  <span style="font-size:34px;letter-spacing:6px;font-weight:700;color:#14532d;">{code}</span>
                </div>
                <p style="margin:0 0 10px;font-size:14px;color:#374151;">Este código expira en <strong>{settings.OTP_EXPIRE_MINUTES} minutos</strong>.</p>
                <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.45;">Si no solicitaste este registro, puedes ignorar este correo.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 24px;background:#f9fafb;border-top:1px solid #e5e7eb;">
                <p style="margin:0;font-size:12px;color:#6b7280;">© PerFinanzas. Todos los derechos reservados.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
        """.strip()

        return EmailOtpService._send_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            context_name="OTP",
        )

    @staticmethod
    def send_password_reset_link(to_email: str, reset_link: str) -> bool:
        subject = f"Recuperación de contraseña - {settings.APP_PUBLIC_NAME}"
        text_body = f"""
Hola,

Recibimos una solicitud para restablecer tu contraseña en {settings.APP_PUBLIC_NAME}.

Usa este enlace para crear una nueva contraseña:
{reset_link}

Este enlace expirará en {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos y solo puede usarse una vez.
Si no solicitaste este cambio, puedes ignorar este correo.

Equipo de {settings.APP_PUBLIC_NAME}
        """.strip()

        html_body = f"""
<!doctype html>
<html lang="es">
  <body style="margin:0;padding:0;background:#f3f7f4;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f7f4;padding:24px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e5e7eb;">
            <tr>
              <td style="background:#1f6f43;padding:22px 24px;color:#ffffff;">
                <h1 style="margin:0;font-size:22px;line-height:1.2;">PerFinanzas</h1>
                <p style="margin:6px 0 0;font-size:14px;opacity:0.95;">Recuperación de contraseña</p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <p style="margin:0 0 14px;font-size:15px;">Hola,</p>
                <p style="margin:0 0 18px;font-size:15px;line-height:1.5;">Recibimos una solicitud para restablecer tu contraseña. Para continuar, haz clic en el siguiente botón:</p>
                <p style="margin:0 0 18px;text-align:center;">
                  <a href="{reset_link}" style="display:inline-block;padding:12px 18px;background:#1f6f43;color:#ffffff;text-decoration:none;border-radius:10px;font-weight:600;">
                    Restablecer contraseña
                  </a>
                </p>
                <p style="margin:0 0 16px;font-size:13px;color:#374151;line-height:1.45;">
                  Si tienes problemas con el botón, usa este
                  <a href="{reset_link}" style="color:#2563eb;text-decoration:underline;">enlace de recuperación</a>.
                </p>
                <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.45;">Este enlace expira en <strong>{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos</strong> y solo puede usarse una vez. Si no solicitaste este cambio, ignora este mensaje.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 24px;background:#f9fafb;border-top:1px solid #e5e7eb;">
                <p style="margin:0;font-size:12px;color:#6b7280;">© PerFinanzas. Todos los derechos reservados.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
        """.strip()

        return EmailOtpService._send_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            context_name="recuperación",
        )

    @staticmethod
    def _send_email(
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
        context_name: str,
    ) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.set_debuglevel(0)
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"✅ Email de {context_name} enviado exitosamente a {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Error de autenticación SMTP: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Error SMTP al enviar email de {context_name} a {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado al enviar email de {context_name} a {to_email}: {str(e)}")
            return False


