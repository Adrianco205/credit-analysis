"""
PDF Service - Manejo de archivos PDF para EcoFinanzas
=====================================================

Funcionalidades:
- Detección de encriptación (contraseña)
- Desencriptación con pypdf (sucesor de PyPDF2)
- Guardado de PDF sin contraseña
- Extracción básica de texto
- Validación de contenido de crédito hipotecario
- Cálculo de checksum SHA-256
"""

import hashlib
import io
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from pypdf import PdfReader, PdfWriter

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
# SERVICIO PRINCIPAL
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
        """
        Detecta si un PDF está protegido con contraseña usando pypdf.
        
        Args:
            file_stream: Stream del archivo PDF
            
        Returns:
            bool: True si el PDF está encriptado, False en caso contrario
        """
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
        """
        Valida un PDF completamente: formato, tamaño, encriptación, contenido.
        
        Args:
            file_stream: Stream del archivo PDF
            check_keywords: Si validar keywords de crédito hipotecario
            max_size_mb: Tamaño máximo en MB (usa default si None)
            
        Returns:
            PDFValidationResult con todos los detalles
        """
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
        """
        Desencripta un PDF y retorna el contenido sin contraseña.
        Usa pypdf con soporte de criptografía.
        
        Args:
            file_stream: Stream del archivo PDF encriptado
            password: Contraseña para desencriptar
            
        Returns:
            PDFDecryptionResult con el contenido desencriptado si exitoso
        """
        try:
            file_stream.seek(0)
            content = file_stream.read()
            file_stream.seek(0)
            
            # Leer PDF encriptado
            reader = PdfReader(io.BytesIO(content))
            
            if not reader.is_encrypted:
                return PDFDecryptionResult(
                    success=True,
                    status=PDFStatus.OK,
                    message="El PDF no está encriptado",
                    decrypted_content=content,
                    page_count=len(reader.pages)
                )
            
            # Intentar desencriptar
            decrypt_result = reader.decrypt(password)
            
            # decrypt() retorna 0 si falla, 1 si es user password, 2 si es owner password
            if decrypt_result == 0:
                return PDFDecryptionResult(
                    success=False,
                    status=PDFStatus.INVALID_PASSWORD,
                    message="Contraseña incorrecta"
                )
            
            # Verificar que se puede leer
            try:
                page_count = len(reader.pages)
                # Intentar acceder a una página para confirmar
                _ = reader.pages[0]
            except Exception as e:
                return PDFDecryptionResult(
                    success=False,
                    status=PDFStatus.CORRUPTED,
                    message=f"PDF desencriptado pero corrupto: {str(e)}"
                )
            
            # Crear PDF sin encriptación
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            
            # Guardar a buffer
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
        """
        Calcula el hash SHA-256 del archivo para verificar integridad.
        
        Args:
            file_stream: Stream del archivo
            
        Returns:
            str: Hash SHA-256 hexadecimal
        """
        file_stream.seek(0)
        sha256_hash = hashlib.sha256()
        
        # Leer en chunks para archivos grandes
        for chunk in iter(lambda: file_stream.read(8192), b""):
            sha256_hash.update(chunk)
        
        file_stream.seek(0)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def extract_text_basic(file_stream: BinaryIO, password: str | None = None) -> str:
        """
        Extrae texto básico del PDF usando pypdf.
        Útil para validación rápida antes de enviar a Gemini.
        
        Args:
            file_stream: Stream del archivo PDF
            password: Contraseña si el PDF está protegido
            
        Returns:
            str: Texto extraído del PDF
        """
        try:
            file_stream.seek(0)
            reader = PdfReader(file_stream)
            
            # Si está encriptado, intentar desencriptar
            if reader.is_encrypted and password:
                reader.decrypt(password)
            
            # Extraer texto de todas las páginas
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
        """
        Valida que el texto contenga palabras clave de un análisis de crédito.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            Tuple[bool, float]: (es_válido, score_confianza)
        """
        # Palabras clave que debe contener un análisis de crédito
        keywords = [
            "crédito", "credito", "préstamo", "prestamo", "cuota",
            "capital", "interés", "interes", "saldo", "desembolso",
            "amortización", "amortizacion", "banco", "hipotecario"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Score de confianza basado en matches
        confidence_score = min(matches / len(keywords), 1.0)
        
        # Se considera válido si tiene al menos 30% de las keywords
        is_valid = confidence_score >= 0.3
        
        return is_valid, confidence_score


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICIO DE ALMACENAMIENTO LOCAL
# ═══════════════════════════════════════════════════════════════════════════════

class LocalStorageService:
    """
    Servicio para almacenar PDFs localmente.
    Sustituye temporalmente a S3 durante desarrollo.
    
    Estructura de carpetas:
    - uploads/
      - pdfs/
        - {user_id}/
          - {document_id}.pdf
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa el servicio de almacenamiento local.
        
        Args:
            base_path: Ruta base para almacenamiento. 
                      Por defecto usa 'uploads' en el directorio del proyecto.
        """
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Usar directorio 'uploads' relativo al backend
            self.base_path = Path(__file__).parent.parent.parent / "uploads"
        
        self.pdfs_path = self.base_path / "pdfs"
        
        # Crear directorios si no existen
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Crea la estructura de directorios necesaria."""
        self.pdfs_path.mkdir(parents=True, exist_ok=True)
        
        # Crear .gitignore para no subir PDFs al repo
        gitignore_path = self.base_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("# Ignorar todos los archivos subidos\n*\n!.gitignore\n")
    
    def _get_user_folder(self, user_id: str) -> Path:
        """Obtiene o crea la carpeta del usuario."""
        user_folder = self.pdfs_path / user_id
        user_folder.mkdir(parents=True, exist_ok=True)
        return user_folder
    
    def save_pdf(
        self,
        content: bytes,
        user_id: str,
        original_filename: str,
        document_id: Optional[str] = None
    ) -> PDFSaveResult:
        """
        Guarda un PDF en el sistema de archivos local.
        
        Args:
            content: Contenido del PDF en bytes
            user_id: ID del usuario (para organización)
            original_filename: Nombre original del archivo
            document_id: ID del documento (genera uno si no se proporciona)
            
        Returns:
            PDFSaveResult con la ruta del archivo guardado
        """
        try:
            # Generar ID si no se proporcionó
            if not document_id:
                document_id = str(uuid.uuid4())
            
            # Crear carpeta del usuario
            user_folder = self._get_user_folder(user_id)
            
            # Nombre del archivo: {document_id}_{original_name_sanitized}.pdf
            safe_name = self._sanitize_filename(original_filename)
            filename = f"{document_id}_{safe_name}"
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            file_path = user_folder / filename
            
            # Guardar archivo
            file_path.write_bytes(content)
            
            # Calcular checksum del archivo guardado
            checksum = hashlib.sha256(content).hexdigest()
            
            # Ruta relativa para almacenar en BD
            relative_path = f"pdfs/{user_id}/{filename}"
            
            logger.info(f"PDF guardado exitosamente: {relative_path}")
            
            return PDFSaveResult(
                success=True,
                message="PDF guardado exitosamente",
                file_path=relative_path,
                file_size_bytes=len(content),
                checksum=checksum
            )
            
        except Exception as e:
            logger.error(f"Error al guardar PDF: {str(e)}")
            return PDFSaveResult(
                success=False,
                message=f"Error al guardar el archivo: {str(e)}"
            )
    
    def get_pdf(self, relative_path: str) -> Optional[bytes]:
        """
        Obtiene el contenido de un PDF almacenado.
        
        Args:
            relative_path: Ruta relativa del archivo (como se guardó en BD)
            
        Returns:
            Contenido del PDF en bytes o None si no existe
        """
        try:
            file_path = self.base_path / relative_path
            
            if not file_path.exists():
                logger.warning(f"PDF no encontrado: {relative_path}")
                return None
            
            return file_path.read_bytes()
            
        except Exception as e:
            logger.error(f"Error al leer PDF: {str(e)}")
            return None
    
    def delete_pdf(self, relative_path: str) -> bool:
        """
        Elimina un PDF almacenado.
        
        Args:
            relative_path: Ruta relativa del archivo
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            file_path = self.base_path / relative_path
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"PDF eliminado: {relative_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error al eliminar PDF: {str(e)}")
            return False
    
    def pdf_exists(self, relative_path: str) -> bool:
        """Verifica si un PDF existe."""
        file_path = self.base_path / relative_path
        return file_path.exists()
    
    def get_absolute_path(self, relative_path: str) -> Optional[Path]:
        """Obtiene la ruta absoluta de un PDF."""
        file_path = self.base_path / relative_path
        if file_path.exists():
            return file_path
        return None
    
    def list_user_pdfs(self, user_id: str) -> list[str]:
        """Lista todos los PDFs de un usuario."""
        user_folder = self.pdfs_path / user_id
        if not user_folder.exists():
            return []
        
        return [
            f"pdfs/{user_id}/{f.name}" 
            for f in user_folder.glob("*.pdf")
        ]
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Limpia el nombre de archivo para uso seguro."""
        # Remover caracteres peligrosos
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)
        
        # Limitar longitud
        if len(sanitized) > 100:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:95] + ext
        
        return sanitized or "document.pdf"


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONVENIENCIA
# ═══════════════════════════════════════════════════════════════════════════════

def process_pdf_upload(
    file_content: bytes,
    original_filename: str,
    user_id: str,
    password: Optional[str] = None,
    storage_service: Optional[LocalStorageService] = None
) -> Tuple[PDFValidationResult, Optional[PDFSaveResult]]:
    """
    Procesa una subida de PDF completa: valida, desencripta si necesario, y guarda.
    
    Args:
        file_content: Contenido del archivo
        original_filename: Nombre original
        user_id: ID del usuario
        password: Contraseña si el PDF está encriptado
        storage_service: Servicio de almacenamiento (crea uno por defecto)
        
    Returns:
        Tuple de (resultado_validacion, resultado_guardado)
    """
    pdf_service = PdfService()
    storage = storage_service or LocalStorageService()
    
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
            # Actualizar resultado de validación con error de contraseña
            validation_result.is_valid = False
            validation_result.status = decrypt_result.status
            validation_result.message = decrypt_result.message
            return validation_result, None
        
        # Usar contenido desencriptado
        content_to_save = decrypt_result.decrypted_content
        validation_result.status = PDFStatus.DECRYPTED
        validation_result.message = "PDF desencriptado y guardado sin contraseña"
        validation_result.page_count = decrypt_result.page_count
        validation_result.is_encrypted = False
    
    # Paso 3: Guardar PDF
    save_result = storage.save_pdf(
        content=content_to_save,
        user_id=user_id,
        original_filename=original_filename
    )
    
    if save_result.success:
        validation_result.checksum = save_result.checksum
    
    return validation_result, save_result


# Instancia global del servicio de almacenamiento
_storage_service: Optional[LocalStorageService] = None


def get_storage_service() -> LocalStorageService:
    """Obtiene la instancia global del servicio de almacenamiento."""
    global _storage_service
    if _storage_service is None:
        _storage_service = LocalStorageService()
    return _storage_service
