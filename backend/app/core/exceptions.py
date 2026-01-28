"""
Exception handlers y middleware para manejo global de errores.
Captura errores de base de datos, validación y excepciones no controladas.
"""
import logging
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Estructura estandarizada para respuestas de error"""
    
    @staticmethod
    def format(
        error_type: str,
        message: str,
        detail: Union[str, dict, list, None] = None,
        status_code: int = 500
    ) -> dict:
        """
        Crea una respuesta de error estandarizada.
        
        Args:
            error_type: Tipo de error (validation, database, server, etc.)
            message: Mensaje principal del error
            detail: Detalles adicionales opcionales
            status_code: Código HTTP del error
            
        Returns:
            Dict con estructura de error estandarizada
        """
        response = {
            "error": error_type,
            "message": message,
            "status_code": status_code
        }
        
        if detail:
            response["detail"] = detail
        
        return response


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Maneja errores de integridad de base de datos (constraints, duplicados).
    
    Args:
        request: Request de FastAPI
        exc: Excepción de IntegrityError
        
    Returns:
        JSONResponse con error formateado
    """
    logger.warning(f"IntegrityError en {request.url.path}: {str(exc.orig)}")
    
    error_msg = str(exc.orig).lower()
    
    # Detectar tipo de violación de constraint
    if "unique" in error_msg or "duplicate" in error_msg:
        if "email" in error_msg:
            message = "El correo electrónico ya está registrado"
        elif "identificacion" in error_msg:
            message = "El número de identificación ya está registrado"
        else:
            message = "El valor ingresado ya existe en el sistema"
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse.format(
                error_type="duplicate_entry",
                message=message,
                status_code=status.HTTP_409_CONFLICT
            )
        )
    
    elif "foreign key" in error_msg:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse.format(
                error_type="invalid_reference",
                message="Referencia a registro inexistente",
                detail="Uno de los valores proporcionados no existe en el sistema",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        )
    
    elif "not null" in error_msg:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse.format(
                error_type="missing_required_field",
                message="Falta un campo obligatorio",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        )
    
    # Error genérico de integridad
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse.format(
            error_type="database_integrity_error",
            message="Error de validación en la base de datos",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    )


async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """
    Maneja errores operacionales de base de datos (conexión, timeout, etc.).
    
    Args:
        request: Request de FastAPI
        exc: Excepción de OperationalError
        
    Returns:
        JSONResponse con error formateado
    """
    logger.error(f"OperationalError en {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse.format(
            error_type="database_unavailable",
            message="Error de conexión con la base de datos. Intenta nuevamente en unos momentos.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    )


async def data_error_handler(request: Request, exc: DataError) -> JSONResponse:
    """
    Maneja errores de datos inválidos en base de datos.
    
    Args:
        request: Request de FastAPI
        exc: Excepción de DataError
        
    Returns:
        JSONResponse con error formateado
    """
    logger.warning(f"DataError en {request.url.path}: {str(exc.orig)}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse.format(
            error_type="invalid_data_format",
            message="Formato de datos inválido",
            detail="Uno o más campos tienen un formato incorrecto",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Maneja errores de validación de Pydantic.
    
    Args:
        request: Request de FastAPI
        exc: Excepción de RequestValidationError
        
    Returns:
        JSONResponse con errores de validación formateados
    """
    logger.info(f"ValidationError en {request.url.path}: {exc.errors()}")
    
    # Formatear errores de validación de forma más amigable
    formatted_errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"][1:])  # Omitir 'body'
        formatted_errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse.format(
            error_type="validation_error",
            message="Error de validación en los datos enviados",
            detail=formatted_errors,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Maneja excepciones no controladas.
    
    Args:
        request: Request de FastAPI
        exc: Excepción genérica
        
    Returns:
        JSONResponse con error genérico
    """
    logger.error(f"Unhandled exception en {request.url.path}: {type(exc).__name__} - {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse.format(
            error_type="internal_server_error",
            message="Error interno del servidor",
            detail="Ha ocurrido un error inesperado. El equipo técnico ha sido notificado.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    )
