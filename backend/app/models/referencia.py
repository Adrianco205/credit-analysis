"""
Modelo de Referencias Personales del Usuario.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TipoReferencia(str, Enum):
    """Tipos de referencia del usuario."""
    FAMILIAR = "FAMILIAR"
    PERSONAL = "PERSONAL"


class ReferenciaUsuario(Base):
    """
    Modelo para almacenar referencias personales/familiares del usuario.
    Cada usuario puede tener múltiples referencias.
    """

    __tablename__ = "referencias_usuario"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))

    # Tipo de referencia
    tipo_referencia: Mapped[str] = mapped_column(String(20))

    # Datos de la referencia
    nombre_completo: Mapped[str] = mapped_column(String(200))
    celular: Mapped[str] = mapped_column(String(20))
    parentesco: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relación con usuario
    usuario = relationship("Usuario", back_populates="referencias")

    def __repr__(self) -> str:
        return f"<ReferenciaUsuario {self.tipo_referencia}: {self.nombre_completo}>"
