"""
Documents API - Endpoints para subida y gestión de PDFs
========================================================

Endpoints:
- POST /upload - Subir PDF (con detección de contraseña)
- POST /decrypt - Desencriptar PDF con contraseña
- GET / - Listar documentos del usuario
- GET /{id} - Obtener detalle de un documento
- DELETE /{id} - Eliminar un documento
"""

import io
import logging
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
    LocalStorageService,
    PDFStatus,
    PdfService,
    get_storage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE UPLOAD
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
    
    ## Respuestas:
    - **200 OK**: PDF procesado exitosamente (ver `validation.status`)
    - **400 Bad Request**: Archivo inválido o muy grande
    - **401 Unauthorized**: No autenticado
    - **409 Conflict**: Documento duplicado (mismo checksum)
    """
    # Validar que sea un archivo PDF por el content type
    if file.content_type and file.content_type != "application/pdf":
        # Permitir octet-stream porque algunos navegadores lo envían así
        if file.content_type != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo debe ser un PDF. Tipo recibido: {file.content_type}"
            )
    
    # Leer contenido del archivo
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío"
        )
    
    # Inicializar servicios
    pdf_service = PdfService()
    storage_service = get_storage_service()
    documents_repo = DocumentsRepo(db)
    
    # Paso 1: Validar el PDF
    file_stream = io.BytesIO(content)
    validation_result = pdf_service.validate_pdf(file_stream, check_keywords=True)
    
    # Construir respuesta de validación base
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
    
    # Si está encriptado y no hay contraseña, pedir contraseña
    if validation_result.status == PDFStatus.ENCRYPTED and not password:
        return DocumentUploadResponse(
            success=False,
            message="El PDF está protegido con contraseña. Por favor proporciona la contraseña.",
            validation=validation_response
        )
    
    # Si no es válido (y no es encriptado), retornar error
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
            validation_response.status = PDFUploadStatus(decrypt_result.status.value)
            validation_response.message = decrypt_result.message
            validation_response.is_valid = False
            
            return DocumentUploadResponse(
                success=False,
                message=decrypt_result.message,
                validation=validation_response
            )
        
        # Usar contenido desencriptado
        content_to_save = decrypt_result.decrypted_content
        was_encrypted = True
        validation_response.status = PDFUploadStatus.DECRYPTED
        validation_response.message = "PDF desencriptado y guardado sin contraseña"
        validation_response.page_count = decrypt_result.page_count
        validation_response.requires_password = False
    
    # Paso 3: Verificar duplicados (por checksum)
    import hashlib
    checksum = hashlib.sha256(content_to_save).hexdigest()
    
    existing_doc = documents_repo.get_by_checksum_and_user(checksum, current_user.id)
    if existing_doc:
        return DocumentUploadResponse(
            success=False,
            message="Ya tienes este documento subido anteriormente",
            document_id=existing_doc.id,
            validation=PDFValidationResponse(
                is_valid=True,
                status=PDFUploadStatus.OK,
                message="Documento duplicado",
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
    
    logger.info(
        f"Documento subido: {documento.id} por usuario {current_user.id}, "
        f"encriptado={was_encrypted}, tamaño={save_result.file_size_bytes}"
    )
    
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
    
    Este endpoint se usa cuando:
    1. Se subió un PDF encriptado sin contraseña
    2. El frontend recibe `requires_password=true`
    3. El usuario proporciona la contraseña
    
    Nota: En la implementación actual, el archivo original debe volver a subirse
    con la contraseña. Este endpoint está reservado para flujos alternativos.
    """
    documents_repo = DocumentsRepo(db)
    
    # Verificar que el documento existe y pertenece al usuario
    documento = documents_repo.get_by_id_and_user(data.document_id, current_user.id)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Este endpoint está reservado para un flujo alternativo donde
    # el archivo se guarda temporalmente encriptado
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Para desencriptar, por favor vuelve a subir el archivo proporcionando la contraseña"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE LECTURA
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista los documentos del usuario autenticado.
    
    ## Parámetros:
    - **status_filter**: Filtrar por status (UPLOADED, PROCESSING, COMPLETED, FAILED)
    - **limit**: Máximo de resultados (default: 50)
    - **offset**: Offset para paginación
    """
    documents_repo = DocumentsRepo(db)
    
    documents = documents_repo.list_by_user(
        usuario_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset
    )
    
    total = documents_repo.count_by_user(
        usuario_id=current_user.id,
        status=status_filter
    )
    
    return DocumentListResponse(
        documents=[
            DocumentMetadata(
                id=doc.id,
                usuario_id=doc.usuario_id,
                banco_id=doc.banco_id,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                pdf_encrypted=doc.pdf_encrypted,
                checksum_sha256=doc.checksum_sha256,
                status=DocumentStatus(doc.status),
                created_at=doc.created_at
            )
            for doc in documents
        ],
        total=total
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene el detalle de un documento específico.
    """
    documents_repo = DocumentsRepo(db)
    
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # TODO: Agregar info del análisis asociado si existe
    
    return DocumentDetailResponse(
        document=DocumentMetadata(
            id=documento.id,
            usuario_id=documento.usuario_id,
            banco_id=documento.banco_id,
            original_filename=documento.original_filename,
            file_size=documento.file_size,
            mime_type=documento.mime_type,
            pdf_encrypted=documento.pdf_encrypted,
            checksum_sha256=documento.checksum_sha256,
            status=DocumentStatus(documento.status),
            created_at=documento.created_at
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE DELETE
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina un documento del usuario.
    
    También elimina el archivo físico del storage.
    """
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()
    
    # Obtener documento
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Eliminar archivo físico
    if documento.s3_key:
        storage_service.delete_pdf(documento.s3_key)
    
    # Eliminar registro de BD
    documents_repo.delete(document_id)
    
    logger.info(f"Documento eliminado: {document_id} por usuario {current_user.id}")
    
    return {"message": "Documento eliminado exitosamente", "document_id": str(document_id)}


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE EXTRACCIÓN CON GEMINI
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{document_id}/extract")
async def extract_document_data(
    document_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extrae datos del documento PDF usando Google Gemini AI.
    
    ## Flujo:
    1. Obtiene el PDF almacenado
    2. Envía a Gemini para extracción de datos
    3. Retorna datos estructurados del crédito hipotecario
    
    ## Respuestas:
    - **200 OK**: Datos extraídos exitosamente
    - **404 Not Found**: Documento no encontrado
    - **422 Unprocessable Entity**: No se pudieron extraer datos
    - **503 Service Unavailable**: Gemini API no disponible
    """
    from app.services.gemini_service import (
        ExtractionStatus,
        get_gemini_service,
        map_extraction_to_analysis,
    )
    
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()
    gemini_service = get_gemini_service()
    
    # Verificar que el servicio está configurado
    if not gemini_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de extracción no disponible. Verifica la configuración de GEMINI_API_KEY."
        )
    
    # Obtener documento
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Obtener contenido del PDF
    if not documento.s3_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El documento no tiene archivo asociado"
        )
    
    pdf_content = storage_service.get_pdf(documento.s3_key)
    
    if not pdf_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo PDF no encontrado en storage"
        )
    
    # Actualizar estado a PROCESSING
    documento.status = "PROCESSING"
    documents_repo.update(documento)
    
    logger.info(f"Iniciando extracción Gemini para documento {document_id}")
    
    try:
        # Extraer datos con Gemini
        extraction_result = await gemini_service.extract_credit_data(pdf_content)
        
        # Verificar resultado
        if extraction_result.status == ExtractionStatus.NOT_CREDIT_DOCUMENT:
            documento.status = "FAILED"
            documents_repo.update(documento)
            
            return {
                "success": False,
                "status": extraction_result.status.value,
                "message": extraction_result.message,
                "es_extracto_hipotecario": False,
                "data": None
            }
        
        if extraction_result.status == ExtractionStatus.API_ERROR:
            documento.status = "UPLOADED"  # Revertir a estado anterior
            documents_repo.update(documento)
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error en servicio de extracción: {extraction_result.message}"
            )
        
        # Mapear datos al formato de análisis
        analysis_data = map_extraction_to_analysis(
            extraction_result,
            str(document_id),
            str(current_user.id)
        )
        
        # Actualizar estado del documento
        documento.status = "COMPLETED"
        documents_repo.update(documento)
        
        logger.info(
            f"Extracción completada para documento {document_id}. "
            f"Status: {extraction_result.status.value}, "
            f"Confianza: {extraction_result.confidence:.2%}"
        )
        
        return {
            "success": True,
            "status": extraction_result.status.value,
            "message": extraction_result.message,
            "confidence": extraction_result.confidence,
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
    """
    Compara el nombre extraído del documento con un nombre esperado.
    
    Útil para validar que el documento pertenece al usuario correcto.
    
    ## Parámetros:
    - **expected_name**: Nombre a comparar con el extraído del documento
    
    ## Respuesta:
    - match: Si los nombres coinciden (con tolerancia)
    - similarity: Porcentaje de similitud (0-1)
    - explanation: Explicación del resultado
    """
    from app.services.gemini_service import get_gemini_service
    
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()
    gemini_service = get_gemini_service()
    
    # Obtener documento
    documento = documents_repo.get_by_id_and_user(document_id, current_user.id)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Por ahora hacemos extracción completa para obtener el nombre
    # En producción, esto debería cachear el resultado de extracción
    pdf_content = storage_service.get_pdf(documento.s3_key)
    
    if not pdf_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo PDF no encontrado"
        )
    
    # Extraer datos (o usar cache)
    extraction = await gemini_service.extract_credit_data(pdf_content)
    
    pdf_name = extraction.data.get("nombre_titular", "")
    
    if not pdf_name:
        return {
            "match": False,
            "similarity": 0.0,
            "pdf_name": None,
            "expected_name": expected_name,
            "explanation": "No se pudo extraer el nombre del documento"
        }
    
    # Comparar nombres
    comparison = await gemini_service.compare_names(pdf_name, expected_name)
    
    return {
        "match": comparison.match,
        "similarity": comparison.similarity,
        "pdf_name": pdf_name,
        "expected_name": expected_name,
        "explanation": comparison.explanation
    }
