"""
Schemas Pydantic para Análisis Hipotecario.
Incluye DTOs para entrada, salida y el Resumen de 4 bloques.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SistemaAmortizacion(str, Enum):
    UVR = "UVR"
    PESOS = "PESOS"
    MIXTO = "MIXTO"


class AnalisisStatus(str, Enum):
    PENDING_EXTRACTION = "PENDING_EXTRACTION"  # PDF subido, esperando Gemini
    EXTRACTED = "EXTRACTED"                    # Datos extraídos, pendiente validación
    PENDING_MANUAL = "PENDING_MANUAL"          # Requiere datos manuales del usuario
    PENDING_PROJECTION = "PENDING_PROJECTION"  # Diagnóstico listo, esperando proyecciones admin
    VALIDATED = "VALIDATED"                    # Listo para generar propuestas
    PROJECTED = "PROJECTED"                    # Proyecciones generadas, propuesta lista
    NAME_MISMATCH = "NAME_MISMATCH"            # Nombre no coincide
    ID_MISMATCH = "ID_MISMATCH"                # NUEVO: Cédula no coincide (alerta crítica)
    INVALID_DOCUMENT = "INVALID_DOCUMENT"      # NUEVO: Documento no es extracto hipotecario
    ERROR = "ERROR"                            # Error en procesamiento


# ═══════════════════════════════════════════════════════════════════════════════
# INPUTS - Lo que envía el usuario
# ═══════════════════════════════════════════════════════════════════════════════

class DatosUsuarioInput(BaseModel):
    """Datos socioeconómicos que proporciona el usuario al subir el PDF"""
    ingresos_mensuales: Decimal = Field(..., gt=0, description="Ingresos mensuales en COP")
    capacidad_pago_max: Decimal | None = Field(None, gt=0, description="Máximo que puede pagar mensualmente")
    tipo_contrato_laboral: str | None = Field(None, max_length=80)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class DatosExtractoManualInput(BaseModel):
    """
    Campos que el usuario puede llenar si Gemini no los detectó.
    Solo se permiten llenar los campos que NO fueron extraídos automáticamente.
    """
    numero_credito: str | None = Field(None, max_length=50)
    sistema_amortizacion: SistemaAmortizacion | None = None
    valor_prestado_inicial: Decimal | None = Field(None, gt=0)
    fecha_desembolso: date | None = None
    
    cuotas_pactadas: int | None = Field(None, gt=0, le=600)
    cuotas_pagadas: int | None = Field(None, ge=0)
    
    tasa_interes_pactada_ea: Decimal | None = Field(None, ge=0, le=1, description="Tasa como decimal: 9.53% = 0.0953")
    tasa_interes_cobrada_ea: Decimal | None = Field(None, ge=0, le=1)
    
    valor_cuota_con_seguros: Decimal | None = Field(None, gt=0)
    beneficio_frech_mensual: Decimal | None = Field(None, ge=0)
    saldo_capital_pesos: Decimal | None = Field(None, gt=0)
    
    # UVR
    saldo_capital_uvr: Decimal | None = Field(None, gt=0)
    valor_uvr_fecha_extracto: Decimal | None = Field(None, gt=0)
    
    # Seguros
    seguro_vida: Decimal | None = Field(None, ge=0)
    seguro_incendio: Decimal | None = Field(None, ge=0)
    seguro_terremoto: Decimal | None = Field(None, ge=0)


class AnalisisCreateInput(BaseModel):
    """Input completo para crear un análisis (PDF + datos usuario)"""
    documento_id: UUID
    datos_usuario: DatosUsuarioInput
    banco_id: int | None = None  # Si el usuario conoce el banco
    password_pdf: str | None = Field(None, description="Contraseña del PDF si está encriptado")


class AnalisisUpdateManualInput(BaseModel):
    """Para actualizar campos manuales después de la extracción"""
    datos_manuales: DatosExtractoManualInput


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS - Respuestas de la API
# ═══════════════════════════════════════════════════════════════════════════════

class DatosBasicosResumen(BaseModel):
    """Bloque 1: DATOS BÁSICOS del resumen"""
    valor_prestado: Decimal
    cuotas_pactadas: int
    cuotas_pagadas: int
    cuotas_por_pagar: int
    cuota_actual_aprox: Decimal
    beneficio_frech: Decimal
    cuota_completa_aprox: Decimal  # Sin subsidio
    total_pagado_fecha: Decimal
    total_frech_recibido: Decimal
    monto_real_pagado_banco: Decimal


class LimitesBancoResumen(BaseModel):
    """
    Bloque 2: LÍMITES CON EL BANCO HOY
    
    MEJORA 3: El campo 'abono_adicional_cuota' siempre viene en None/blanco
    para representar la "foto actual" sin intervención del administrador.
    """
    valor_prestado: Decimal
    saldo_actual_credito: Decimal
    # MEJORA 3: Campo vacío por diseño - representa estado actual sin abono extra
    abono_adicional_cuota: Decimal | None = None  # Siempre NULL en diagnóstico inicial


class AjusteInflacionResumen(BaseModel):
    """Bloque 3: AJUSTE POR INFLACIÓN (Solo para créditos UVR)"""
    ajuste_pesos: Decimal  # Diferencia saldo actual - valor prestado
    porcentaje_ajuste: Decimal  # -24.05% significa que subió 24%


class CostosExtraResumen(BaseModel):
    """Bloque 4: INTERESES Y SEGUROS"""
    total_intereses_seguros: Decimal  # Lo que no abona a capital


class ResumenCreditoResponse(BaseModel):
    """
    Respuesta completa del resumen del crédito.
    Agrupa los 4 bloques visuales de la UI.
    """
    # Metadata
    analisis_id: UUID
    numero_credito: str | None
    nombre_titular: str | None
    banco_nombre: str | None
    sistema_amortizacion: str | None
    fecha_extracto: date | None
    
    # Los 4 bloques
    datos_basicos: DatosBasicosResumen
    limites_banco: LimitesBancoResumen
    ajuste_inflacion: AjusteInflacionResumen | None  # None si no es UVR
    costos_extra: CostosExtraResumen
    
    # Tasas (información adicional)
    tasa_cobrada_con_frech: Decimal | None  # Ej: 4.71% EA
    seguros_actuales_mensual: Decimal | None


class DatosExtractoResponse(BaseModel):
    """Todos los datos extraídos del PDF"""
    # Identificación
    nombre_titular_extracto: str | None
    numero_credito: str | None
    banco_nombre: str | None
    sistema_amortizacion: str | None
    plan_credito: str | None
    
    # Fechas y plazos
    fecha_desembolso: date | None
    fecha_extracto: date | None
    plazo_total_meses: int | None
    
    # Cuotas
    cuotas_pactadas: int | None
    cuotas_pagadas: int | None
    cuotas_pendientes: int | None
    cuotas_vencidas: int | None
    
    # Tasas
    tasa_interes_pactada_ea: Decimal | None
    tasa_interes_cobrada_ea: Decimal | None
    tasa_interes_subsidiada_ea: Decimal | None
    tasa_mora_pactada_ea: Decimal | None
    
    # Montos
    valor_prestado_inicial: Decimal | None
    valor_cuota_sin_seguros: Decimal | None
    valor_cuota_con_seguros: Decimal | None
    beneficio_frech_mensual: Decimal | None
    valor_cuota_con_subsidio: Decimal | None
    saldo_capital_pesos: Decimal | None
    total_por_pagar: Decimal | None
    
    # UVR
    saldo_capital_uvr: Decimal | None
    valor_uvr_fecha_extracto: Decimal | None
    valor_cuota_uvr: Decimal | None
    
    # Seguros
    seguro_vida: Decimal | None
    seguro_incendio: Decimal | None
    seguro_terremoto: Decimal | None
    seguros_total_mensual: Decimal | None
    
    # Campos que requieren input manual
    campos_faltantes: list[str] | None = None


class AnalisisResponse(BaseModel):
    """Respuesta completa de un análisis"""
    id: UUID
    documento_id: UUID
    usuario_id: UUID
    status: AnalisisStatus
    
    # Validaciones
    nombre_coincide: bool | None
    es_extracto_hipotecario: bool
    
    # Datos extraídos
    datos_extracto: DatosExtractoResponse
    
    # Datos del usuario
    ingresos_mensuales: Decimal | None
    capacidad_pago_max: Decimal | None
    tipo_contrato_laboral: str | None
    
    # Campos manuales
    campos_manuales: list[str] | None
    
    model_config = ConfigDict(from_attributes=True)


class AnalisisListItem(BaseModel):
    """Item para listados de análisis"""
    id: UUID
    numero_credito: str | None
    banco_nombre: str | None
    saldo_capital_pesos: Decimal | None
    status: AnalisisStatus
    fecha_extracto: date | None
    created_at: date | None
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSES PARA GEMINI
# ═══════════════════════════════════════════════════════════════════════════════

class GeminiExtractionResult(BaseModel):
    """Estructura esperada de la respuesta de Gemini"""
    extraction_success: bool
    confidence_score: float = Field(ge=0, le=1)
    
    # Datos extraídos
    nombre_titular_extracto: str | None = None
    numero_credito: str | None = None
    banco_detectado: str | None = None
    sistema_amortizacion: str | None = None
    
    valor_prestado_inicial: Decimal | None = None
    fecha_desembolso: str | None = None  # Gemini retorna string, se parsea después
    
    cuotas_pactadas: int | None = None
    cuotas_pagadas: int | None = None
    cuotas_pendientes: int | None = None
    
    tasa_interes_pactada: Decimal | None = None
    tasa_interes_cobrada: Decimal | None = None
    
    valor_cuota_actual: Decimal | None = None
    beneficio_frech: Decimal | None = None
    saldo_capital: Decimal | None = None
    
    saldo_uvr: Decimal | None = None
    valor_uvr: Decimal | None = None
    
    seguros: dict | None = None  # {"vida": X, "incendio": Y, "terremoto": Z}
    
    # Validaciones
    es_extracto_hipotecario: bool = True
    campos_no_encontrados: list[str] | None = None
    mensaje_error: str | None = None
