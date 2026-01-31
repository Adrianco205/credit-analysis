"""
Schemas Pydantic para Propuestas de Ahorro (Nuevas Oportunidades).
Incluye DTOs para las 3 opciones de abono y cálculos de proyección.
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Literal
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

PORCENTAJE_HONORARIOS = Decimal("0.03")  # 3% del ahorro
PORCENTAJE_IVA = Decimal("0.19")  # 19% IVA Colombia
TARIFA_MINIMA_HONORARIOS = Decimal("500000")  # $500,000 COP mínimo
PORCENTAJE_INGRESO_MINIMO = Decimal("0.30")  # 30% de la cuota (Ley 546/99)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class OrigenPropuesta(str, Enum):
    USER = "USER"    # Propuesta inicial del usuario
    ADMIN = "ADMIN"  # Ajustada por administrador


# ═══════════════════════════════════════════════════════════════════════════════
# INPUTS - Lo que envía el usuario
# ═══════════════════════════════════════════════════════════════════════════════

class OpcionAbonoInput(BaseModel):
    """Una opción de abono adicional definida por el usuario"""
    numero_opcion: int = Field(..., ge=1, le=10, description="Número de opción (1, 2, 3...)")
    abono_adicional_mensual: Decimal = Field(..., gt=0, description="Abono extra mensual en COP")
    nombre_opcion: str | None = Field(None, max_length=50, description="Ej: '1a Elección'")


class GenerarProyeccionesInput(BaseModel):
    """
    Input para generar las proyecciones de un análisis.
    El usuario define las 3 opciones de abono según su capacidad.
    """
    analisis_id: UUID
    opciones: list[OpcionAbonoInput] = Field(
        ..., 
        min_length=1, 
        max_length=5,
        description="Lista de opciones de abono (típicamente 3)"
    )
    
    # Opcional: Admin puede ajustar estos valores
    ingresos_mensuales_override: Decimal | None = Field(None, gt=0)


class RecalcularPropuestaInput(BaseModel):
    """Input para que el Admin recalcule una propuesta específica"""
    propuesta_id: UUID
    nuevo_abono_adicional: Decimal = Field(..., gt=0)
    origen: OrigenPropuesta = OrigenPropuesta.ADMIN


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS - Respuestas de la API
# ═══════════════════════════════════════════════════════════════════════════════

class TiempoAhorrado(BaseModel):
    """Estructura para tiempo ahorrado/restante"""
    anios: int
    meses: int
    
    @computed_field
    @property
    def total_meses(self) -> int:
        return (self.anios * 12) + self.meses
    
    @computed_field
    @property
    def descripcion(self) -> str:
        """Ej: '16 años, 8 meses' o '11 años, 8 meses'"""
        return f"{self.anios} años, {self.meses} meses"


class ProyeccionOpcionResponse(BaseModel):
    """
    Respuesta de una opción calculada.
    Corresponde a una columna de "Nuevas Oportunidades".
    """
    id: UUID | None = None
    numero_opcion: int
    nombre_opcion: str | None
    
    # Entrada
    abono_adicional_mensual: Decimal
    
    # ═══════════════════════════════════════════════════════════════════
    # RESULTADOS PRINCIPALES (Lo que se muestra en la tabla)
    # ═══════════════════════════════════════════════════════════════════
    
    # Tiempo restante con esta opción
    cuotas_nuevas: int
    tiempo_restante: TiempoAhorrado
    
    # Dinero
    nuevo_valor_cuota: Decimal  # Cuota actual + Abono adicional
    total_por_pagar_aprox: Decimal
    
    # Ahorro
    cuotas_reducidas: int
    tiempo_ahorrado: TiempoAhorrado
    valor_ahorrado_intereses: Decimal
    
    # Veces pagado
    veces_pagado: Decimal  # 1.95, 1.83, 1.72
    
    # ═══════════════════════════════════════════════════════════════════
    # HONORARIOS Y REQUISITOS
    # ═══════════════════════════════════════════════════════════════════
    honorarios_calculados: Decimal  # 3% del ahorro
    honorarios_con_iva: Decimal     # Honorarios + 19%
    ingreso_minimo_requerido: Decimal  # 30% de la nueva cuota
    
    # Metadata
    origen: OrigenPropuesta
    es_opcion_seleccionada: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class LimitesActualesResponse(BaseModel):
    """Estado actual del crédito (columna izquierda de la tabla)"""
    saldo_credito: Decimal
    cuotas_pendientes: int
    tiempo_pendiente: TiempoAhorrado
    abono_adicional_cuota: Decimal  # Actualmente $0
    valor_cuota: Decimal
    total_por_pagar_aprox: Decimal
    veces_pagado: Decimal


class PropuestaCompletaResponse(BaseModel):
    """
    Respuesta completa con todas las proyecciones.
    Representa la tabla "NUEVAS OPORTUNIDADES" completa.
    """
    # Identificación
    analisis_id: UUID
    numero_credito: str | None
    nombre_cliente: str | None
    banco_nombre: str | None
    fecha_generacion: date
    
    # Estado actual (columna izquierda)
    limites_actuales: LimitesActualesResponse
    
    # Las 3 opciones calculadas
    opciones: list[ProyeccionOpcionResponse]
    
    # Información adicional
    tasa_cobrada_con_frech: Decimal | None
    seguros_actuales: Decimal | None
    
    # Validez
    vigencia_dias: int = 20  # "Propuesta válida por 20 días"
    fecha_vencimiento: date | None = None
    
    # Agente
    agente_financiero: str | None = None


class PropuestaListItem(BaseModel):
    """Item para listados de propuestas"""
    id: UUID
    analisis_id: UUID
    numero_opcion: int
    abono_adicional_mensual: Decimal
    valor_ahorrado_intereses: Decimal | None
    honorarios_calculados: Decimal | None
    origen: OrigenPropuesta
    es_opcion_seleccionada: bool
    created_at: datetime | None
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS PARA CÁLCULOS INTERNOS
# ═══════════════════════════════════════════════════════════════════════════════

class DatosCalculoInput(BaseModel):
    """Datos necesarios para el motor de cálculo"""
    # Del análisis
    saldo_capital: Decimal
    valor_cuota_actual: Decimal  # Con subsidio
    cuotas_pendientes: int
    tasa_interes_mensual: Decimal  # Convertida de EA a mensual
    valor_prestado_inicial: Decimal
    
    # Del abono
    abono_adicional: Decimal


class ResultadoAmortizacion(BaseModel):
    """Resultado del cálculo de amortización"""
    cuotas_totales: int
    total_pagado: Decimal
    total_intereses: Decimal
    total_capital: Decimal
    
    # Para comparación
    ahorro_vs_actual: Decimal | None = None


class FilaAmortizacion(BaseModel):
    """Una fila de la tabla de amortización (si se necesita detalle)"""
    numero_cuota: int
    saldo_inicial: Decimal
    cuota: Decimal
    interes: Decimal
    capital: Decimal
    abono_extra: Decimal
    saldo_final: Decimal
