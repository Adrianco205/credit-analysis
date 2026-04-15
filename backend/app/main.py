from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import IntegrityError, OperationalError, DataError

from app.api.v1.router import api_router
from app.services.cleanup_service import cleanup_expired_pending_users
from app.core.exceptions import (
    integrity_error_handler,
    operational_error_handler,
    data_error_handler,
    validation_error_handler,
    generic_exception_handler
)


from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Al iniciar la aplicación ---
    scheduler = BackgroundScheduler()
    # Programamos para que revise la DB cada 10 minutos (puedes ajustar este intervalo)
    scheduler.add_job(cleanup_expired_pending_users, 'interval', minutes=10)
    scheduler.start()
    
    yield # Aquí la app funciona normalmente
    
    # --- Al apagar la aplicación ---
    scheduler.shutdown()


app = FastAPI(
    title="PerFinanzas Credit Analysis API",
    description="API para análisis de créditos hipotecarios con IA",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS restrictivo para producción basado en variables de entorno.
# Solo habilita localhost cuando el frontend configurado también es local.
origins = [settings.FRONTEND_BASE_URL]

if "localhost" in settings.FRONTEND_BASE_URL or "127.0.0.1" in settings.FRONTEND_BASE_URL:
    origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar exception handlers globales
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(OperationalError, operational_error_handler)
app.add_exception_handler(DataError, data_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Registrar routers
app.include_router(api_router, prefix="/api/v1")
