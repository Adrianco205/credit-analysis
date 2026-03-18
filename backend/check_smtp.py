import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

def test_email():
    print(f"--- Probando conexión SMTP ---")
    print(f"Host: {SMTP_HOST}:{SMTP_PORT}")
    print(f"Usuario: {SMTP_USER}")
    
    if not SMTP_USER or not SMTP_PASSWORD:
        print("❌ Error: Faltan credenciales SMTP_USER o SMTP_PASSWORD en .env")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM_EMAIL
        msg["To"] = SMTP_USER  # Enviarse a sí mismo para probar
        msg["Subject"] = "Prueba de Configuración SMTP PerFinanzas"
        msg.attach(MIMEText("Si recibes esto, la configuración SMTP funciona correctamente.", "plain"))

        print(f"Intentando conectar a {SMTP_HOST}...")
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.set_debuglevel(1)  # Ver log detallado de la conversación SMTP
            server.starttls()
            print("✅ TLS iniciado.")
            
            print("Autenticando...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("✅ Autenticación exitosa.")
            
            print("Enviando correo...")
            server.send_message(msg)
            print("✅ Correo enviado exitosamente.")
            
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de Autenticación: Verifica tu usuario y contraseña (o App Password).")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_email()

