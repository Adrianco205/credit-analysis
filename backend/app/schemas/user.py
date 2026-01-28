from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """Schema para la respuesta del perfil de usuario"""
    id: str
    identificacion: str
    nombres: str
    primer_apellido: str
    segundo_apellido: str | None
    genero: str | None
    email: str
    telefono: str | None
    status: str
    email_verificado: bool


class UpdatePasswordRequest(BaseModel):
    """Schema para actualizar contraseña"""
    current_password: str = Field(min_length=1, description="Contraseña actual")
    new_password: str = Field(min_length=8, max_length=72, description="Nueva contraseña")
