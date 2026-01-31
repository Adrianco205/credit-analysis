"""
Endpoint de prueba para verificar conexión con Gemini.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai

from app.core.config import settings

router = APIRouter(prefix="/test", tags=["test"])


class GeminiTestRequest(BaseModel):
    mensaje: str = "Hola"


class GeminiTestResponse(BaseModel):
    mensaje_enviado: str
    respuesta: str
    modelo: str


@router.post("/gemini", response_model=GeminiTestResponse)
async def test_gemini(request: GeminiTestRequest = GeminiTestRequest()):
    """
    Endpoint de prueba para verificar que Gemini funciona.
    
    Envía un mensaje simple y retorna la respuesta.
    """
    try:
        # Crear cliente con API key
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Generar respuesta
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=request.mensaje
        )
        
        return GeminiTestResponse(
            mensaje_enviado=request.mensaje,
            respuesta=response.text,
            modelo="gemini-2.5-flash"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error con Gemini: {str(e)}"
        )


@router.get("/gemini/hola")
async def test_gemini_simple():
    """
    Endpoint GET simple: envía "Hola" a Gemini.
    """
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hola, responde brevemente en español"
        )
        
        return {
            "status": "ok",
            "mensaje": "Hola",
            "respuesta": response.text,
            "modelo": "gemini-2.5-flash"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
