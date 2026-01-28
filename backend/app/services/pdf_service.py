import hashlib
import logging
from pathlib import Path
from typing import BinaryIO, Tuple
import PyPDF2

logger = logging.getLogger(__name__)


class PdfService:
    """
    Servicio para manejo de archivos PDF.
    Incluye detección de encriptación y preparación para extracción con IA.
    """
    
    @staticmethod
    def is_pdf_encrypted(file_stream: BinaryIO) -> bool:
        """
        Detecta si un PDF está protegido con contraseña.
        
        Args:
            file_stream: Stream del archivo PDF
            
        Returns:
            bool: True si el PDF está encriptado, False en caso contrario
        """
        try:
            # Resetear el cursor al inicio
            file_stream.seek(0)
            
            # Intentar leer el PDF
            reader = PyPDF2.PdfReader(file_stream)
            
            # PyPDF2 detecta automáticamente si está encriptado
            is_encrypted = reader.is_encrypted
            
            # Resetear cursor para uso posterior
            file_stream.seek(0)
            
            return is_encrypted
            
        except Exception as e:
            logger.error(f"Error al verificar encriptación del PDF: {str(e)}")
            file_stream.seek(0)
            return False
    
    @staticmethod
    def decrypt_pdf(file_stream: BinaryIO, password: str) -> Tuple[bool, str]:
        """
        Intenta desencriptar un PDF con la contraseña proporcionada.
        
        Args:
            file_stream: Stream del archivo PDF
            password: Contraseña para desencriptar
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            file_stream.seek(0)
            reader = PyPDF2.PdfReader(file_stream)
            
            if not reader.is_encrypted:
                return True, "El PDF no está encriptado"
            
            # Intentar desencriptar
            if reader.decrypt(password):
                # Verificar que realmente se puede leer
                try:
                    _ = len(reader.pages)
                    file_stream.seek(0)
                    return True, "PDF desencriptado exitosamente"
                except Exception as e:
                    logger.warning(f"PDF desencriptado pero no se puede leer: {str(e)}")
                    file_stream.seek(0)
                    return False, "Contraseña incorrecta o PDF corrupto"
            else:
                file_stream.seek(0)
                return False, "Contraseña incorrecta"
                
        except Exception as e:
            logger.error(f"Error al desencriptar PDF: {str(e)}")
            file_stream.seek(0)
            return False, f"Error al procesar el PDF: {str(e)}"
    
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
        Extrae texto básico del PDF usando PyPDF2.
        Útil para validación rápida antes de enviar a Gemini.
        
        Args:
            file_stream: Stream del archivo PDF
            password: Contraseña si el PDF está protegido
            
        Returns:
            str: Texto extraído del PDF
        """
        try:
            file_stream.seek(0)
            reader = PyPDF2.PdfReader(file_stream)
            
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
