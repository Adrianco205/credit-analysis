"""
Tests para Gemini Service - Extracción de datos de PDFs
=======================================================

Tests unitarios para:
- Normalización de datos extraídos
- Comparación de nombres
- Parseo de respuestas JSON
- Mapeo a modelo de análisis
"""

import json
import os
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Configurar variables de entorno mínimas para tests
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "testsecretkey12345678901234567890")
os.environ.setdefault("SMTP_HOST", "smtp.test.com")
os.environ.setdefault("SMTP_USER", "test@test.com")
os.environ.setdefault("SMTP_PASSWORD", "testpassword")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.com")

from app.services.gemini_service import (
    ExtractionResult,
    ExtractionStatus,
    GeminiService,
    NameComparisonResult,
    map_extraction_to_analysis,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def gemini_service():
    """Servicio sin API key configurada (para tests unitarios)."""
    return GeminiService(api_key=None)


@pytest.fixture
def sample_gemini_response():
    """Respuesta de ejemplo de Gemini."""
    return json.dumps({
        "es_extracto_hipotecario": True,
        "confianza_extraccion": 0.92,
        "banco_detectado": "Bancolombia",
        "sistema_amortizacion": "UVR",
        
        "nombre_titular": "JUAN CARLOS PÉREZ GARCÍA",
        "numero_credito": "123456789012",
        "plan_credito": "VIS",
        
        "fecha_desembolso": "2020-05-15",
        "fecha_extracto": "2024-01-15",
        "plazo_total_meses": 180,
        
        "cuotas_pactadas": 180,
        "cuotas_pagadas": 44,
        "cuotas_pendientes": 136,
        "cuotas_vencidas": 0,
        
        "tasa_interes_pactada_ea": 9.53,
        "tasa_interes_cobrada_ea": 9.53,
        "tasa_interes_subsidiada_ea": 4.71,
        
        "valor_prestado_inicial": 150000000,
        "valor_cuota_con_seguros": 1350000,
        "beneficio_frech_mensual": 200000,
        "saldo_capital_pesos": 142000000,
        
        "saldo_capital_uvr": 350000,
        "valor_uvr_fecha_extracto": 405.72,
        
        "seguro_vida": 85000,
        "seguro_incendio": 45000,
        "seguro_terremoto": 25000,
        
        "campos_no_encontrados": ["tasa_mora_ea", "intereses_mora"],
        "notas": "Extracto completo de Bancolombia"
    })


@pytest.fixture
def sample_non_credit_response():
    """Respuesta cuando el documento no es un extracto de crédito."""
    return json.dumps({
        "es_extracto_hipotecario": False,
        "tipo_documento_detectado": "Factura de servicios públicos"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE NORMALIZACIÓN DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataNormalization:
    """Tests para normalización de datos extraídos."""
    
    def test_normalize_text_fields(self, gemini_service):
        """Normaliza campos de texto correctamente."""
        data = {
            "nombre_titular": "  JUAN PÉREZ  ",
            "numero_credito": "12345",
            "sistema_amortizacion": "UVR"
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        assert normalized["nombre_titular"] == "JUAN PÉREZ"
        assert normalized["numero_credito"] == "12345"
        assert normalized["sistema_amortizacion"] == "UVR"
    
    def test_normalize_date_fields(self, gemini_service):
        """Normaliza campos de fecha correctamente."""
        data = {
            "fecha_desembolso": "2020-05-15",
            "fecha_extracto": "2024-01-15"
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        assert normalized["fecha_desembolso"] == date(2020, 5, 15)
        assert normalized["fecha_extracto"] == date(2024, 1, 15)
    
    def test_normalize_integer_fields(self, gemini_service):
        """Normaliza campos enteros correctamente."""
        data = {
            "cuotas_pactadas": 180,
            "cuotas_pagadas": "44",
            "cuotas_pendientes": 136.0
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        assert normalized["cuotas_pactadas"] == 180
        assert normalized["cuotas_pagadas"] == 44
        assert normalized["cuotas_pendientes"] == 136
    
    def test_normalize_decimal_fields(self, gemini_service):
        """Normaliza campos decimales (montos) correctamente."""
        data = {
            "valor_prestado_inicial": 150000000,
            "saldo_capital_pesos": "142000000",
            "beneficio_frech_mensual": 200000.50
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        assert normalized["valor_prestado_inicial"] == Decimal("150000000")
        assert normalized["saldo_capital_pesos"] == Decimal("142000000")
        assert normalized["beneficio_frech_mensual"] == Decimal("200000.50")
    
    def test_normalize_percentage_to_decimal(self, gemini_service):
        """Convierte tasas de porcentaje (ej: 9.53) a decimal (0.0953)."""
        data = {
            "tasa_interes_pactada_ea": 9.53,
            "tasa_interes_cobrada_ea": "12.5",
            "tasa_interes_subsidiada_ea": 4.71
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        # Las tasas mayores a 1 se convierten a decimal
        assert normalized["tasa_interes_pactada_ea"] == Decimal("0.0953")
        assert normalized["tasa_interes_cobrada_ea"] == Decimal("0.125")
        assert normalized["tasa_interes_subsidiada_ea"] == Decimal("0.0471")
    
    def test_normalize_already_decimal_rate(self, gemini_service):
        """No modifica tasas que ya son decimales (menores a 1)."""
        data = {
            "tasa_interes_pactada_ea": 0.0953,
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        assert normalized["tasa_interes_pactada_ea"] == Decimal("0.0953")
    
    def test_handle_invalid_date(self, gemini_service):
        """Maneja fechas inválidas sin fallar."""
        data = {
            "fecha_desembolso": "fecha-invalida",
            "fecha_extracto": "2024-13-45"  # Mes/día inválidos
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        # No debe incluir campos con fechas inválidas
        assert "fecha_desembolso" not in normalized
        assert "fecha_extracto" not in normalized
    
    def test_handle_empty_values(self, gemini_service):
        """Maneja valores vacíos correctamente."""
        data = {
            "nombre_titular": "",
            "numero_credito": None,
            "cuotas_pactadas": None
        }
        
        normalized = gemini_service._normalize_extracted_data(data)
        
        # No debe incluir campos vacíos
        assert "nombre_titular" not in normalized
        assert "numero_credito" not in normalized
        assert "cuotas_pactadas" not in normalized


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE PARSEO DE RESPUESTAS
# ═══════════════════════════════════════════════════════════════════════════════

class TestResponseParsing:
    """Tests para parseo de respuestas de Gemini."""
    
    def test_parse_valid_response(self, gemini_service, sample_gemini_response):
        """Parsea respuesta válida de Gemini."""
        result = gemini_service._parse_extraction_response(sample_gemini_response)
        
        assert result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL]
        assert result.confidence == 0.92
        assert result.banco_detectado == "Bancolombia"
        assert result.es_extracto_hipotecario is True
        assert "nombre_titular" in result.campos_encontrados
        assert "tasa_mora_ea" in result.campos_faltantes
    
    def test_parse_markdown_wrapped_json(self, gemini_service):
        """Parsea JSON envuelto en bloques de código markdown."""
        markdown_response = """```json
        {
            "es_extracto_hipotecario": true,
            "confianza_extraccion": 0.85,
            "nombre_titular": "TEST USER",
            "campos_no_encontrados": []
        }
        ```"""
        
        result = gemini_service._parse_extraction_response(markdown_response)
        
        assert result.status == ExtractionStatus.SUCCESS
        assert result.data.get("nombre_titular") == "TEST USER"
    
    def test_parse_non_credit_document(self, gemini_service, sample_non_credit_response):
        """Detecta documentos que no son extractos de crédito."""
        result = gemini_service._parse_extraction_response(sample_non_credit_response)
        
        assert result.status == ExtractionStatus.NOT_CREDIT_DOCUMENT
        assert result.es_extracto_hipotecario is False
        assert "Factura" in result.message
    
    def test_parse_invalid_json(self, gemini_service):
        """Maneja JSON inválido graciosamente."""
        invalid_response = "Este no es un JSON válido { incompleto"
        
        result = gemini_service._parse_extraction_response(invalid_response)
        
        assert result.status == ExtractionStatus.API_ERROR
        assert "Error parseando" in result.message


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE COMPARACIÓN DE NOMBRES
# ═══════════════════════════════════════════════════════════════════════════════

class TestNameComparison:
    """Tests para comparación inteligente de nombres."""
    
    def test_exact_match(self, gemini_service):
        """Nombres idénticos coinciden."""
        result = gemini_service._simple_name_comparison(
            "JUAN CARLOS PÉREZ",
            "JUAN CARLOS PÉREZ"
        )
        
        assert result.match is True
        assert result.similarity == 1.0
    
    def test_match_different_order(self, gemini_service):
        """Nombres en diferente orden coinciden."""
        result = gemini_service._simple_name_comparison(
            "PÉREZ GARCÍA JUAN CARLOS",
            "JUAN CARLOS PÉREZ GARCÍA"
        )
        
        assert result.match is True
        assert result.similarity >= 0.7
    
    def test_match_without_accents(self, gemini_service):
        """Nombres con y sin tildes coinciden."""
        result = gemini_service._simple_name_comparison(
            "JUAN CARLOS PEREZ GARCIA",
            "JUAN CARLOS PÉREZ GARCÍA"
        )
        
        assert result.match is True
        assert result.similarity == 1.0
    
    def test_match_partial_name(self, gemini_service):
        """Nombre parcial está contenido en el completo."""
        result = gemini_service._simple_name_comparison(
            "JUAN CARLOS PÉREZ GARCÍA MARTÍNEZ",
            "JUAN PÉREZ"
        )
        
        # El nombre corto debe estar contenido en el largo
        assert result.match is True
    
    def test_no_match_different_names(self, gemini_service):
        """Nombres completamente diferentes no coinciden."""
        result = gemini_service._simple_name_comparison(
            "JUAN CARLOS PÉREZ",
            "MARÍA FERNANDA GÓMEZ"
        )
        
        assert result.match is False
        assert result.similarity < 0.3
    
    def test_ignore_connectors(self, gemini_service):
        """Ignora conectores como 'de', 'del', 'la'."""
        result = gemini_service._simple_name_comparison(
            "MARÍA DE LOS ÁNGELES GARCÍA",
            "MARIA ANGELES GARCIA"
        )
        
        assert result.match is True
    
    def test_handle_empty_name(self, gemini_service):
        """Maneja nombres vacíos."""
        result = gemini_service._simple_name_comparison("", "JUAN PÉREZ")
        
        assert result.match is False
        assert result.similarity == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MAPEO A ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMapToAnalysis:
    """Tests para mapeo de extracción a modelo de análisis."""
    
    def test_map_basic_fields(self):
        """Mapea campos básicos correctamente."""
        extraction = ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            confidence=0.9,
            data={
                "nombre_titular": "JUAN PÉREZ",
                "numero_credito": "12345",
                "sistema_amortizacion": "UVR",
                "valor_prestado_inicial": Decimal("150000000"),
                "cuotas_pactadas": 180
            },
            banco_detectado="Bancolombia",
            campos_encontrados=["nombre_titular", "numero_credito"],
            campos_faltantes=["tasa_mora_ea"]
        )
        
        result = map_extraction_to_analysis(
            extraction,
            "doc-123",
            "user-456"
        )
        
        assert result["documento_id"] == "doc-123"
        assert result["usuario_id"] == "user-456"
        assert result["nombre_titular_extracto"] == "JUAN PÉREZ"
        assert result["numero_credito"] == "12345"
        assert result["banco_detectado"] == "Bancolombia"
        assert result["valor_prestado_inicial"] == Decimal("150000000")
        assert result["gemini_extraction_confidence"] == 0.9
    
    def test_map_handles_missing_fields(self):
        """Mapea campos faltantes como None."""
        extraction = ExtractionResult(
            status=ExtractionStatus.PARTIAL,
            confidence=0.5,
            data={
                "nombre_titular": "JUAN"
            },
            campos_encontrados=["nombre_titular"],
            campos_faltantes=["saldo_capital_pesos"]
        )
        
        result = map_extraction_to_analysis(extraction, "doc", "user")
        
        assert result["saldo_capital_pesos"] is None
        assert result["tasa_interes_pactada_ea"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE CONFIGURACIÓN DEL SERVICIO
# ═══════════════════════════════════════════════════════════════════════════════

class TestServiceConfiguration:
    """Tests para configuración del servicio."""
    
    def test_service_not_configured_without_api_key(self):
        """Servicio no está configurado sin API key."""
        service = GeminiService(api_key=None)
        
        assert service.is_configured is False
    
    def test_service_configured_with_api_key(self):
        """Servicio se configura con API key."""
        # Mock la configuración de genai
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = MagicMock()
            
            service = GeminiService(api_key="test-api-key")
            
            assert service.is_configured is True
            mock_genai.configure.assert_called_once_with(api_key="test-api-key")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ASYNC DE EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncExtraction:
    """Tests async para extracción de datos."""
    
    @pytest.mark.asyncio
    async def test_extract_without_config_returns_error(self):
        """Extracción sin configuración retorna error."""
        service = GeminiService(api_key=None)
        
        result = await service.extract_credit_data(b"fake pdf content")
        
        assert result.status == ExtractionStatus.API_ERROR
        assert "no está configurada" in result.message
    
    @pytest.mark.asyncio
    async def test_extract_with_mocked_api(self, sample_gemini_response):
        """Extracción con API mockeada funciona."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            # Configurar mock
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = sample_gemini_response
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService(api_key="test-key")
            result = await service.extract_credit_data(b"fake pdf")
            
            assert result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL]
            assert result.banco_detectado == "Bancolombia"
            assert result.confidence == 0.92
    
    @pytest.mark.asyncio
    async def test_compare_names_with_mocked_api(self):
        """Comparación de nombres con API mockeada."""
        comparison_response = json.dumps({
            "match": True,
            "similarity": 0.95,
            "explanation": "Los nombres coinciden con alta similitud"
        })
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = comparison_response
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService(api_key="test-key")
            result = await service.compare_names("JUAN PÉREZ", "Juan Perez")
            
            assert result.match is True
            assert result.similarity == 0.95
