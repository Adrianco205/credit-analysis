"""
Repositorio para operaciones de Referencias del Usuario.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.referencia import ReferenciaUsuario, TipoReferencia


class ReferenciasRepo:
    """Repositorio para gestión de referencias personales y familiares del usuario."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, referencia_id: UUID) -> Optional[ReferenciaUsuario]:
        """Obtiene una referencia por su ID."""
        stmt = select(ReferenciaUsuario).where(ReferenciaUsuario.id == referencia_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_usuario(self, usuario_id: UUID) -> list[ReferenciaUsuario]:
        """Obtiene todas las referencias de un usuario."""
        stmt = select(ReferenciaUsuario).where(
            ReferenciaUsuario.usuario_id == usuario_id
        ).order_by(ReferenciaUsuario.tipo_referencia)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_usuario_y_tipo(
        self, usuario_id: UUID, tipo: str
    ) -> Optional[ReferenciaUsuario]:
        """Obtiene la referencia de un usuario por tipo (FAMILIAR o PERSONAL)."""
        stmt = select(ReferenciaUsuario).where(
            ReferenciaUsuario.usuario_id == usuario_id,
            ReferenciaUsuario.tipo_referencia == tipo
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        usuario_id: UUID,
        tipo_referencia: str,
        nombre_completo: str,
        celular: str,
        parentesco: Optional[str] = None
    ) -> ReferenciaUsuario:
        """Crea una nueva referencia para el usuario."""
        referencia = ReferenciaUsuario(
            usuario_id=usuario_id,
            tipo_referencia=tipo_referencia,
            nombre_completo=nombre_completo,
            celular=celular,
            parentesco=parentesco
        )
        self.db.add(referencia)
        self.db.commit()
        self.db.refresh(referencia)
        return referencia

    def update(
        self,
        referencia: ReferenciaUsuario,
        nombre_completo: Optional[str] = None,
        celular: Optional[str] = None,
        parentesco: Optional[str] = None
    ) -> ReferenciaUsuario:
        """Actualiza una referencia existente."""
        if nombre_completo is not None:
            referencia.nombre_completo = nombre_completo
        if celular is not None:
            referencia.celular = celular
        if parentesco is not None:
            referencia.parentesco = parentesco
        
        referencia.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(referencia)
        return referencia

    def delete(self, referencia_id: UUID) -> bool:
        """Elimina una referencia por su ID."""
        stmt = delete(ReferenciaUsuario).where(ReferenciaUsuario.id == referencia_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def delete_by_usuario_y_tipo(self, usuario_id: UUID, tipo: str) -> bool:
        """Elimina la referencia de un usuario por tipo."""
        stmt = delete(ReferenciaUsuario).where(
            ReferenciaUsuario.usuario_id == usuario_id,
            ReferenciaUsuario.tipo_referencia == tipo
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0
