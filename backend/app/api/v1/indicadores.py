"""
API de Indicadores Financieros de Colombia
==========================================

Endpoints para consultar UVR, IPC, DTF e IBR desde fuentes oficiales:
- Socrata (datos.gov.co) - Fuente principal
- Banco de la República - Fallback
- Estimaciones matemáticas - Último recurso

Los datos se cachean por 12 horas para optimizar rendimiento.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.indicadores_service import (
    IndicadoresFinancierosService,
    FuenteDatos,
    obtener_servicio_indicadores,
)

router = APIRouter(prefix="/indicadores", tags=["Indicadores Financieros"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS DE RESPUESTA
# ═══════════════════════════════════════════════════════════════════════════════

class UVRResponse(BaseModel):
    """Respuesta con valor de la UVR"""
    fecha: date
    valor: Decimal = Field(..., description="Valor de la UVR en pesos colombianos")
    fuente: str = Field(..., description="Fuente de los datos (SOCRATA, BANREP_API, CACHE, MANUAL)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2026-01-29",
                "valor": "385.4521",
                "fuente": "SOCRATA"
            }
        }


class IPCResponse(BaseModel):
    """Respuesta con IPC"""
    fecha: date = Field(..., description="Último día del mes")
    valor: Decimal = Field(..., description="Índice de Precios al Consumidor")
    variacion_mensual: Decimal = Field(..., description="Variación porcentual vs mes anterior")
    variacion_anual: Decimal = Field(..., description="Inflación anual (%)")
    fuente: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2025-12-31",
                "valor": "158.50",
                "variacion_mensual": "0.45",
                "variacion_anual": "5.80",
                "fuente": "SOCRATA"
            }
        }


class DTFResponse(BaseModel):
    """Respuesta con DTF"""
    fecha: date
    valor: Decimal = Field(..., description="Tasa DTF E.A. (%)")
    fuente: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2026-01-24",
                "valor": "10.50",
                "fuente": "SOCRATA"
            }
        }


class IBRResponse(BaseModel):
    """Respuesta con IBR"""
    fecha: date
    overnight: Decimal = Field(..., description="IBR Overnight (%)")
    un_mes: Optional[Decimal] = Field(None, description="IBR 1 mes (%)")
    tres_meses: Optional[Decimal] = Field(None, description="IBR 3 meses (%)")
    fuente: str


class IndicadoresConsolidadosResponse(BaseModel):
    """Respuesta consolidada de todos los indicadores"""
    fecha: date
    uvr: Optional[Decimal] = Field(None, description="Valor UVR (COP)")
    dtf: Optional[Decimal] = Field(None, description="DTF E.A. (%)")
    ibr_overnight: Optional[Decimal] = Field(None, description="IBR Overnight (%)")
    ipc_anual: Optional[Decimal] = Field(None, description="Inflación anual (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2026-01-29",
                "uvr": "385.4521",
                "dtf": "10.50",
                "ibr_overnight": "9.75",
                "ipc_anual": "5.80"
            }
        }


class ConversionUVRRequest(BaseModel):
    """Request para conversión UVR <-> Pesos"""
    monto: Decimal = Field(..., gt=0, description="Monto a convertir")
    valor_uvr: Optional[Decimal] = Field(None, gt=0, description="Valor UVR (si no se provee, usa el actual)")
    direccion: str = Field("uvr_a_pesos", description="uvr_a_pesos o pesos_a_uvr")


class ConversionUVRResponse(BaseModel):
    """Respuesta de conversión"""
    monto_original: Decimal
    monto_convertido: Decimal
    valor_uvr_usado: Decimal
    direccion: str


class ProyeccionUVRRequest(BaseModel):
    """Request para proyectar UVR"""
    meses: int = Field(..., ge=1, le=360, description="Meses a proyectar")
    uvr_inicial: Optional[Decimal] = Field(None, description="UVR inicial (si no se provee, usa el actual)")
    inflacion_anual: Decimal = Field(default=Decimal("0.06"), description="Inflación anual esperada (default 6%)")


class ProyeccionUVRResponse(BaseModel):
    """Respuesta de proyección UVR"""
    uvr_inicial: Decimal
    uvr_proyectado: Decimal
    meses: int
    inflacion_anual: Decimal
    incremento_absoluto: Decimal
    incremento_porcentual: Decimal


class HistoricoUVRItem(BaseModel):
    """Item del histórico de UVR"""
    fecha: date
    valor: Decimal
    fuente: str


class HistoricoUVRResponse(BaseModel):
    """Respuesta con histórico de UVR"""
    fecha_inicio: date
    fecha_fin: date
    total_registros: int
    datos: List[HistoricoUVRItem]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_service() -> IndicadoresFinancierosService:
    """Obtiene el servicio de indicadores"""
    return obtener_servicio_indicadores()


@router.get(
    "/uvr",
    response_model=UVRResponse,
    summary="Obtener valor UVR",
    description="Obtiene el valor de la Unidad de Valor Real (UVR) para hoy o una fecha específica."
)
async def get_uvr(
    fecha: Optional[date] = Query(
        None, 
        description="Fecha en formato YYYY-MM-DD. Si no se provee, retorna el valor de hoy."
    )
):
    """
    Obtiene el valor de la UVR.
    
    La UVR (Unidad de Valor Real) es calculada diariamente por el Banco de la República
    basándose en la variación del IPC. Se utiliza principalmente para créditos hipotecarios
    en sistema UVR.
    
    **Fuentes de datos (en orden de prioridad):**
    1. Socrata (datos.gov.co)
    2. API del Banco de la República
    3. Estimación matemática basada en inflación histórica
    """
    service = _get_service()
    
    try:
        if fecha:
            uvr = await service.obtener_uvr(fecha)
        else:
            uvr = await service.obtener_uvr_actual()
        
        return UVRResponse(
            fecha=uvr.fecha,
            valor=uvr.valor,
            fuente=uvr.fuente.value
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando UVR: {str(e)}")


@router.get(
    "/ipc",
    response_model=IPCResponse,
    summary="Obtener IPC",
    description="Obtiene el Índice de Precios al Consumidor (inflación) para un mes específico."
)
async def get_ipc(
    anio: Optional[int] = Query(None, ge=2000, le=2100, description="Año"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mes (1-12)")
):
    """
    Obtiene el IPC (Índice de Precios al Consumidor).
    
    El IPC es publicado mensualmente por el DANE y se utiliza para medir la inflación.
    Si no se especifica año/mes, retorna el último disponible.
    """
    service = _get_service()
    
    try:
        if anio and mes:
            ipc = await service.obtener_ipc(anio, mes)
        else:
            ipc = await service.obtener_ipc_actual()
        
        return IPCResponse(
            fecha=ipc.fecha,
            valor=ipc.valor,
            variacion_mensual=ipc.variacion_mensual,
            variacion_anual=ipc.variacion_anual,
            fuente=ipc.fuente.value
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando IPC: {str(e)}")


@router.get(
    "/dtf",
    response_model=DTFResponse,
    summary="Obtener DTF",
    description="Obtiene la tasa DTF (Depósito a Término Fijo) vigente."
)
async def get_dtf(
    fecha: Optional[date] = Query(None, description="Fecha específica (default: hoy)")
):
    """
    Obtiene la tasa DTF.
    
    El DTF es calculado semanalmente por el Banco de la República como el promedio
    ponderado de las tasas de captación a 90 días de los establecimientos bancarios.
    """
    service = _get_service()
    
    try:
        if fecha:
            dtf = await service.obtener_dtf(fecha)
        else:
            dtf = await service.obtener_dtf_actual()
        
        return DTFResponse(
            fecha=dtf.fecha,
            valor=dtf.valor,
            fuente=dtf.fuente.value
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando DTF: {str(e)}")


@router.get(
    "/ibr",
    response_model=IBRResponse,
    summary="Obtener IBR",
    description="Obtiene el Indicador Bancario de Referencia."
)
async def get_ibr(
    fecha: Optional[date] = Query(None, description="Fecha específica (default: hoy)")
):
    """
    Obtiene el IBR (Indicador Bancario de Referencia).
    
    El IBR es calculado diariamente por el BanRep y se utiliza como referencia
    para tasas de interés en Colombia. Incluye variantes: Overnight, 1 mes, 3 meses.
    """
    service = _get_service()
    
    try:
        if fecha:
            ibr = await service.obtener_ibr(fecha)
        else:
            ibr = await service.obtener_ibr_actual()
        
        return IBRResponse(
            fecha=ibr.fecha,
            overnight=ibr.overnight,
            un_mes=ibr.un_mes,
            tres_meses=ibr.tres_meses,
            fuente=ibr.fuente.value
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando IBR: {str(e)}")


@router.get(
    "/consolidados",
    response_model=IndicadoresConsolidadosResponse,
    summary="Obtener todos los indicadores",
    description="Obtiene todos los indicadores financieros consolidados para hoy."
)
async def get_indicadores_consolidados():
    """
    Obtiene todos los indicadores financieros del día.
    
    Útil para dashboards y cálculos que requieren múltiples indicadores.
    Incluye: UVR, DTF, IBR, IPC (inflación anual).
    """
    service = _get_service()
    
    try:
        indicadores = await service.obtener_indicadores_hoy()
        
        return IndicadoresConsolidadosResponse(
            fecha=indicadores.fecha,
            uvr=indicadores.uvr,
            dtf=indicadores.dtf,
            ibr_overnight=indicadores.ibr_overnight,
            ipc_anual=indicadores.ipc_anual
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando indicadores: {str(e)}")


@router.get(
    "/uvr/historico",
    response_model=HistoricoUVRResponse,
    summary="Histórico de UVR",
    description="Obtiene el histórico de valores UVR para un rango de fechas."
)
async def get_historico_uvr(
    fecha_inicio: date = Query(..., description="Fecha inicial (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha final (default: hoy)")
):
    """
    Obtiene el histórico de valores UVR.
    
    Útil para gráficos de evolución y análisis de tendencias.
    Máximo 365 días por consulta para evitar sobrecarga.
    """
    service = _get_service()
    
    if fecha_fin is None:
        fecha_fin = date.today()
    
    # Validar rango máximo
    dias = (fecha_fin - fecha_inicio).days
    if dias > 365:
        raise HTTPException(
            status_code=400,
            detail="El rango máximo es de 365 días. Por favor reduzca el período."
        )
    
    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="La fecha de inicio debe ser anterior a la fecha fin."
        )
    
    try:
        historico = await service.obtener_historico_uvr(fecha_inicio, fecha_fin)
        
        datos = [
            HistoricoUVRItem(
                fecha=uvr.fecha,
                valor=uvr.valor,
                fuente=uvr.fuente.value
            )
            for uvr in historico
        ]
        
        return HistoricoUVRResponse(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_registros=len(datos),
            datos=datos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando histórico: {str(e)}")


@router.post(
    "/uvr/convertir",
    response_model=ConversionUVRResponse,
    summary="Convertir UVR <-> Pesos",
    description="Convierte montos entre UVR y pesos colombianos."
)
async def convertir_uvr(request: ConversionUVRRequest):
    """
    Convierte montos entre UVR y pesos colombianos.
    
    Útil para:
    - Convertir saldo de crédito en UVR a pesos actuales
    - Calcular cuántas UVR equivale un monto en pesos
    """
    service = _get_service()
    
    try:
        # Obtener valor UVR actual si no se provee
        if request.valor_uvr:
            valor_uvr = request.valor_uvr
        else:
            uvr_actual = await service.obtener_uvr_actual()
            valor_uvr = uvr_actual.valor
        
        if request.direccion == "uvr_a_pesos":
            monto_convertido = service.convertir_uvr_a_pesos(request.monto, valor_uvr)
        elif request.direccion == "pesos_a_uvr":
            monto_convertido = service.convertir_pesos_a_uvr(request.monto, valor_uvr)
        else:
            raise HTTPException(
                status_code=400,
                detail="Dirección debe ser 'uvr_a_pesos' o 'pesos_a_uvr'"
            )
        
        return ConversionUVRResponse(
            monto_original=request.monto,
            monto_convertido=monto_convertido,
            valor_uvr_usado=valor_uvr,
            direccion=request.direccion
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en conversión: {str(e)}")


@router.post(
    "/uvr/proyectar",
    response_model=ProyeccionUVRResponse,
    summary="Proyectar UVR a futuro",
    description="Proyecta el valor de la UVR a futuro basándose en inflación esperada."
)
async def proyectar_uvr(request: ProyeccionUVRRequest):
    """
    Proyecta el valor de la UVR a futuro.
    
    La UVR se incrementa diariamente basándose en la inflación.
    Esta proyección estima el valor futuro usando inflación anual esperada.
    
    Fórmula: UVR_futuro = UVR_actual * (1 + inflación)^(meses/12)
    """
    service = _get_service()
    
    try:
        # Obtener UVR actual si no se provee
        if request.uvr_inicial:
            uvr_inicial = request.uvr_inicial
        else:
            uvr_actual = await service.obtener_uvr_actual()
            uvr_inicial = uvr_actual.valor
        
        uvr_proyectado = service.proyectar_uvr(
            uvr_actual=uvr_inicial,
            meses=request.meses,
            inflacion_anual=request.inflacion_anual
        )
        
        incremento_absoluto = uvr_proyectado - uvr_inicial
        incremento_porcentual = ((uvr_proyectado / uvr_inicial) - 1) * 100
        
        return ProyeccionUVRResponse(
            uvr_inicial=uvr_inicial,
            uvr_proyectado=uvr_proyectado,
            meses=request.meses,
            inflacion_anual=request.inflacion_anual,
            incremento_absoluto=incremento_absoluto.quantize(Decimal("0.0001")),
            incremento_porcentual=incremento_porcentual.quantize(Decimal("0.01"))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en proyección: {str(e)}")
