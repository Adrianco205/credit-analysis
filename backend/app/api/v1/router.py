from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.locations import router as locations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.admin import router as admin_router
from app.api.v1.indicadores import router as indicadores_router
from app.api.v1.test_gemini import router as test_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(locations_router, prefix="/locations", tags=["locations"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(analyses_router, tags=["analyses"])
api_router.include_router(admin_router, tags=["admin"])
api_router.include_router(indicadores_router, tags=["indicadores"])
api_router.include_router(test_router, tags=["test"])

