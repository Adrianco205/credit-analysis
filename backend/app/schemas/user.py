from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==========================================
# PERFIL DE USUARIO
# ==========================================

class UserProfileResponse(BaseModel):
    """Schema para la respuesta del perfil de usuario - versión completa para dashboard."""
    id: str
    identificacion: str
    tipo_identificacion: str | None
    nombres: str
    primer_apellido: str
    segundo_apellido: str | None
    genero: str | None
    email: str
    telefono: str | None
    status: str
    email_verificado: bool
    # Ciudad
    ciudad_id: int | None
    ciudad_nombre: str | None
    departamento_nombre: str | None
    # Rol del usuario
    rol: str | None


class UpdatePasswordRequest(BaseModel):
    """Schema para actualizar contraseña."""
    current_password: str = Field(min_length=1, description="Contraseña actual")
    new_password: str = Field(min_length=8, max_length=72, description="Nueva contraseña")


class UpdateProfileRequest(BaseModel):
    """Schema para actualizar datos del perfil (teléfono y ciudad)."""
    telefono: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
        pattern=r"^\+?[\d\s-]{7,20}$",
        description="Número de teléfono"
    )
    ciudad_id: int | None = Field(
        default=None,
        description="ID de la ciudad"
    )


# ==========================================
# REFERENCIAS DEL USUARIO
# ==========================================

class ReferenciaBase(BaseModel):
    """Schema base para referencias."""
    nombre_completo: str = Field(
        min_length=3,
        max_length=200,
        description="Nombre completo de la referencia"
    )
    celular: str = Field(
        min_length=7,
        max_length=20,
        pattern=r"^\+?[\d\s-]{7,20}$",
        description="Número de celular de la referencia"
    )
    parentesco: str | None = Field(
        default=None,
        max_length=50,
        description="Parentesco (solo para referencias familiares)"
    )


class ReferenciaCreate(ReferenciaBase):
    """Schema para crear una referencia."""
    tipo_referencia: Literal["FAMILIAR", "PERSONAL"] = Field(
        description="Tipo de referencia: FAMILIAR o PERSONAL"
    )


class ReferenciaUpdate(BaseModel):
    """Schema para actualizar una referencia."""
    nombre_completo: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Nombre completo de la referencia"
    )
    celular: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
        pattern=r"^\+?[\d\s-]{7,20}$",
        description="Número de celular de la referencia"
    )
    parentesco: str | None = Field(
        default=None,
        max_length=50,
        description="Parentesco (solo para referencias familiares)"
    )


class ReferenciaResponse(BaseModel):
    """Schema para respuesta de una referencia."""
    id: str
    tipo_referencia: str
    nombre_completo: str
    celular: str
    parentesco: str | None
    created_at: datetime


class ReferenciasListResponse(BaseModel):
    """Schema para listar referencias del usuario."""
    familiar: ReferenciaResponse | None = None
    personal: ReferenciaResponse | None = None


# ==========================================
# HISTORIAL DE ESTUDIOS/ANÁLISIS
# ==========================================

class EstudioHistorialItem(BaseModel):
    """Schema para un item del historial de estudios."""
    analisis_id: str
    documento_id: str | None
    banco_nombre: str | None
    fecha_subida: datetime | None
    status: str
    # Información adicional útil
    saldo_actual: float | None
    numero_credito: str | None


class EstudiosHistorialResponse(BaseModel):
    """Schema para respuesta del historial de estudios con paginación."""
    total: int
    page: int
    limit: int
    total_pages: int
    estudios: list[EstudioHistorialItem]

