from pydantic import BaseModel, EmailStr, Field, model_validator


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

    ciudad_departamento: str | None = None


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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=8, max_length=72)
    confirm_password: str = Field(min_length=8, max_length=72)

    @model_validator(mode="after")
    def validate_password_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class ResetPasswordResponse(BaseModel):
    message: str
