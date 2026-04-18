from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OTP_EXPIRE_MINUTES: int = 10
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_NAME: str = "PerFinanzas"
    SMTP_FROM_EMAIL: str

    APP_PUBLIC_NAME: str = "PerFinanzas"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    
    # ---------------------------------------------------------------------------
    # INDICADORES FINANCIEROS
    # ---------------------------------------------------------------------------
    
    # Banco de la Rep�blica (opcional - para API autenticada)
    BANREP_API_KEY: Optional[str] = None
    
    # Google Gemini (para extracci�n de PDFs)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # Feature flags
    ENABLE_TEST_ENDPOINTS: bool = False
    UVR_ENGINE_V2_ENABLED: bool = False
    UVR_INFLACION_ANUAL_ESTIMADA_DEFAULT: float = 0.06
    
    # Google Cloud Storage (para almacenamiento de documentos)
    GCS_BUCKET_NAME: str = "perfinanzas-documentos"
    
    # ---------------------------------------------------------------------------
    # CONFIGURACI�N DE NEGOCIO
    # ---------------------------------------------------------------------------
    
    # Honorarios
    PORCENTAJE_HONORARIOS: float = 0.05  # 5% del saldo del crédito
    TARIFA_MINIMA_HONORARIOS: float = 500000  # $500,000 COP
    PORCENTAJE_IVA: float = 0.19  # 19% IVA Colombia
    
    # Ley 546/99 - Capacidad de pago
    PORCENTAJE_INGRESO_MINIMO: float = 0.30  # Cuota m�xima 30% del ingreso
    
    # Cache de indicadores
    INDICADORES_CACHE_TTL_HORAS: int = 12

    # Credenciales de Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GOOGLE_CLOUD_PROJECT: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()


