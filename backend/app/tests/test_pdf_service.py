"""
Tests para PDF Service - Validación, desencriptación y almacenamiento
=====================================================================

Pruebas:
- Validación de PDFs (válidos, corruptos, muy grandes)
- Detección de encriptación
- Desencriptación con contraseña correcta/incorrecta
- Almacenamiento local
- Extracción de texto básico
"""

import hashlib
import io
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Generator

import pytest
from pypdf import PdfWriter

from app.services.pdf_service import (
    LocalStorageService,
    PDFDecryptionResult,
    PDFSaveResult,
    PDFStatus,
    PDFValidationResult,
    PdfService,
    process_pdf_upload,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def pdf_service() -> PdfService:
    """Instancia del servicio PDF."""
    return PdfService()


@pytest.fixture
def temp_storage_dir() -> Generator[Path, None, None]:
    """Directorio temporal para tests de almacenamiento."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage_service(temp_storage_dir: Path) -> LocalStorageService:
    """Servicio de almacenamiento con directorio temporal."""
    return LocalStorageService(base_path=str(temp_storage_dir))


@pytest.fixture
def simple_pdf_content() -> bytes:
    """Genera un PDF simple sin encriptación."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)  # Página carta
    
    # Agregar metadatos
    writer.add_metadata({
        "/Title": "Test Document",
        "/Author": "Test",
    })
    
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def encrypted_pdf_content() -> tuple[bytes, str]:
    """Genera un PDF encriptado con contraseña conocida."""
    password = "test123"
    
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    
    # Encriptar con contraseña de usuario
    writer.encrypt(user_password=password, owner_password=password)
    
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.read(), password


@pytest.fixture
def credit_pdf_content() -> bytes:
    """Genera un PDF con keywords de crédito hipotecario."""
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, TextStringObject
    
    writer = PdfWriter()
    
    # Crear una página con texto de crédito
    page = writer.add_blank_page(width=612, height=792)
    
    # Agregar metadatos con keywords
    writer.add_metadata({
        "/Title": "Extracto de Crédito Hipotecario",
        "/Subject": "Crédito hipotecario banco cuota capital interés saldo amortización",
        "/Keywords": "crédito, hipotecario, banco, cuota, capital, interés",
    })
    
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.read()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VALIDACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFValidation:
    """Tests para validación de PDFs."""
    
    def test_validate_valid_pdf(self, pdf_service: PdfService, simple_pdf_content: bytes):
        """Validar un PDF válido sin encriptación."""
        file_stream = io.BytesIO(simple_pdf_content)
        
        result = pdf_service.validate_pdf(file_stream, check_keywords=False)
        
        assert result.is_valid is True
        assert result.status == PDFStatus.OK
        assert result.is_encrypted is False
        assert result.page_count == 1
        assert result.file_size_bytes > 0
        assert result.checksum is not None
    
    def test_validate_encrypted_pdf(self, pdf_service: PdfService, encrypted_pdf_content: tuple[bytes, str]):
        """Validar un PDF encriptado detecta que necesita contraseña."""
        content, _ = encrypted_pdf_content
        file_stream = io.BytesIO(content)
        
        result = pdf_service.validate_pdf(file_stream, check_keywords=False)
        
        assert result.is_valid is True  # Válido pero necesita contraseña
        assert result.status == PDFStatus.ENCRYPTED
        assert result.is_encrypted is True
        assert result.message == "El PDF requiere contraseña para abrirlo"
    
    def test_validate_empty_file(self, pdf_service: PdfService):
        """Validar archivo vacío retorna error."""
        file_stream = io.BytesIO(b"")
        
        result = pdf_service.validate_pdf(file_stream)
        
        assert result.is_valid is False
        assert result.status == PDFStatus.EMPTY
    
    def test_validate_not_a_pdf(self, pdf_service: PdfService):
        """Validar archivo que no es PDF retorna error."""
        file_stream = io.BytesIO(b"This is not a PDF file")
        
        result = pdf_service.validate_pdf(file_stream)
        
        assert result.is_valid is False
        assert result.status == PDFStatus.CORRUPTED
        assert "no es un PDF válido" in result.message
    
    def test_validate_file_too_large(self, pdf_service: PdfService, simple_pdf_content: bytes):
        """Validar archivo muy grande retorna error."""
        file_stream = io.BytesIO(simple_pdf_content)
        
        # Limitar a 0.0001 MB (prácticamente cualquier archivo es demasiado grande)
        result = pdf_service.validate_pdf(file_stream, max_size_mb=0.0001)
        
        assert result.is_valid is False
        assert result.status == PDFStatus.TOO_LARGE
    
    def test_validate_checksum_calculation(self, pdf_service: PdfService, simple_pdf_content: bytes):
        """Verificar que el checksum se calcula correctamente."""
        file_stream = io.BytesIO(simple_pdf_content)
        
        result = pdf_service.validate_pdf(file_stream, check_keywords=False)
        
        # Calcular checksum esperado
        expected_checksum = hashlib.sha256(simple_pdf_content).hexdigest()
        
        assert result.checksum == expected_checksum


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE DESENCRIPTACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFDecryption:
    """Tests para desencriptación de PDFs."""
    
    def test_decrypt_with_correct_password(self, pdf_service: PdfService, encrypted_pdf_content: tuple[bytes, str]):
        """Desencriptar PDF con contraseña correcta."""
        content, password = encrypted_pdf_content
        file_stream = io.BytesIO(content)
        
        result = pdf_service.decrypt_pdf(file_stream, password)
        
        assert result.success is True
        assert result.status == PDFStatus.DECRYPTED
        assert result.decrypted_content is not None
        assert len(result.decrypted_content) > 0
        assert result.page_count == 1
    
    def test_decrypt_with_wrong_password(self, pdf_service: PdfService, encrypted_pdf_content: tuple[bytes, str]):
        """Desencriptar PDF con contraseña incorrecta falla."""
        content, _ = encrypted_pdf_content
        file_stream = io.BytesIO(content)
        
        result = pdf_service.decrypt_pdf(file_stream, "wrong_password")
        
        assert result.success is False
        assert result.status == PDFStatus.INVALID_PASSWORD
        assert result.decrypted_content is None
    
    def test_decrypt_non_encrypted_pdf(self, pdf_service: PdfService, simple_pdf_content: bytes):
        """Desencriptar PDF sin encriptación retorna el contenido original."""
        file_stream = io.BytesIO(simple_pdf_content)
        
        result = pdf_service.decrypt_pdf(file_stream, "any_password")
        
        assert result.success is True
        assert result.status == PDFStatus.OK
        assert result.decrypted_content is not None
    
    def test_decrypted_pdf_is_readable(self, pdf_service: PdfService, encrypted_pdf_content: tuple[bytes, str]):
        """Verificar que el PDF desencriptado se puede leer."""
        content, password = encrypted_pdf_content
        file_stream = io.BytesIO(content)
        
        result = pdf_service.decrypt_pdf(file_stream, password)
        
        assert result.success is True
        
        # Verificar que el contenido desencriptado es un PDF válido
        decrypted_stream = io.BytesIO(result.decrypted_content)
        validation = pdf_service.validate_pdf(decrypted_stream, check_keywords=False)
        
        assert validation.is_valid is True
        assert validation.is_encrypted is False
        assert validation.status == PDFStatus.OK


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE ALMACENAMIENTO LOCAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestLocalStorage:
    """Tests para almacenamiento local de PDFs."""
    
    def test_save_pdf_success(self, storage_service: LocalStorageService, simple_pdf_content: bytes):
        """Guardar un PDF exitosamente."""
        user_id = str(uuid.uuid4())
        
        result = storage_service.save_pdf(
            content=simple_pdf_content,
            user_id=user_id,
            original_filename="test.pdf"
        )
        
        assert result.success is True
        assert result.file_path is not None
        assert result.file_path.startswith("pdfs/")
        assert user_id in result.file_path
        assert result.file_size_bytes == len(simple_pdf_content)
        assert result.checksum is not None
    
    def test_save_and_retrieve_pdf(self, storage_service: LocalStorageService, simple_pdf_content: bytes):
        """Guardar y recuperar un PDF."""
        user_id = str(uuid.uuid4())
        
        save_result = storage_service.save_pdf(
            content=simple_pdf_content,
            user_id=user_id,
            original_filename="test.pdf"
        )
        
        assert save_result.success is True
        
        # Recuperar
        retrieved_content = storage_service.get_pdf(save_result.file_path)
        
        assert retrieved_content is not None
        assert retrieved_content == simple_pdf_content
    
    def test_delete_pdf(self, storage_service: LocalStorageService, simple_pdf_content: bytes):
        """Eliminar un PDF."""
        user_id = str(uuid.uuid4())
        
        save_result = storage_service.save_pdf(
            content=simple_pdf_content,
            user_id=user_id,
            original_filename="test.pdf"
        )
        
        assert save_result.success is True
        
        # Verificar que existe
        assert storage_service.pdf_exists(save_result.file_path) is True
        
        # Eliminar
        deleted = storage_service.delete_pdf(save_result.file_path)
        
        assert deleted is True
        assert storage_service.pdf_exists(save_result.file_path) is False
    
    def test_get_nonexistent_pdf(self, storage_service: LocalStorageService):
        """Obtener un PDF que no existe retorna None."""
        result = storage_service.get_pdf("pdfs/nonexistent/file.pdf")
        
        assert result is None
    
    def test_list_user_pdfs(self, storage_service: LocalStorageService, simple_pdf_content: bytes):
        """Listar PDFs de un usuario."""
        user_id = str(uuid.uuid4())
        
        # Guardar varios PDFs
        for i in range(3):
            storage_service.save_pdf(
                content=simple_pdf_content,
                user_id=user_id,
                original_filename=f"test_{i}.pdf"
            )
        
        # Listar
        pdfs = storage_service.list_user_pdfs(user_id)
        
        assert len(pdfs) == 3
        assert all(user_id in pdf for pdf in pdfs)
    
    def test_sanitize_filename_special_chars(self, storage_service: LocalStorageService, simple_pdf_content: bytes):
        """Verificar que nombres de archivo con caracteres especiales se sanitizan."""
        user_id = str(uuid.uuid4())
        
        result = storage_service.save_pdf(
            content=simple_pdf_content,
            user_id=user_id,
            original_filename="archivo con espacios y ñ!@#$.pdf"
        )
        
        assert result.success is True
        # Verificar que no tiene caracteres especiales en la ruta
        assert "!" not in result.file_path
        assert "@" not in result.file_path
        assert "#" not in result.file_path
        assert "$" not in result.file_path


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE EXTRACCIÓN DE TEXTO
# ═══════════════════════════════════════════════════════════════════════════════

class TestTextExtraction:
    """Tests para extracción de texto de PDFs."""
    
    def test_extract_text_basic(self, pdf_service: PdfService, simple_pdf_content: bytes):
        """Extraer texto de un PDF simple."""
        file_stream = io.BytesIO(simple_pdf_content)
        
        # Un PDF en blanco puede no tener texto
        text = pdf_service.extract_text_basic(file_stream)
        
        # No debería fallar
        assert isinstance(text, str)
    
    def test_is_pdf_encrypted(self, pdf_service: PdfService, simple_pdf_content: bytes, encrypted_pdf_content: tuple[bytes, str]):
        """Verificar detección de encriptación."""
        # PDF no encriptado
        simple_stream = io.BytesIO(simple_pdf_content)
        assert pdf_service.is_pdf_encrypted(simple_stream) is False
        
        # PDF encriptado
        content, _ = encrypted_pdf_content
        encrypted_stream = io.BytesIO(content)
        assert pdf_service.is_pdf_encrypted(encrypted_stream) is True


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE KEYWORDS DE CRÉDITO
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreditKeywords:
    """Tests para validación de keywords de crédito."""
    
    def test_validate_credit_keywords_match(self, pdf_service: PdfService):
        """Texto con keywords de crédito tiene alta confianza."""
        text = """
        Extracto de Crédito Hipotecario
        Banco: Bancolombia
        Número de crédito: 12345
        Cuota mensual: $1,500,000
        Capital: $200,000,000
        Interés: 12% EA
        Saldo actual: $180,000,000
        Sistema de amortización: UVR
        """
        
        is_valid, confidence = pdf_service.validate_credit_analysis_keywords(text)
        
        assert is_valid is True
        assert confidence >= 0.3
    
    def test_validate_credit_keywords_no_match(self, pdf_service: PdfService):
        """Texto sin keywords de crédito tiene baja confianza."""
        text = """
        Receta de cocina:
        - 2 huevos
        - 1 taza de harina
        - Sal al gusto
        """
        
        is_valid, confidence = pdf_service.validate_credit_analysis_keywords(text)
        
        assert is_valid is False
        assert confidence < 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE FLUJO COMPLETO
# ═══════════════════════════════════════════════════════════════════════════════

class TestProcessPDFUpload:
    """Tests para el flujo completo de upload."""
    
    def test_process_simple_pdf(self, simple_pdf_content: bytes, temp_storage_dir: Path):
        """Procesar un PDF simple sin encriptación."""
        storage = LocalStorageService(base_path=str(temp_storage_dir))
        user_id = str(uuid.uuid4())
        
        validation, save_result = process_pdf_upload(
            file_content=simple_pdf_content,
            original_filename="test.pdf",
            user_id=user_id,
            storage_service=storage
        )
        
        assert validation.is_valid is True
        assert validation.status == PDFStatus.OK
        assert save_result is not None
        assert save_result.success is True
    
    def test_process_encrypted_pdf_without_password(self, encrypted_pdf_content: tuple[bytes, str], temp_storage_dir: Path):
        """Procesar PDF encriptado sin contraseña solicita contraseña."""
        content, _ = encrypted_pdf_content
        storage = LocalStorageService(base_path=str(temp_storage_dir))
        user_id = str(uuid.uuid4())
        
        validation, save_result = process_pdf_upload(
            file_content=content,
            original_filename="encrypted.pdf",
            user_id=user_id,
            storage_service=storage
        )
        
        assert validation.is_valid is True
        assert validation.status == PDFStatus.ENCRYPTED
        assert validation.is_encrypted is True
        assert save_result is None  # No se guardó porque necesita contraseña
    
    def test_process_encrypted_pdf_with_password(self, encrypted_pdf_content: tuple[bytes, str], temp_storage_dir: Path):
        """Procesar PDF encriptado con contraseña correcta."""
        content, password = encrypted_pdf_content
        storage = LocalStorageService(base_path=str(temp_storage_dir))
        user_id = str(uuid.uuid4())
        
        validation, save_result = process_pdf_upload(
            file_content=content,
            original_filename="encrypted.pdf",
            user_id=user_id,
            password=password,
            storage_service=storage
        )
        
        assert validation.is_valid is True
        assert validation.status == PDFStatus.DECRYPTED
        assert save_result is not None
        assert save_result.success is True
        
        # Verificar que el archivo guardado no está encriptado
        saved_content = storage.get_pdf(save_result.file_path)
        pdf_service = PdfService()
        assert pdf_service.is_pdf_encrypted(io.BytesIO(saved_content)) is False
    
    def test_process_encrypted_pdf_with_wrong_password(self, encrypted_pdf_content: tuple[bytes, str], temp_storage_dir: Path):
        """Procesar PDF encriptado con contraseña incorrecta falla."""
        content, _ = encrypted_pdf_content
        storage = LocalStorageService(base_path=str(temp_storage_dir))
        user_id = str(uuid.uuid4())
        
        validation, save_result = process_pdf_upload(
            file_content=content,
            original_filename="encrypted.pdf",
            user_id=user_id,
            password="wrong_password",
            storage_service=storage
        )
        
        assert validation.is_valid is False
        assert validation.status == PDFStatus.INVALID_PASSWORD
        assert save_result is None
