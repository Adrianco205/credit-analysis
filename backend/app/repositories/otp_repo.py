from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.otp import VerificacionOTP


class OtpRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, otp: VerificacionOTP) -> VerificacionOTP:
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def get_pending(self, user_id, tipo: str) -> VerificacionOTP | None:
        return self.db.execute(
            select(VerificacionOTP)
            .where(
                VerificacionOTP.user_id == user_id,
                VerificacionOTP.tipo == tipo,
                VerificacionOTP.status == "PENDING",
            )
            .order_by(VerificacionOTP.expires_at.desc())  # Obtener el más reciente
        ).scalars().first()  # Devuelve el primero o None (no lanza error si hay múltiples)

    def save(self, otp: VerificacionOTP):
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)

    def get_by_id(self, otp_id) -> VerificacionOTP | None:
        return self.db.execute(
            select(VerificacionOTP).where(VerificacionOTP.id == otp_id)
        ).scalar_one_or_none()

    def expire_pending(self, user_id, tipo: str) -> int:
        pendings = self.db.execute(
            select(VerificacionOTP).where(
                VerificacionOTP.user_id == user_id,
                VerificacionOTP.tipo == tipo,
                VerificacionOTP.status == "PENDING",
            )
        ).scalars().all()

        for otp in pendings:
            otp.status = "EXPIRED"
            self.db.add(otp)

        self.db.commit()
        return len(pendings)
