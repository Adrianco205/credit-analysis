from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from app.db.session import SessionLocal
from app.models.user import Usuario
import logging

# Configuración básica de logs para ver la limpieza en la consola de Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_expired_pending_users():
    """
    Elimina usuarios en estado 'PENDING' que lleven más de 40 minutos sin activar.
    """
    db = SessionLocal()
    try:
        # Definimos el tiempo límite: ahora menos 40 minutos
        # Usamos timezone.utc porque tus modelos usan DateTime(timezone=True)
        threshold_time = datetime.now(timezone.utc) - timedelta(minutes=40)
        
        # Ejecutamos la eliminación
        # El ON DELETE CASCADE de la DB limpiará las tablas: 
        # usuario_roles, verificaciones_otp, etc.
        stmt = delete(Usuario).where(
            Usuario.status == "PENDING",
            Usuario.created_at <= threshold_time
        )
        
        result = db.execute(stmt)
        db.commit()
        
        if result.rowcount > 0:
            logger.info(f"🧹 [CLEANUP] Se eliminaron {result.rowcount} registros PENDING expirados (>40 min).")
            
    except Exception as e:
        logger.error(f"❌ [CLEANUP ERROR] Falló la limpieza automática: {e}")
        db.rollback()
    finally:
        db.close()