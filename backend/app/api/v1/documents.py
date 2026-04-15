"""
Documents API - Endpoints para subida y gestión de PDFs
========================================================

Endpoints:
- POST /upload - Subir PDF (con detección de contraseña)
- POST /decrypt - Desencriptar PDF con contraseña (No implementado - flujo redirigido a upload)
- POST /extract - Extraer datos de un PDF recién subido en un solo paso
- GET / - Listar documentos del usuario
- GET /{id} - Obtener detalle de un documento
- DELETE /{id} - Eliminar un documento
- GET /{id}/download - Generar URL firmada para descarga (Google Cloud Storage)
- POST /{id}/extract - Extraer datos de un documento existente con Gemini
- POST /{id}/compare-name - Comparar nombre extraído con uno esperado
"""

import io
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import Usuario
from app.repositories.documents_repo import DocumentsRepo
from app.schemas.documentos import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentStatus,
    DocumentUploadResponse,
    PDFPasswordInput,
    PDFUploadStatus,
    PDFValidationResponse,
)
from app.services.pdf_service import (
    GCSService,
    PDFStatus,
    PdfService,
    get_storage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE UPLOAD Y GESTIÓN INICIAL
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="Archivo PDF del extracto bancario"),
    password: Optional[str] = Form(None, description="Contraseña del PDF (si está protegido)"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sube un archivo PDF de extracto bancario.
    
    ## Flujo:
    1. Valida que el archivo sea un PDF válido
    2. Si está encriptado y no se proporciona contraseña, retorna `requires_password=true`
    3. Si se proporciona contraseña, desencripta y guarda sin contraseña
    4. Si no está encriptado, guarda directamente
    """
    if file.content_type and file.content_type not in ["application/pdf", "application/octet-stream"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo debe ser un PDF. Tipo recibido: {file.content_type}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")

    pdf_service = PdfService()
    storage_service = get_storage_service()
    documents_repo = DocumentsRepo(db)

    # Paso 1: Validar el PDF
    file_stream = io.BytesIO(content)
    validation_result = pdf_service.validate_pdf(file_stream, check_keywords=True)

    validation_response = PDFValidationResponse(
        is_valid=validation_result.is_valid,
        status=PDFUploadStatus(validation_result.status.value),
        message=validation_result.message,
        requires_password=validation_result.status == PDFStatus.ENCRYPTED,
        page_count=validation_result.page_count,
        file_size_bytes=validation_result.file_size_bytes,
        has_credit_keywords=validation_result.has_credit_keywords,
        keyword_confidence=validation_result.keyword_confidence
    )

    if validation_result.status == PDFStatus.ENCRYPTED and not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "PDF_PASSWORD_REQUIRED",
                "message": "El PDF está protegido con contraseña. Por favor proporciona la contraseña.",
                "requires_password": True
            }
        )

    if not validation_result.is_valid and validation_result.status != PDFStatus.ENCRYPTED:
        return DocumentUploadResponse(
            success=False,
            message=validation_result.message,
            validation=validation_response
        )

    # Paso 2: Desencriptar si es necesario
    content_to_save = content
    was_encrypted = False

    if validation_result.status == PDFStatus.ENCRYPTED and password:
        file_stream.seek(0)
        decrypt_result = pdf_service.decrypt_pdf(file_stream, password)
        
        if not decrypt_result.success:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "PDF_INVALID_PASSWORD",
                    "message": decrypt_result.message,
                    "requires_password": True
                }
            )
        
        content_to_save = decrypt_result.decrypted_content
        was_encrypted = True
        validation_response.status = PDFUploadStatus.DECRYPTED
        validation_response.message = "PDF desencriptado y guardado sin contraseña"
        validation_response.page_count = decrypt_result.page_count
        validation_response.requires_password = False

    # Paso 3: Verificar duplicados del mes (por checksum)
    checksum = hashlib.sha256(content_to_save).hexdigest()
    
    existing_doc = documents_repo.get_by_checksum_and_user_in_current_month(
        checksum, current_user.id, reference_datetime=datetime.now(timezone.utc)
    )
    if existing_doc:
        return DocumentUploadResponse(
            success=False,
            message="Este documento ya lo ha subido anteriormente. Puede ver el resumen de su análisis en la sección de 'Historial de análisis'.",
            document_id=existing_doc.id,
            validation=PDFValidationResponse(
                is_valid=True, status=PDFUploadStatus.OK, 
                message="Podrá volver a subir este documento el próximo mes, una vez que se reflejen nuevos movimientos en su extracto.",
                requires_password=False
            )
        )

    # Paso 4: Guardar archivo
    save_result = storage_service.save_pdf(
        content=content_to_save,
        user_id=str(current_user.id),
        original_filename=file.filename or "extracto.pdf"
    )

    if not save_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo: {save_result.message}"
        )

    # Paso 5: Crear registro en BD
    documento = documents_repo.create(
        usuario_id=current_user.id,
        original_filename=file.filename or "extracto.pdf",
        file_size=save_result.file_size_bytes,
        s3_key=save_result.file_path,
        checksum=save_result.checksum,
        pdf_encrypted=was_encrypted,
        status="UPLOADED"
    )

    logger.info(f"Documento subido: {documento.id} por usuario {current_user.id}")

    return DocumentUploadResponse(
        success=True,
        message="PDF subido exitosamente" + (" (desencriptado)" if was_encrypted else ""),
        document_id=documento.id,
        file_path=save_result.file_path,
        checksum=save_result.checksum,
        validation=validation_response
    )


@router.post("/decrypt", response_model=DocumentUploadResponse)
async def decrypt_pdf_with_password(
    data: PDFPasswordInput,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Desencripta un PDF previamente subido usando la contraseña proporcionada.
    Nota: En la implementación actual, el archivo original debe volver a subirse.
    """
    documents_repo = DocumentsRepo(db)
    documento = documents_repo.get_by_id_and_user(data.document_id, current_user.id)
    
    if not documento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Para desencriptar, por favor vuelve a subir el archivo proporcionando la contraseña"
    )


@router.post("/extract")
async def extract_uploaded_pdf(
    file: UploadFile = File(..., description="Archivo PDF del extracto bancario"),
    password: Optional[str] = Form(None, description="Contraseña del PDF (si está protegido)"),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Extrae datos de un PDF recién subido en un solo paso usando Gemini AI.
    """
    from app.services.gemini_service import ExtractionStatus, get_gemini_service

    if file.content_type and file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo debe ser un PDF. Tipo recibido: {file.content_type}",
        )

    file_content = await file.read()
    if len(file_content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")

    gemini_service = get_gemini_service()
    storage_service = get_storage_service()

    if not gemini_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de extracción no disponible. Verifica la configuración de GEMINI_API_KEY.",
        )

    result = await gemini_service.extract_credit_data_from_upload(
        file_content=file_content,
        original_filename=file.filename or "extracto.pdf",
        user_id=str(current_user.id),
        password=password,
        storage_service=storage_service,
    )

    if result.requires_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "PDF_PASSWORD_REQUIRED",
                "message": result.message,
                "requires_password": True,
            },
        )

    if not result.success and result.extraction is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "PDF_PROCESSING_FAILED",
                "message": result.message,
                "validation_status": result.validation_status,
            },
        )

    extraction = result.extraction

    if extraction.status == ExtractionStatus.API_ERROR:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "GEMINI_API_ERROR", "message": extraction.message},
        )

    return {
        "success": extraction.status != ExtractionStatus.NOT_CREDIT_DOCUMENT,
        "status": extraction.status.value,
        "message": extraction.message,
        "confidence": extraction.confidence,
        "banco_detectado": extraction.banco_detectado,
        "campos_encontrados": extraction.campos_encontrados,
        "campos_faltantes": extraction.campos_faltantes,
        "es_extracto_hipotecario": extraction.es_extracto_hipotecario,
        "saved_file_path": result.saved_file_path,
        "checksum": result.checksum,
        "data": extraction.data,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE LECTURA Y ELIMINACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista los documentos del usuario autenticado."""
    documents_repo = DocumentsRepo(db)
    
    documents = documents_repo.list_by_user(
        usuario_id=current_user.id, status=status_filter, limit=limit, offset=offset
    )
    total = documents_repo.count_by_user(usuario_id=current_user.id, status=status_filter)
    
    return DocumentListResponse(
        documents=[
            DocumentMetadata(
                id=doc.id, usuario_id=doc.usuario_id, banco_id=doc.banco_id,
                original_filename=doc.original_filename, file_size=doc.file_size,
                mime_type=doc.mime_type, pdf_encrypted=doc.pdf_encrypted,
                checksum_sha256=doc.checksum, status=DocumentStatus(doc.status),
                created_at=doc.created_at
            ) for doc in documents
        ],
        total=total
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle de un documento específico."""
    documents_repo = DocumentsRepo(db)
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    
    return DocumentDetailResponse(
        document=DocumentMetadata(
            id=documento.id, usuario_id=documento.usuario_id, banco_id=documento.banco_id,
            original_filename=documento.original_filename, file_size=documento.file_size,
            mime_type=documento.mime_type, pdf_encrypted=documento.pdf_encrypted,
            checksum_sha256=documento.checksum, status=DocumentStatus(documento.status),
            created_at=documento.created_at
        )
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina un documento del usuario y su archivo físico del storage."""
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()
    
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    
    if documento.s3_key:
        storage_service.delete_pdf(documento.s3_key)
    
    documents_repo.delete(document_id)
    logger.info(f"Documento eliminado: {document_id} por usuario {current_user.id}")
    
    return {"message": "Documento eliminado exitosamente", "document_id": str(document_id)}


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT DE DESCARGA (URL PRESIGNED)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{document_id}/download")
async def get_document_download_url(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Genera una URL temporal y segura para descargar el PDF directamente desde Google Cloud Storage.
    
    ## Respuestas:
    - **200 OK**: Retorna la URL temporal (expira en 15 minutos)
    - **404 Not Found**: Documento no encontrado o sin archivo físico
    """
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service() 
    
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado o no tienes acceso"
        )
    
    if not documento.s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El documento no tiene un archivo físico asociado"
        )
    
    try:
        temporal_url = storage_service.generate_presigned_url(documento.s3_key, expiration_minutes=15)
        
        return {
            "success": True,
            "url": temporal_url,
            "filename": documento.original_filename
        }
    except Exception as e:
        logger.error(f"Error generando URL para {documento.s3_key}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el enlace de descarga"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS ADICIONALES DE GEMINI (Extracción / Comparación)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{document_id}/extract")
async def extract_document_data(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extrae datos estructurados de un documento PDF existente usando Gemini."""
    from app.services.gemini_service import (
        ExtractionStatus, get_gemini_service, map_extraction_to_analysis,
    )
    
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()
    gemini_service = get_gemini_service()
    
    if not gemini_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de extracción no disponible."
        )
    
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    if not documento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    
    if not documento.s3_key:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sin archivo asociado")
    
    pdf_content = storage_service.get_pdf(documento.s3_key)
    if not pdf_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado en storage")
    
    documento.status = "PROCESSING"
    documents_repo.update(documento)
    
    try:
        extraction_result = await gemini_service.extract_credit_data(pdf_content)
        
        if extraction_result.status == ExtractionStatus.NOT_CREDIT_DOCUMENT:
            documento.status = "FAILED"
            documents_repo.update(documento)
            return {
                "success": False, "status": extraction_result.status.value,
                "message": extraction_result.message, "es_extracto_hipotecario": False, "data": None
            }
        
        if extraction_result.status == ExtractionStatus.API_ERROR:
            documento.status = "UPLOADED" 
            documents_repo.update(documento)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error en servicio de extracción: {extraction_result.message}"
            )
        
        analysis_data = map_extraction_to_analysis(extraction_result, str(document_id), str(current_user.id))
        
        documento.status = "COMPLETED"
        documents_repo.update(documento)
        
        return {
            "success": True, "status": extraction_result.status.value,
            "message": extraction_result.message, "confidence": extraction_result.confidence,
            "banco_detectado": extraction_result.banco_detectado,
            "campos_encontrados": extraction_result.campos_encontrados,
            "campos_faltantes": extraction_result.campos_faltantes,
            "es_extracto_hipotecario": extraction_result.es_extracto_hipotecario,
            "data": analysis_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en extracción para documento {document_id}: {e}")
        documento.status = "FAILED"
        documents_repo.update(documento)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado durante la extracción: {str(e)}"
        )


@router.post("/{document_id}/compare-name")
async def compare_document_name(
    document_id: UUID,
    expected_name: str,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compara el nombre extraído del documento con un nombre esperado."""
    from app.services.gemini_service import get_gemini_service
    
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()
    gemini_service = get_gemini_service()
    
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    if not documento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    
    pdf_content = storage_service.get_pdf(documento.s3_key)
    if not pdf_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo PDF no encontrado")
    
    extraction = await gemini_service.extract_credit_data(pdf_content)
    pdf_name = extraction.data.get("nombre_titular", "")
    
    if not pdf_name:
        return {
            "match": False, "similarity": 0.0, "pdf_name": None,
            "expected_name": expected_name, "explanation": "No se pudo extraer el nombre del documento"
        }
    
    comparison = await gemini_service.compare_names(pdf_name, expected_name)
    
    return {
        "match": comparison.match,
        "similarity": comparison.similarity,
        "pdf_name": pdf_name,
        "expected_name": expected_name,
        "explanation": comparison.explanation
    }