import uuid
from sqlalchemy import String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    nombres: Mapped[str | None] = mapped_column(String(150))
    primer_apellido: Mapped[str | None] = mapped_column(String(80))
    segundo_apellido: Mapped[str | None] = mapped_column(String(80))
    tipo_identificacion: Mapped[str | None] = mapped_column(String(10))
    identificacion: Mapped[str | None] = mapped_column(String(30), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(30))
    genero: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str | None] = mapped_column(String(255))

    ciudad_id: Mapped[int | None] = mapped_column(ForeignKey("ciudades.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), server_default=text("'PENDING'"))
    email_verificado: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
