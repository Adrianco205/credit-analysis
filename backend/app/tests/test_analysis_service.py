"""
Tests para Analysis Service y Repositories
==========================================

Tests unitarios para:
- AnalysesRepo: CRUD de análisis
- PropuestasRepo: CRUD de propuestas
- AnalysisService: Orquestación del flujo
"""

import os
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Configurar variables de entorno antes de importar
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "testsecretkey12345678901234567890")
os.environ.setdefault("SMTP_HOST", "smtp.test.com")
os.environ.setdefault("SMTP_USER", "test@test.com")
os.environ.setdefault("SMTP_PASSWORD", "testpassword")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.com")

from app.services.analysis_service import (
    AnalysisService,
    AnalysisCreationResult,
    ProjectionGenerationResult,
    DatosUsuarioInput,
    OpcionAbonoInput,
)
from app.services.gemini_service import ExtractionResult, ExtractionStatus
from app.services.calc_service import (
    DatosCredito,
    ResultadoProyeccion,
    TiempoAhorro,
    crear_calculadora
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_extraction_result():
    """Resultado de extracción exitoso."""
    return ExtractionResult(
        status=ExtractionStatus.SUCCESS,
        confidence=0.92,
        data={
            "nombre_titular": "JUAN CARLOS PÉREZ",
            "numero_credito": "123456789",
            "sistema_amortizacion": "UVR",
            "fecha_desembolso": date(2020, 5, 15),
            "fecha_extracto": date(2024, 1, 15),
            "cuotas_pactadas": 180,
            "cuotas_pagadas": 44,
            "cuotas_pendientes": 136,
            "tasa_interes_cobrada_ea": Decimal("0.0471"),
            "valor_prestado_inicial": Decimal("150000000"),
            "valor_cuota_con_seguros": Decimal("1350000"),
            "saldo_capital_pesos": Decimal("142000000"),
            "beneficio_frech_mensual": Decimal("200000"),
        },
        campos_encontrados=["nombre_titular", "numero_credito", "saldo_capital_pesos"],
        campos_faltantes=[],
        banco_detectado="Bancolombia",
        es_extracto_hipotecario=True
    )


@pytest.fixture
def sample_partial_extraction():
    """Resultado de extracción parcial (faltan campos críticos)."""
    return ExtractionResult(
        status=ExtractionStatus.PARTIAL,
        confidence=0.65,
        data={
            "nombre_titular": "MARÍA GARCÍA",
            "numero_credito": "987654321",
            "saldo_capital_pesos": Decimal("80000000"),
            # Faltan: tasa_interes_cobrada_ea, valor_cuota_con_seguros
        },
        campos_encontrados=["nombre_titular", "saldo_capital_pesos"],
        campos_faltantes=["tasa_interes_cobrada_ea", "valor_cuota_con_seguros", "cuotas_pendientes"],
        banco_detectado="Davivienda",
        es_extracto_hipotecario=True
    )


@pytest.fixture
def sample_datos_usuario():
    """Datos de usuario para crear análisis."""
    return DatosUsuarioInput(
        ingresos_mensuales=Decimal("5000000"),
        capacidad_pago_max=Decimal("2000000"),
        tipo_contrato_laboral="Indefinido"
    )


@pytest.fixture
def sample_opciones_abono():
    """Opciones de abono para proyecciones."""
    return [
        OpcionAbonoInput(numero_opcion=1, abono_adicional_mensual=Decimal("500000"), nombre_opcion="1a Elección"),
        OpcionAbonoInput(numero_opcion=2, abono_adicional_mensual=Decimal("750000"), nombre_opcion="2a Elección"),
        OpcionAbonoInput(numero_opcion=3, abono_adicional_mensual=Decimal("1000000"), nombre_opcion="3a Elección"),
    ]


@pytest.fixture
def sample_datos_credito():
    """Datos de crédito para cálculos."""
    return DatosCredito(
        saldo_capital=Decimal("142000000"),
        valor_cuota_actual=Decimal("1350000"),
        cuotas_pendientes=136,
        tasa_interes_ea=Decimal("0.0471"),
        valor_prestado_inicial=Decimal("150000000"),
        beneficio_frech=Decimal("200000"),
        seguros_mensual=Decimal("150000"),
        sistema_amortizacion="UVR"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE CALC SERVICE (Proyecciones)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalculadoraProyecciones:
    """Tests para el motor de cálculo financiero."""
    
    def test_crear_calculadora(self):
        """Crea calculadora correctamente."""
        calc = crear_calculadora()
        assert calc is not None
    
    def test_tasa_ea_a_mensual(self):
        """Convierte tasa EA a mensual correctamente."""
        calc = crear_calculadora()
        tasa_ea = Decimal("0.12")  # 12% EA
        tasa_mensual = calc.tasa_ea_a_mensual(tasa_ea)
        
        # Debe ser aproximadamente 0.95% mensual
        assert Decimal("0.009") < tasa_mensual < Decimal("0.01")
    
    def test_calcular_cuota_fija(self):
        """Calcula cuota fija para amortización francesa."""
        calc = crear_calculadora()
        
        cuota = calc.calcular_cuota_fija(
            capital=Decimal("100000000"),
            tasa_mensual=Decimal("0.01"),  # 1% mensual
            num_cuotas=180
        )
        
        # Cuota debe ser razonable
        assert Decimal("1000000") < cuota < Decimal("2000000")
    
    def test_calcular_proyeccion_con_abono(self, sample_datos_credito):
        """Calcula proyección con abono extra."""
        calc = crear_calculadora()
        
        resultado = calc.calcular_proyeccion(
            datos=sample_datos_credito,
            abono_extra=Decimal("500000"),
            numero_opcion=1,
            nombre_opcion="Test"
        )
        
        assert isinstance(resultado, ResultadoProyeccion)
        assert resultado.cuotas_nuevas < sample_datos_credito.cuotas_pendientes
        assert resultado.cuotas_reducidas > 0
        assert resultado.valor_ahorrado_intereses > 0
        assert resultado.tiempo_ahorrado.total_meses > 0
    
    def test_calcular_proyeccion_sin_abono(self, sample_datos_credito):
        """Calcular proyección sin abono (baseline)."""
        calc = crear_calculadora()
        
        resultado = calc.calcular_proyeccion(
            datos=sample_datos_credito,
            abono_extra=Decimal("0"),
            numero_opcion=0,
            nombre_opcion="Actual"
        )
        
        # Sin abono, no hay cuotas reducidas
        assert resultado.cuotas_reducidas == 0
        assert resultado.valor_ahorrado_intereses == 0
    
    def test_calcular_honorarios(self):
        """Calcula honorarios (3% del ahorro)."""
        calc = crear_calculadora()
        
        ahorro = Decimal("50000000")
        honorarios = calc.calcular_honorarios(ahorro)
        
        expected = ahorro * Decimal("0.03")
        assert honorarios == expected
    
    def test_calcular_honorarios_minimo(self):
        """Honorarios no bajan del mínimo."""
        calc = crear_calculadora()
        
        # Ahorro muy bajo
        ahorro = Decimal("1000000")  # 3% = $30,000, menor al mínimo
        honorarios = calc.calcular_honorarios(ahorro)
        
        # Debe aplicar tarifa mínima
        assert honorarios >= Decimal("500000")
    
    def test_calcular_honorarios_con_iva(self):
        """Calcula honorarios con IVA (19%)."""
        calc = crear_calculadora()
        
        honorarios = Decimal("1000000")
        total = calc.calcular_honorarios_con_iva(honorarios)
        
        expected = honorarios * Decimal("1.19")
        assert total == expected
    
    def test_calcular_ingreso_minimo(self):
        """Calcula ingreso mínimo (30% de la cuota según Ley 546)."""
        calc = crear_calculadora()
        
        cuota = Decimal("1500000")
        ingreso_minimo = calc.calcular_ingreso_minimo(cuota)
        
        # La cuota debe ser máximo 30% del ingreso
        # Ingreso = cuota / 0.30
        expected = cuota / Decimal("0.30")
        assert ingreso_minimo == expected


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE TIEMPO AHORRADO
# ═══════════════════════════════════════════════════════════════════════════════

class TestTiempoAhorro:
    """Tests para la clase TiempoAhorro."""
    
    def test_desde_meses_exactos(self):
        """Convierte meses exactos a años."""
        tiempo = TiempoAhorro.desde_meses(24)
        
        assert tiempo.anios == 2
        assert tiempo.meses == 0
        assert tiempo.total_meses == 24
    
    def test_desde_meses_con_resto(self):
        """Convierte meses con resto."""
        tiempo = TiempoAhorro.desde_meses(38)
        
        assert tiempo.anios == 3
        assert tiempo.meses == 2
        assert tiempo.total_meses == 38
    
    def test_desde_meses_solo_meses(self):
        """Convierte pocos meses."""
        tiempo = TiempoAhorro.desde_meses(5)
        
        assert tiempo.anios == 0
        assert tiempo.meses == 5
    
    def test_str_representation(self):
        """Representación en string."""
        tiempo = TiempoAhorro(anios=5, meses=3)
        
        assert str(tiempo) == "5 años, 3 meses"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataclasses:
    """Tests para dataclasses de entrada."""
    
    def test_datos_usuario_input(self):
        """Crea DatosUsuarioInput correctamente."""
        datos = DatosUsuarioInput(
            ingresos_mensuales=Decimal("5000000"),
            capacidad_pago_max=Decimal("2000000"),
            tipo_contrato_laboral="Indefinido"
        )
        
        assert datos.ingresos_mensuales == Decimal("5000000")
        assert datos.capacidad_pago_max == Decimal("2000000")
    
    def test_datos_usuario_input_opcionales(self):
        """DatosUsuarioInput con campos opcionales."""
        datos = DatosUsuarioInput(
            ingresos_mensuales=Decimal("3000000")
        )
        
        assert datos.capacidad_pago_max is None
        assert datos.tipo_contrato_laboral is None
    
    def test_opcion_abono_input(self):
        """Crea OpcionAbonoInput correctamente."""
        opcion = OpcionAbonoInput(
            numero_opcion=1,
            abono_adicional_mensual=Decimal("500000"),
            nombre_opcion="Primera Opción"
        )
        
        assert opcion.numero_opcion == 1
        assert opcion.abono_adicional_mensual == Decimal("500000")
        assert opcion.nombre_opcion == "Primera Opción"
    
    def test_datos_credito(self, sample_datos_credito):
        """Crea DatosCredito correctamente."""
        assert sample_datos_credito.saldo_capital == Decimal("142000000")
        assert sample_datos_credito.tasa_interes_ea == Decimal("0.0471")
        assert sample_datos_credito.sistema_amortizacion == "UVR"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE EXTRACTION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractionResult:
    """Tests para resultados de extracción."""
    
    def test_extraction_success(self, sample_extraction_result):
        """Extracción exitosa tiene datos completos."""
        assert sample_extraction_result.status == ExtractionStatus.SUCCESS
        assert sample_extraction_result.confidence >= 0.9
        assert sample_extraction_result.es_extracto_hipotecario is True
        assert "nombre_titular" in sample_extraction_result.data
    
    def test_extraction_partial(self, sample_partial_extraction):
        """Extracción parcial tiene campos faltantes."""
        assert sample_partial_extraction.status == ExtractionStatus.PARTIAL
        assert len(sample_partial_extraction.campos_faltantes) > 0
        assert "tasa_interes_cobrada_ea" in sample_partial_extraction.campos_faltantes


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE ANÁLISIS SERVICE (Lógica de negocio)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalysisServiceLogic:
    """Tests para la lógica del servicio de análisis."""
    
    def test_check_requires_manual_input_complete(self):
        """No requiere input manual si datos están completos."""
        extracted_data = {
            "saldo_capital_pesos": Decimal("100000000"),
            "valor_cuota_con_seguros": Decimal("1200000"),
            "cuotas_pendientes": 120,
            "tasa_interes_cobrada_ea": Decimal("0.05")
        }
        campos_faltantes = []
        
        # Crear servicio mock
        service = MagicMock(spec=AnalysisService)
        service._check_requires_manual_input = AnalysisService._check_requires_manual_input
        
        result = service._check_requires_manual_input(
            service, extracted_data, campos_faltantes
        )
        
        assert result is False
    
    def test_check_requires_manual_input_missing_critical(self):
        """Requiere input manual si falta campo crítico."""
        extracted_data = {
            "saldo_capital_pesos": Decimal("100000000"),
            # Falta: valor_cuota_con_seguros, cuotas_pendientes, tasa
        }
        campos_faltantes = ["valor_cuota_con_seguros", "cuotas_pendientes", "tasa_interes_cobrada_ea"]
        
        service = MagicMock(spec=AnalysisService)
        service._check_requires_manual_input = AnalysisService._check_requires_manual_input
        
        result = service._check_requires_manual_input(
            service, extracted_data, campos_faltantes
        )
        
        assert result is True
    
    def test_build_user_full_name(self):
        """Construye nombre completo del usuario."""
        # Mock usuario
        usuario = MagicMock()
        usuario.nombres = "Juan Carlos"
        usuario.primer_apellido = "Pérez"
        usuario.segundo_apellido = "García"
        
        service = MagicMock(spec=AnalysisService)
        service._build_user_full_name = AnalysisService._build_user_full_name
        
        nombre = service._build_user_full_name(service, usuario)
        
        assert nombre == "Juan Carlos Pérez García"
    
    def test_build_user_full_name_partial(self):
        """Construye nombre con apellidos faltantes."""
        usuario = MagicMock()
        usuario.nombres = "María"
        usuario.primer_apellido = "López"
        usuario.segundo_apellido = None
        
        service = MagicMock(spec=AnalysisService)
        service._build_user_full_name = AnalysisService._build_user_full_name
        
        nombre = service._build_user_full_name(service, usuario)
        
        assert nombre == "María López"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE RESULT DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TestResultDataclasses:
    """Tests para dataclasses de resultado."""
    
    def test_analysis_creation_result_success(self):
        """AnalysisCreationResult exitoso."""
        result = AnalysisCreationResult(
            success=True,
            analisis=MagicMock(),
            requires_manual_input=False
        )
        
        assert result.success is True
        assert result.error_code is None
        assert result.name_mismatch is False
    
    def test_analysis_creation_result_error(self):
        """AnalysisCreationResult con error."""
        result = AnalysisCreationResult(
            success=False,
            error_code="DOCUMENT_NOT_FOUND",
            error_message="Documento no encontrado"
        )
        
        assert result.success is False
        assert result.error_code == "DOCUMENT_NOT_FOUND"
        assert result.analisis is None
    
    def test_analysis_creation_result_name_mismatch(self):
        """AnalysisCreationResult con nombre no coincidente."""
        result = AnalysisCreationResult(
            success=True,
            analisis=MagicMock(),
            name_mismatch=True
        )
        
        assert result.success is True
        assert result.name_mismatch is True
    
    def test_projection_generation_result_success(self):
        """ProjectionGenerationResult exitoso."""
        propuestas = [MagicMock(), MagicMock(), MagicMock()]
        result = ProjectionGenerationResult(
            success=True,
            propuestas=propuestas
        )
        
        assert result.success is True
        assert len(result.propuestas) == 3
    
    def test_projection_generation_result_error(self):
        """ProjectionGenerationResult con error."""
        result = ProjectionGenerationResult(
            success=False,
            error_message="El análisis no está validado"
        )
        
        assert result.success is False
        assert "validado" in result.error_message
