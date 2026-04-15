"""
PDF Service - Manejo de archivos PDF para PerFinanzas (GCS Integration)
=======================================================================

Funcionalidades:
- Detección de encriptación (contraseña)
- Desencriptación con pypdf
- Extracción básica de texto y validación de contenido
- Almacenamiento seguro en Google Cloud Storage (Bucket: perfinanzas-documentos)
- Generación de URLs firmadas para descarga
- Cálculo de checksum SHA-256
"""

import hashlib
import io
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import BinaryIO, Optional, Tuple, List

from google.cloud import storage
from pypdf import PdfReader, PdfWriter

from app.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS Y DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class PDFStatus(str, Enum):
    """Estados posibles del procesamiento de PDF"""
    OK = "OK"  # PDF válido y listo
    ENCRYPTED = "ENCRYPTED"  # Tiene contraseña, necesita desencriptar
    DECRYPTED = "DECRYPTED"  # Fue desencriptado exitosamente
    INVALID_PASSWORD = "INVALID_PASSWORD"  # Contraseña incorrecta
    CORRUPTED = "CORRUPTED"  # Archivo corrupto o no es PDF
    TOO_LARGE = "TOO_LARGE"  # Excede tamaño máximo
    EMPTY = "EMPTY"  # PDF sin contenido


@dataclass
class PDFValidationResult:
    """Resultado de validación de un PDF"""
    is_valid: bool
    status: PDFStatus
    message: str
    is_encrypted: bool = False
    page_count: int = 0
    file_size_bytes: int = 0
    checksum: Optional[str] = None
    has_credit_keywords: bool = False
    keyword_confidence: float = 0.0


@dataclass
class PDFDecryptionResult:
    """Resultado de desencriptación de un PDF"""
    success: bool
    status: PDFStatus
    message: str
    decrypted_content: Optional[bytes] = None
    page_count: int = 0


@dataclass
class PDFSaveResult:
    """Resultado de guardar un PDF"""
    success: bool
    message: str
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    checksum: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICIO DE PROCESAMIENTO PDF
# ═══════════════════════════════════════════════════════════════════════════════

class PdfService:
    """
    Servicio para manejo de archivos PDF.
    Incluye detección de encriptación, desencriptación y preparación para IA.
    
    Usa pypdf (sucesor de PyPDF2) para todas las operaciones.
    """
    
    # Configuración
    MAX_FILE_SIZE_MB = 20  # Tamaño máximo permitido
    ALLOWED_MIME_TYPES = ["application/pdf"]
    
    @staticmethod
    def is_pdf_encrypted(file_stream: BinaryIO) -> bool:
        """Detecta si un PDF está protegido con contraseña."""
        try:
            file_stream.seek(0)
            content = file_stream.read()
            file_stream.seek(0)
            
            reader = PdfReader(io.BytesIO(content))
            return reader.is_encrypted
            
        except Exception as e:
            logger.error(f"Error al verificar encriptación del PDF: {str(e)}")
            file_stream.seek(0)
            return False
    
    @staticmethod
    def validate_pdf(
        file_stream: BinaryIO, 
        check_keywords: bool = True,
        max_size_mb: Optional[float] = None
    ) -> PDFValidationResult:
        """Valida un PDF completamente: formato, tamaño, encriptación, contenido."""
        max_size = (max_size_mb or PdfService.MAX_FILE_SIZE_MB) * 1024 * 1024
        
        try:
            file_stream.seek(0)
            content = file_stream.read()
            file_size = len(content)
            file_stream.seek(0)
            
            # Validar tamaño
            if file_size > max_size:
                return PDFValidationResult(
                    is_valid=False,
                    status=PDFStatus.TOO_LARGE,
                    message=f"El archivo excede el tamaño máximo de {max_size_mb or PdfService.MAX_FILE_SIZE_MB}MB",
                    file_size_bytes=file_size
                )
            
            if file_size == 0:
                return PDFValidationResult(
                    is_valid=False,
                    status=PDFStatus.EMPTY,
                    message="El archivo está vacío"
                )
            
            # Verificar que es un PDF válido (magic bytes)
            if not content.startswith(b'%PDF'):
                return PDFValidationResult(
                    is_valid=False,
                    status=PDFStatus.CORRUPTED,
                    message="El archivo no es un PDF válido"
                )
            
            # Calcular checksum
            checksum = hashlib.sha256(content).hexdigest()
            
            # Intentar leer el PDF
            try:
                reader = PdfReader(io.BytesIO(content))
                
                # Verificar si está encriptado
                if reader.is_encrypted:
                    return PDFValidationResult(
                        is_valid=True,  # Es válido pero necesita contraseña
                        status=PDFStatus.ENCRYPTED,
                        message="El PDF requiere contraseña para abrirlo",
                        is_encrypted=True,
                        file_size_bytes=file_size,
                        checksum=checksum
                    )
                
                # Contar páginas
                page_count = len(reader.pages)
                
            except Exception as e:
                return PDFValidationResult(
                    is_valid=False,
                    status=PDFStatus.CORRUPTED,
                    message=f"Error al leer el PDF: {str(e)}",
                    file_size_bytes=file_size
                )
            
            # Validar keywords de crédito si se solicita
            has_keywords = False
            keyword_confidence = 0.0
            
            if check_keywords:
                text = PdfService.extract_text_basic(io.BytesIO(content))
                has_keywords, keyword_confidence = PdfService.validate_credit_analysis_keywords(text)
            
            return PDFValidationResult(
                is_valid=True,
                status=PDFStatus.OK,
                message="PDF válido y listo para procesar",
                is_encrypted=False,
                page_count=page_count,
                file_size_bytes=file_size,
                checksum=checksum,
                has_credit_keywords=has_keywords,
                keyword_confidence=keyword_confidence
            )
            
        except Exception as e:
            logger.error(f"Error en validación de PDF: {str(e)}")
            file_stream.seek(0)
            return PDFValidationResult(
                is_valid=False,
                status=PDFStatus.CORRUPTED,
                message=f"Error inesperado: {str(e)}"
            )

    @staticmethod
    def decrypt_pdf(
        file_stream: BinaryIO, 
        password: str
    ) -> PDFDecryptionResult:
        """Desencripta un PDF y retorna el contenido sin contraseña."""
        try:
            file_stream.seek(0)
            content = file_stream.read()
            file_stream.seek(0)
            
            reader = PdfReader(io.BytesIO(content))
            
            if not reader.is_encrypted:
                return PDFDecryptionResult(
                    success=True,
                    status=PDFStatus.OK,
                    message="El PDF no está encriptado",
                    decrypted_content=content,
                    page_count=len(reader.pages)
                )
            
            decrypt_result = reader.decrypt(password)
            
            if decrypt_result == 0:
                return PDFDecryptionResult(
                    success=False,
                    status=PDFStatus.INVALID_PASSWORD,
                    message="Contraseña incorrecta"
                )
            
            try:
                page_count = len(reader.pages)
                _ = reader.pages[0]
            except Exception as e:
                return PDFDecryptionResult(
                    success=False,
                    status=PDFStatus.CORRUPTED,
                    message=f"PDF desencriptado pero corrupto: {str(e)}"
                )
            
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            
            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)
            decrypted_content = output_buffer.read()
            
            return PDFDecryptionResult(
                success=True,
                status=PDFStatus.DECRYPTED,
                message="PDF desencriptado exitosamente",
                decrypted_content=decrypted_content,
                page_count=page_count
            )
                
        except Exception as e:
            logger.error(f"Error al desencriptar PDF: {str(e)}")
            file_stream.seek(0)
            return PDFDecryptionResult(
                success=False,
                status=PDFStatus.CORRUPTED,
                message=f"Error al procesar el PDF: {str(e)}"
            )
    
    @staticmethod
    def calculate_checksum(file_stream: BinaryIO) -> str:
        """Calcula el hash SHA-256 del archivo para verificar integridad."""
        file_stream.seek(0)
        sha256_hash = hashlib.sha256()
        for chunk in iter(lambda: file_stream.read(8192), b""):
            sha256_hash.update(chunk)
        file_stream.seek(0)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def extract_text_basic(file_stream: BinaryIO, password: str | None = None) -> str:
        """Extrae texto básico del PDF. Útil para validación antes de Gemini."""
        try:
            file_stream.seek(0)
            reader = PdfReader(file_stream)
            
            if reader.is_encrypted and password:
                reader.decrypt(password)
            
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            file_stream.seek(0)
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF: {str(e)}")
            file_stream.seek(0)
            return ""
    
    @staticmethod
    def validate_credit_analysis_keywords(text: str) -> Tuple[bool, float]:
        """Valida que el texto contenga palabras clave de un análisis de crédito."""
        keywords = [
            "crédito", "credito", "préstamo", "prestamo", "cuota",
            "capital", "interés", "interes", "saldo", "desembolso",
            "amortización", "amortizacion", "banco", "hipotecario"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        confidence_score = min(matches / len(keywords), 1.0)
        is_valid = confidence_score >= 0.3
        
        return is_valid, confidence_score


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICIO DE ALMACENAMIENTO GCS
# ═══════════════════════════════════════════════════════════════════════════════

class GCSService:
    """
    Servicio para almacenar y gestionar PDFs en Google Cloud Storage.
    """
    
    def __init__(self):
        # Asume automáticamente la identidad de la VM que configuramos
        self.client = storage.Client()
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.bucket = self.client.bucket(self.bucket_name)

    def save_pdf(
        self, 
        content: bytes, 
        user_id: str, 
        original_filename: str, 
        document_id: Optional[str] = None
    ) -> PDFSaveResult:
        """Guarda el archivo en GCS y retorna la metadata requerida."""
        try:
            # Generar ID si no se proporcionó
            if not document_id:
                document_id = str(uuid.uuid4())
            
            # Generar ruta única: usuarios/{user_id}/{document_id}.pdf
            file_extension = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'
            blob_name = f"usuarios/{user_id}/{document_id}.{file_extension}"
            
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(content, content_type="application/pdf")
            
            checksum = hashlib.sha256(content).hexdigest()
            logger.info(f"PDF guardado exitosamente en GCS: {blob_name}")
            
            return PDFSaveResult(
                success=True,
                message='Upload a GCS exitoso',
                file_path=blob_name,  # Esto se guarda como s3_key en tu DB
                file_size_bytes=len(content),
                checksum=checksum
            )
        except Exception as e:
            logger.error(f"Error al guardar PDF en GCS: {str(e)}")
            return PDFSaveResult(
                success=False,
                message=f"Error al guardar el archivo: {str(e)}"
            )

    def generate_presigned_url(self, blob_name: str, expiration_minutes: int = 15) -> Optional[str]:
        """Genera una URL temporal para descarga directa."""
        try:
            blob = self.bucket.blob(blob_name)
            if not blob.exists():
                return None
                
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Error al generar URL firmada: {str(e)}")
            return None

    def get_pdf(self, blob_name: str) -> Optional[bytes]:
        """Descarga el PDF a memoria (Útil para enviarlo a Gemini)."""
        try:
            blob = self.bucket.blob(blob_name)
            if not blob.exists():
                logger.warning(f"PDF no encontrado en GCS: {blob_name}")
                return None
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"Error al leer PDF de GCS: {str(e)}")
            return None
            
    def delete_pdf(self, blob_name: str) -> bool:
        """Elimina el archivo del bucket."""
        try:
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
                logger.info(f"PDF eliminado de GCS: {blob_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al eliminar PDF de GCS: {str(e)}")
            return False

    def pdf_exists(self, blob_name: str) -> bool:
        """Verifica si un PDF existe en GCS."""
        blob = self.bucket.blob(blob_name)
        return blob.exists()
        
    def list_user_pdfs(self, user_id: str) -> List[str]:
        """Lista todos los PDFs de un usuario en GCS."""
        try:
            prefix = f"usuarios/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs if blob.name.endswith('.pdf')]
        except Exception as e:
            logger.error(f"Error al listar PDFs de GCS: {str(e)}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONVENIENCIA
# ═══════════════════════════════════════════════════════════════════════════════

def process_pdf_upload(
    file_content: bytes,
    original_filename: str,
    user_id: str,
    password: Optional[str] = None,
    storage_service: Optional[GCSService] = None
) -> Tuple[PDFValidationResult, Optional[PDFSaveResult]]:
    """
    Procesa una subida de PDF completa: valida, desencripta si necesario, y guarda en GCS.
    """
    pdf_service = PdfService()
    storage = storage_service or get_storage_service()
    
    file_stream = io.BytesIO(file_content)
    
    # Paso 1: Validar PDF
    validation_result = pdf_service.validate_pdf(file_stream, check_keywords=True)
    
    # Si está encriptado y no hay contraseña, retornar indicando que se necesita
    if validation_result.status == PDFStatus.ENCRYPTED and not password:
        return validation_result, None
    
    # Si no es válido (excepto encriptado), retornar error
    if not validation_result.is_valid and validation_result.status != PDFStatus.ENCRYPTED:
        return validation_result, None
    
    # Paso 2: Desencriptar si es necesario
    content_to_save = file_content
    
    if validation_result.status == PDFStatus.ENCRYPTED and password:
        decrypt_result = pdf_service.decrypt_pdf(file_stream, password)
        
        if not decrypt_result.success:
            validation_result.is_valid = False
            validation_result.status = decrypt_result.status
            validation_result.message = decrypt_result.message
            return validation_result, None
        
        content_to_save = decrypt_result.decrypted_content
        validation_result.status = PDFStatus.DECRYPTED
        validation_result.message = "PDF desencriptado y guardado sin contraseña"
        validation_result.page_count = decrypt_result.page_count
        validation_result.is_encrypted = False
    
    # Paso 3: Guardar PDF en Google Cloud Storage
    save_result = storage.save_pdf(
        content=content_to_save,
        user_id=user_id,
        original_filename=original_filename
    )
    
    if save_result.success:
        validation_result.checksum = save_result.checksum
    
    return validation_result, save_result


# Instancia global del servicio de almacenamiento
_storage_service: Optional[GCSService] = None

def get_storage_service() -> GCSService:
    """Obtiene la instancia global del servicio de almacenamiento GCS."""
    global _storage_service
    if _storage_service is None:
        _storage_service = GCSService()
    return _storage_service