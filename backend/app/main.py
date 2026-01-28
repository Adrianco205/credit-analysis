from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
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
    title="EcoFinanzas Credit Analysis API",
    description="API para análisis de créditos hipotecarios con IA",
    version="1.0.0",
    lifespan=lifespan
)

# Registrar exception handlers globales
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(OperationalError, operational_error_handler)
app.add_exception_handler(DataError, data_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Registrar routers
app.include_router(api_router, prefix="/api/v1")