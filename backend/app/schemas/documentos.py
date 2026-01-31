"""
Schemas de Documentos - DTOs para subida y gestión de PDFs
==========================================================

Incluye schemas para:
- Subida de archivos PDF
- Respuestas con estado de encriptación
- Metadatos de documentos
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentStatus(str, Enum):
    """Estados del documento en el sistema"""
    UPLOADED = "UPLOADED"  # Recién subido
    PROCESSING = "PROCESSING"  # En procesamiento (extracción IA)
    COMPLETED = "COMPLETED"  # Procesado exitosamente
    FAILED = "FAILED"  # Error en procesamiento
    

class PDFUploadStatus(str, Enum):
    """Estados específicos del proceso de upload"""
    OK = "OK"  # PDF válido y guardado
    ENCRYPTED = "ENCRYPTED"  # Tiene contraseña, necesita desencriptar
    DECRYPTED = "DECRYPTED"  # Fue desencriptado y guardado
    INVALID_PASSWORD = "INVALID_PASSWORD"  # Contraseña incorrecta
    CORRUPTED = "CORRUPTED"  # Archivo corrupto o no es PDF
    TOO_LARGE = "TOO_LARGE"  # Excede tamaño máximo
    EMPTY = "EMPTY"  # PDF sin contenido


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS DE REQUEST
# ═══════════════════════════════════════════════════════════════════════════════

class PDFPasswordInput(BaseModel):
    """Input para proporcionar contraseña de un PDF encriptado"""
    document_id: UUID = Field(..., description="ID del documento que requiere contraseña")
    password: str = Field(..., min_length=1, description="Contraseña del PDF")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS DE RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════

class PDFValidationResponse(BaseModel):
    """Respuesta de validación de PDF durante upload"""
    is_valid: bool = Field(..., description="Si el PDF es válido para procesar")
    status: PDFUploadStatus = Field(..., description="Estado del procesamiento")
    message: str = Field(..., description="Mensaje descriptivo")
    requires_password: bool = Field(False, description="Si se necesita contraseña")
    page_count: int = Field(0, description="Número de páginas del PDF")
    file_size_bytes: int = Field(0, description="Tamaño del archivo en bytes")
    has_credit_keywords: bool = Field(False, description="Si contiene keywords de crédito")
    keyword_confidence: float = Field(0.0, description="Confianza de que es extracto de crédito (0-1)")
    
    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """Respuesta completa de subida de documento"""
    success: bool = Field(..., description="Si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    
    # Datos del documento (si se guardó)
    document_id: Optional[UUID] = Field(None, description="ID del documento guardado")
    file_path: Optional[str] = Field(None, description="Ruta del archivo (interna)")
    checksum: Optional[str] = Field(None, description="SHA-256 del archivo")
    
    # Validación del PDF
    validation: PDFValidationResponse = Field(..., description="Resultado de validación")
    
    model_config = ConfigDict(from_attributes=True)


class DocumentMetadata(BaseModel):
    """Metadatos de un documento almacenado"""
    id: UUID
    usuario_id: UUID
    banco_id: Optional[int] = None
    
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    
    pdf_encrypted: bool = False
    checksum_sha256: Optional[str] = None
    
    status: DocumentStatus = DocumentStatus.UPLOADED
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Lista de documentos de un usuario"""
    documents: list[DocumentMetadata]
    total: int
    
    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(BaseModel):
    """Detalle completo de un documento"""
    document: DocumentMetadata
    
    # Info adicional del análisis si existe
    analisis_id: Optional[UUID] = Field(None, description="ID del análisis asociado")
    analisis_status: Optional[str] = Field(None, description="Estado del análisis")
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS PARA FLUJO COMPLETO
# ═══════════════════════════════════════════════════════════════════════════════

class UploadPDFWithPasswordRequest(BaseModel):
    """
    Request para subir PDF que podría tener contraseña.
    Se usa cuando el frontend ya sabe que el PDF tiene contraseña.
    """
    password: Optional[str] = Field(
        None, 
        min_length=1,
        description="Contraseña del PDF (si está encriptado)"
    )


class DecryptAndSaveRequest(BaseModel):
    """Request para desencriptar un PDF previamente subido temporalmente"""
    temp_file_id: str = Field(..., description="ID del archivo temporal")
    password: str = Field(..., min_length=1, description="Contraseña del PDF")


class DocumentProcessingStatus(BaseModel):
    """Estado del procesamiento de un documento"""
    document_id: UUID
    status: DocumentStatus
    progress_percent: int = Field(0, ge=0, le=100)
    current_step: str = Field("", description="Paso actual del procesamiento")
    error_message: Optional[str] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
