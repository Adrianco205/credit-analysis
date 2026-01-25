from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    nombres: str = Field(min_length=1, max_length=150)
    primer_apellido: str = Field(min_length=1, max_length=80)
    segundo_apellido: str | None = Field(default=None, max_length=80)

    tipo_identificacion: str = Field(min_length=1, max_length=10)
    identificacion: str = Field(min_length=3, max_length=30)

    email: EmailStr
    telefono: str | None = Field(default=None, max_length=30)
    genero: str | None = Field(default=None, max_length=20)

    password: str = Field(min_length=8, max_length=72)

    ciudad_id: int | None = None


class RegisterResponse(BaseModel):
    user_id: str
    status: str
    message: str


class VerifyOtpRequest(BaseModel):
    user_id: str
    code: str = Field(min_length=4, max_length=12)


class LoginRequest(BaseModel):
    identificacion: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
