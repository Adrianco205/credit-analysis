from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"


settings = Settings()
