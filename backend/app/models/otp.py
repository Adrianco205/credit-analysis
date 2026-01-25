import uuid
from sqlalchemy import String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class VerificacionOTP(Base):
    __tablename__ = "verificaciones_otp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)

    code_hash: Mapped[str | None] = mapped_column(String(255))
    tipo: Mapped[str | None] = mapped_column(String(20))  # EMAIL
    status: Mapped[str] = mapped_column(String(20), server_default=text("'PENDING'"))  # PENDING/VERIFIED/EXPIRED

    expires_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
