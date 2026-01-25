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
            .order_by(VerificacionOTP.expires_at.desc())
        ).scalar_one_or_none()

    def save(self, otp: VerificacionOTP):
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
