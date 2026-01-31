from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OTP_EXPIRE_MINUTES: int = 10

    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_NAME: str = "Credit Analysis"
    SMTP_FROM_EMAIL: str

    APP_PUBLIC_NAME: str = "Credit Analysis"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INDICADORES FINANCIEROS
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Banco de la República (opcional - para API autenticada)
    BANREP_API_KEY: Optional[str] = None
    
    # Google Gemini (para extracción de PDFs)
    GEMINI_API_KEY: Optional[str] = None
    
    # AWS S3 (para almacenamiento de documentos)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "ecofinanzas-documents"
    AWS_REGION: str = "us-east-1"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Honorarios
    PORCENTAJE_HONORARIOS: float = 0.03  # 3% del ahorro
    TARIFA_MINIMA_HONORARIOS: float = 500000  # $500,000 COP
    PORCENTAJE_IVA: float = 0.19  # 19% IVA Colombia
    
    # Ley 546/99 - Capacidad de pago
    PORCENTAJE_INGRESO_MINIMO: float = 0.30  # Cuota máxima 30% del ingreso
    
    # Cache de indicadores
    INDICADORES_CACHE_TTL_HORAS: int = 12

    class Config:
        env_file = ".env"


settings = Settings()
