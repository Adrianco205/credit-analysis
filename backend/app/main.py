from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.api.v1.router import api_router
from app.services.cleanup_service import cleanup_expired_pending_users

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
    title="Credit Analysis API",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")