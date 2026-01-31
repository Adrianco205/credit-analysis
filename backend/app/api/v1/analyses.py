"""
API Endpoints para Análisis Hipotecario.
========================================

Endpoints:
- POST   /analyses              → Crear análisis desde documento
- GET    /analyses              → Listar análisis del usuario
- GET    /analyses/{id}         → Obtener análisis detallado
- GET    /analyses/{id}/summary → Obtener resumen (4 bloques)
- PATCH  /analyses/{id}/manual  → Actualizar campos manuales
- POST   /analyses/{id}/projections → Generar proyecciones
- GET    /analyses/{id}/projections → Obtener proyecciones
- POST   /analyses/{id}/select-option → Seleccionar opción de ahorro
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import Usuario
from app.models.banco import Banco
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.propuestas_repo import PropuestasRepo
from app.services.analysis_service import (
    AnalysisService,
    DatosUsuarioInput,
    OpcionAbonoInput,
    get_analysis_service
)
from app.schemas.analisis import (
    AnalisisStatus,
    SistemaAmortizacion,
    ResumenCreditoResponse,
    DatosBasicosResumen,
    LimitesBancoResumen,
    AjusteInflacionResumen,
    CostosExtraResumen,
)
from app.schemas.propuestas import (
    TiempoAhorrado,
    ProyeccionOpcionResponse,
    LimitesActualesResponse,
    PropuestaCompletaResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses", tags=["analyses"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS DE REQUEST/RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════

class DatosUsuarioRequest(BaseModel):
    """Datos socioeconómicos del usuario."""
    ingresos_mensuales: Decimal = Field(..., gt=0, description="Ingresos mensuales en COP")
    capacidad_pago_max: Decimal | None = Field(None, gt=0)
    tipo_contrato_laboral: str | None = Field(None, max_length=80)
    # MEJORA 2: Preferencias de abono extra del usuario
    opciones_abono_preferidas: list[Decimal] | None = Field(
        None, 
        max_length=5,
        description="Opciones de abono extra mensual preferidas por el usuario (ej: [200000, 300000, 400000])"
    )


class CreateAnalysisRequest(BaseModel):
    """Request para crear un análisis."""
    documento_id: UUID
    datos_usuario: DatosUsuarioRequest


class UpdateManualFieldsRequest(BaseModel):
    """Request para actualizar campos manuales."""
    numero_credito: str | None = Field(None, max_length=50)
    sistema_amortizacion: str | None = None
    valor_prestado_inicial: Decimal | None = Field(None, gt=0)
    fecha_desembolso: date | None = None
    cuotas_pactadas: int | None = Field(None, gt=0)
    cuotas_pagadas: int | None = Field(None, ge=0)
    cuotas_pendientes: int | None = Field(None, gt=0)
    tasa_interes_pactada_ea: Decimal | None = Field(None, ge=0, le=1)
    tasa_interes_cobrada_ea: Decimal | None = Field(None, ge=0, le=1)
    valor_cuota_con_seguros: Decimal | None = Field(None, gt=0)
    beneficio_frech_mensual: Decimal | None = Field(None, ge=0)
    saldo_capital_pesos: Decimal | None = Field(None, gt=0)
    saldo_capital_uvr: Decimal | None = Field(None, gt=0)
    valor_uvr_fecha_extracto: Decimal | None = Field(None, gt=0)
    seguro_vida: Decimal | None = Field(None, ge=0)
    seguro_incendio: Decimal | None = Field(None, ge=0)
    seguro_terremoto: Decimal | None = Field(None, ge=0)


class OpcionAbonoRequest(BaseModel):
    """Una opción de abono para proyección."""
    numero_opcion: int = Field(..., ge=1, le=10)
    abono_adicional_mensual: Decimal = Field(..., gt=0)
    nombre_opcion: str | None = Field(None, max_length=50)


class GenerateProjectionsRequest(BaseModel):
    """Request para generar proyecciones."""
    opciones: list[OpcionAbonoRequest] = Field(..., min_length=1, max_length=5)


class SelectOptionRequest(BaseModel):
    """Request para seleccionar una opción."""
    numero_opcion: int = Field(..., ge=1)


class AnalysisListItem(BaseModel):
    """Item para listado de análisis."""
    id: UUID
    documento_id: UUID
    numero_credito: str | None
    banco_nombre: str | None = None
    saldo_capital_pesos: Decimal | None
    status: str
    fecha_extracto: date | None
    created_at: date | None
    tiene_propuestas: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisDetailResponse(BaseModel):
    """Respuesta detallada de un análisis."""
    id: UUID
    documento_id: UUID
    usuario_id: UUID
    status: str
    
    # Validaciones
    nombre_coincide: bool | None
    es_extracto_hipotecario: bool
    
    # Datos del crédito
    nombre_titular_extracto: str | None
    numero_credito: str | None
    sistema_amortizacion: str | None
    plan_credito: str | None
    
    # Fechas
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
    
    # Montos
    valor_prestado_inicial: Decimal | None
    valor_cuota_sin_seguros: Decimal | None
    valor_cuota_con_seguros: Decimal | None
    beneficio_frech_mensual: Decimal | None
    valor_cuota_con_subsidio: Decimal | None
    saldo_capital_pesos: Decimal | None
    
    # UVR
    saldo_capital_uvr: Decimal | None
    valor_uvr_fecha_extracto: Decimal | None
    
    # Seguros
    seguro_vida: Decimal | None
    seguro_incendio: Decimal | None
    seguro_terremoto: Decimal | None
    seguros_total_mensual: Decimal | None
    
    # Datos del usuario
    ingresos_mensuales: Decimal | None
    capacidad_pago_max: Decimal | None
    tipo_contrato_laboral: str | None
    
    # MEJORA 2: Preferencias de abono del usuario
    opciones_abono_preferidas: list[Decimal] | None
    abono_adicional_actual: Decimal | None  # MEJORA 3: Siempre NULL en diagnóstico inicial
    
    # Campos manuales y extraídos
    campos_manuales: list[str] | None
    campos_extraidos_ia: list[str] | None  # MEJORA 5: Campos READONLY
    
    # MEJORA 4: Validación de identidad
    cedula_coincide: bool | None
    identificacion_extracto: str | None
    
    # Metadata
    created_at: datetime | None
    
    model_config = ConfigDict(from_attributes=True)


class CreateAnalysisResponse(BaseModel):
    """Respuesta al crear análisis."""
    success: bool
    analisis_id: UUID | None = None
    status: str | None = None
    message: str | None = None
    requires_manual_input: bool = False
    campos_faltantes: list[str] | None = None
    campos_extraidos: list[str] | None = None  # MEJORA 5: Campos que son READONLY
    name_mismatch: bool = False
    id_mismatch: bool = False  # MEJORA 4: Cédula no coincide
    invalid_document_type: bool = False  # MEJORA 1: Documento no es hipotecario
    tipo_documento_detectado: str | None = None  # MEJORA 1: Qué tipo de documento es


class ProjectionResponse(BaseModel):
    """Respuesta de una proyección individual."""
    id: UUID
    numero_opcion: int
    nombre_opcion: str | None
    abono_adicional_mensual: Decimal
    
    # Tiempo
    cuotas_nuevas: int | None
    tiempo_restante_anios: int | None
    tiempo_restante_meses: int | None
    cuotas_reducidas: int | None
    tiempo_ahorrado_anios: int | None
    tiempo_ahorrado_meses: int | None
    
    # Dinero
    nuevo_valor_cuota: Decimal | None
    total_por_pagar_aprox: Decimal | None
    valor_ahorrado_intereses: Decimal | None
    veces_pagado: Decimal | None
    
    # Honorarios
    honorarios_calculados: Decimal | None
    honorarios_con_iva: Decimal | None
    ingreso_minimo_requerido: Decimal | None
    
    # Estado
    origen: str
    es_opcion_seleccionada: bool
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("", response_model=CreateAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: CreateAnalysisRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo análisis a partir de un documento PDF.
    
    El documento debe estar previamente subido. Este endpoint:
    1. **MEJORA 1**: Valida que el documento sea un extracto hipotecario
    2. Extrae datos con IA (Gemini)
    3. Valida que el nombre del titular coincida con el usuario
    4. **MEJORA 4**: Valida que la cédula del PDF coincida con el usuario
    5. Crea el registro de análisis
    
    Si faltan campos críticos, el análisis quedará en estado PENDING_MANUAL.
    Si el documento no es un extracto hipotecario, retorna error INVALID_DOCUMENT_TYPE.
    """
    service = get_analysis_service(db)
    
    datos_usuario = DatosUsuarioInput(
        ingresos_mensuales=request.datos_usuario.ingresos_mensuales,
        capacidad_pago_max=request.datos_usuario.capacidad_pago_max,
        tipo_contrato_laboral=request.datos_usuario.tipo_contrato_laboral,
        # MEJORA 2: Capturar preferencias de abono del usuario
        opciones_abono_preferidas=request.datos_usuario.opciones_abono_preferidas
    )
    
    result = await service.create_analysis_from_document(
        documento_id=request.documento_id,
        usuario=current_user,
        datos_usuario=datos_usuario
    )
    
    if not result.success:
        if result.error_code == "DOCUMENT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error_message)
        if result.error_code == "ANALYSIS_EXISTS":
            raise HTTPException(status_code=409, detail=result.error_message)
        # MEJORA 1: Error específico para tipo de documento inválido
        if result.error_code == "INVALID_DOCUMENT_TYPE":
            raise HTTPException(
                status_code=422, 
                detail={
                    "message": result.error_message,
                    "tipo_documento_detectado": result.tipo_documento_detectado,
                    "error_code": "INVALID_DOCUMENT_TYPE"
                }
            )
        raise HTTPException(status_code=400, detail=result.error_message)
    
    return CreateAnalysisResponse(
        success=True,
        analisis_id=result.analisis.id,
        status=result.analisis.status,
        message="Análisis creado exitosamente",
        requires_manual_input=result.requires_manual_input,
        campos_faltantes=result.campos_faltantes,
        campos_extraidos=result.campos_extraidos,  # MEJORA 5: Campos readonly
        name_mismatch=result.name_mismatch,
        id_mismatch=result.id_mismatch  # MEJORA 4
    )


@router.get("", response_model=list[AnalysisListItem])
def list_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Listar análisis del usuario autenticado."""
    repo = AnalysesRepo(db)
    propuestas_repo = PropuestasRepo(db)
    
    analisis_list = repo.list_by_user(current_user.id, skip=skip, limit=limit)
    
    result = []
    for a in analisis_list:
        item = AnalysisListItem(
            id=a.id,
            documento_id=a.documento_id,
            numero_credito=a.numero_credito,
            saldo_capital_pesos=a.saldo_capital_pesos,
            status=a.status,
            fecha_extracto=a.fecha_extracto,
            created_at=a.created_at.date() if a.created_at else None,
            tiene_propuestas=propuestas_repo.has_propuestas(a.id)
        )
        result.append(item)
    
    return result


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    analysis_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener detalle completo de un análisis."""
    repo = AnalysesRepo(db)
    
    analisis = repo.get_by_id_and_user(analysis_id, current_user.id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    return AnalysisDetailResponse.model_validate(analisis)


@router.get("/{analysis_id}/summary", response_model=ResumenCreditoResponse)
def get_analysis_summary(
    analysis_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener el resumen del crédito organizado en 4 bloques:
    1. DATOS BÁSICOS
    2. LÍMITES CON EL BANCO  
    3. AJUSTE POR INFLACIÓN (solo UVR)
    4. INTERESES Y SEGUROS
    """
    repo = AnalysesRepo(db)
    
    analisis = repo.get_by_id_and_user(analysis_id, current_user.id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    # Calcular campos derivados si no están
    if analisis.total_pagado_fecha is None:
        repo.calculate_derived_fields(analisis)
        db.commit()
    
    # Bloque 1: Datos Básicos
    cuotas_por_pagar = analisis.cuotas_pendientes or 0
    cuota_actual = analisis.valor_cuota_con_subsidio or analisis.valor_cuota_con_seguros or Decimal("0")
    beneficio_frech = analisis.beneficio_frech_mensual or Decimal("0")
    cuota_completa = (analisis.valor_cuota_con_seguros or Decimal("0"))
    
    datos_basicos = DatosBasicosResumen(
        valor_prestado=analisis.valor_prestado_inicial or Decimal("0"),
        cuotas_pactadas=analisis.cuotas_pactadas or 0,
        cuotas_pagadas=analisis.cuotas_pagadas or 0,
        cuotas_por_pagar=cuotas_por_pagar,
        cuota_actual_aprox=cuota_actual,
        beneficio_frech=beneficio_frech,
        cuota_completa_aprox=cuota_completa,
        total_pagado_fecha=analisis.total_pagado_fecha or Decimal("0"),
        total_frech_recibido=analisis.total_frech_recibido or Decimal("0"),
        monto_real_pagado_banco=analisis.monto_real_pagado_banco or Decimal("0")
    )
    
    # Bloque 2: Límites con el Banco
    # MEJORA 3: abono_adicional_cuota siempre en None (diagnóstico inicial)
    limites_banco = LimitesBancoResumen(
        valor_prestado=analisis.valor_prestado_inicial or Decimal("0"),
        saldo_actual_credito=analisis.saldo_capital_pesos or Decimal("0"),
        abono_adicional_cuota=analisis.abono_adicional_actual  # Siempre NULL inicialmente
    )
    
    # Bloque 3: Ajuste por Inflación (solo UVR)
    ajuste_inflacion = None
    if analisis.sistema_amortizacion == "UVR":
        ajuste_inflacion = AjusteInflacionResumen(
            ajuste_pesos=analisis.ajuste_inflacion_pesos or Decimal("0"),
            porcentaje_ajuste=analisis.porcentaje_ajuste_inflacion or Decimal("0")
        )
    
    # Bloque 4: Costos Extra
    costos_extra = CostosExtraResumen(
        total_intereses_seguros=analisis.total_intereses_seguros or Decimal("0")
    )
    
    return ResumenCreditoResponse(
        analisis_id=analisis.id,
        numero_credito=analisis.numero_credito,
        nombre_titular=analisis.nombre_titular_extracto,
        banco_nombre=None,  # TODO: Join con tabla bancos
        sistema_amortizacion=analisis.sistema_amortizacion,
        fecha_extracto=analisis.fecha_extracto,
        datos_basicos=datos_basicos,
        limites_banco=limites_banco,
        ajuste_inflacion=ajuste_inflacion,
        costos_extra=costos_extra,
        tasa_cobrada_con_frech=analisis.tasa_interes_subsidiada_ea,
        seguros_actuales_mensual=analisis.seguros_total_mensual
    )


@router.patch("/{analysis_id}/manual", response_model=CreateAnalysisResponse)
def update_manual_fields(
    analysis_id: UUID,
    request: UpdateManualFieldsRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar campos que el usuario debe proporcionar manualmente.
    
    **MEJORA 5**: Solo permite actualizar campos que NO fueron extraídos automáticamente.
    Los campos en `campos_extraidos` (devueltos en la respuesta de creación) son de SOLO LECTURA.
    
    Si intentas modificar un campo que ya fue extraído por la IA, será ignorado silenciosamente.
    """
    service = get_analysis_service(db)
    
    # Convertir request a dict, excluyendo None
    manual_data = {
        k: v for k, v in request.model_dump().items() 
        if v is not None
    }
    
    result = service.update_manual_fields(
        analisis_id=analysis_id,
        usuario_id=current_user.id,
        manual_data=manual_data
    )
    
    if not result.success:
        if result.error_code == "ANALYSIS_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error_message)
        raise HTTPException(status_code=400, detail=result.error_message)
    
    return CreateAnalysisResponse(
        success=True,
        analisis_id=result.analisis.id,
        status=result.analisis.status,
        message="Campos actualizados",
        requires_manual_input=result.requires_manual_input,
        campos_faltantes=result.campos_faltantes,  # Campos que aún faltan
        campos_extraidos=result.campos_extraidos   # MEJORA 5: Campos readonly
    )


@router.post("/{analysis_id}/projections", response_model=list[ProjectionResponse])
def generate_projections(
    analysis_id: UUID,
    request: GenerateProjectionsRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generar proyecciones de ahorro para un análisis.
    
    El usuario proporciona las opciones de abono adicional que puede pagar.
    El sistema calcula para cada opción:
    - Tiempo ahorrado
    - Intereses ahorrados
    - Honorarios (3% del ahorro)
    - Ingreso mínimo requerido (30% de la nueva cuota)
    """
    service = get_analysis_service(db)
    
    opciones = [
        OpcionAbonoInput(
            numero_opcion=o.numero_opcion,
            abono_adicional_mensual=o.abono_adicional_mensual,
            nombre_opcion=o.nombre_opcion
        )
        for o in request.opciones
    ]
    
    result = service.generate_projections(
        analisis_id=analysis_id,
        opciones=opciones,
        usuario_id=current_user.id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)
    
    return [ProjectionResponse.model_validate(p) for p in result.propuestas]


@router.get("/{analysis_id}/projections", response_model=list[ProjectionResponse])
def get_projections(
    analysis_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener proyecciones generadas para un análisis."""
    # Verificar acceso
    analyses_repo = AnalysesRepo(db)
    analisis = analyses_repo.get_by_id_and_user(analysis_id, current_user.id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    propuestas_repo = PropuestasRepo(db)
    propuestas = propuestas_repo.list_by_analisis(analysis_id)
    
    return [ProjectionResponse.model_validate(p) for p in propuestas]


@router.post("/{analysis_id}/select-option", response_model=ProjectionResponse)
def select_option(
    analysis_id: UUID,
    request: SelectOptionRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Seleccionar una opción de ahorro."""
    # Verificar acceso
    analyses_repo = AnalysesRepo(db)
    analisis = analyses_repo.get_by_id_and_user(analysis_id, current_user.id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    propuestas_repo = PropuestasRepo(db)
    propuesta = propuestas_repo.select_opcion(analysis_id, request.numero_opcion)
    
    if not propuesta:
        raise HTTPException(
            status_code=404, 
            detail=f"Opción {request.numero_opcion} no encontrada"
        )
    
    db.commit()
    return ProjectionResponse.model_validate(propuesta)


@router.get("/{analysis_id}/select-option", response_model=ProjectionResponse)
def select_option_get(
    analysis_id: UUID,
    numero_opcion: int = Query(..., ge=1),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Seleccionar una opción de ahorro (vía GET)."""
    analyses_repo = AnalysesRepo(db)
    analisis = analyses_repo.get_by_id_and_user(analysis_id, current_user.id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    propuestas_repo = PropuestasRepo(db)
    propuesta = propuestas_repo.select_opcion(analysis_id, numero_opcion)

    if not propuesta:
        raise HTTPException(
            status_code=404,
            detail=f"Opción {numero_opcion} no encontrada"
        )

    db.commit()
    return ProjectionResponse.model_validate(propuesta)


# ═══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE PROPUESTA PDF
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi.responses import StreamingResponse
from datetime import datetime
import io

from app.services.proposal_pdf_service import (
    PropuestaPDFGenerator,
    DatosPropuesta,
    DatosCliente,
    DatosCredito,
    OpcionAhorro,
    generar_numero_propuesta,
)


@router.get(
    "/{analysis_id}/proposal/pdf",
    summary="Descargar propuesta en PDF",
    description="Genera y descarga el PDF con la propuesta de optimización del crédito.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF de la propuesta"
        }
    }
)
def download_proposal_pdf(
    analysis_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genera y descarga el PDF de propuesta de ahorro.
    
    Requisitos:
    - El análisis debe tener proyecciones generadas (estado PROJECTED)
    - El usuario debe ser el propietario del análisis
    """
    # Verificar acceso
    analyses_repo = AnalysesRepo(db)
    analisis = analyses_repo.get_by_id_and_user(analysis_id, current_user.id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    # Verificar que tenga proyecciones
    propuestas_repo = PropuestasRepo(db)
    propuestas = propuestas_repo.list_by_analisis(analysis_id)
    
    if not propuestas:
        raise HTTPException(
            status_code=400,
            detail="El análisis no tiene proyecciones. Solicite al administrador que las genere."
        )
    
    # Construir datos del cliente
    nombre_completo = " ".join(
        [
            current_user.nombres or "",
            current_user.primer_apellido or "",
            current_user.segundo_apellido or "",
        ]
    ).strip() or "No registrado"

    datos_cliente = DatosCliente(
        nombre_completo=nombre_completo,
        cedula=current_user.identificacion or "No registrada",
        email=current_user.email or "No registrado",
        telefono=current_user.telefono,
        ingresos_mensuales=analisis.ingresos_mensuales or Decimal("0"),
    )
    
    # Construir datos del crédito
    banco_nombre = "No especificado"
    if analisis.banco_id:
        banco = db.get(Banco, analisis.banco_id)
        if banco and banco.nombre:
            banco_nombre = banco.nombre

    cuota_mensual = analisis.valor_cuota_con_seguros or analisis.valor_cuota_sin_seguros or Decimal("0")
    tasa_interes = analisis.tasa_interes_cobrada_ea or analisis.tasa_interes_pactada_ea or Decimal("0")

    datos_credito = DatosCredito(
        numero_credito=analisis.numero_credito or "No especificado",
        banco=banco_nombre,
        saldo_capital=analisis.saldo_capital_pesos or Decimal("0"),
        tasa_interes_ea=tasa_interes,
        cuota_mensual=cuota_mensual,
        cuotas_pendientes=analisis.cuotas_pendientes or 0,
        cuotas_pagadas=analisis.cuotas_pagadas or 0,
        fecha_desembolso=analisis.fecha_desembolso,
        sistema_amortizacion=analisis.sistema_amortizacion or "PESOS",
    )
    
    # Construir opciones de ahorro
    opciones = []
    for p in propuestas:
        tiempo_ahorrado_meses = (p.tiempo_ahorrado_anios or 0) * 12 + (p.tiempo_ahorrado_meses or 0)
        abono_extra = p.abono_adicional_mensual or Decimal("0")
        nueva_cuota = p.nuevo_valor_cuota or (cuota_mensual + abono_extra)

        opcion = OpcionAhorro(
            numero_opcion=p.numero_opcion,
            nombre=p.nombre_opcion or f"Opción {p.numero_opcion}",
            abono_extra_mensual=abono_extra,
            cuotas_nuevas=p.cuotas_nuevas or 0,
            tiempo_ahorrado_meses=tiempo_ahorrado_meses,
            intereses_ahorrados=p.valor_ahorrado_intereses or Decimal("0"),
            honorarios=p.honorarios_calculados or Decimal("0"),
            honorarios_con_iva=p.honorarios_con_iva or Decimal("0"),
            ingreso_minimo_requerido=p.ingreso_minimo_requerido or Decimal("0"),
            nueva_cuota=nueva_cuota,
        )
        opciones.append(opcion)
    
    # Ordenar por número de opción
    opciones.sort(key=lambda x: x.numero_opcion)
    
    # Datos de la propuesta
    fecha_generacion = datetime.now()
    datos_propuesta = DatosPropuesta(
        cliente=datos_cliente,
        credito=datos_credito,
        opciones=opciones,
        fecha_generacion=fecha_generacion,
        numero_propuesta=generar_numero_propuesta(str(analysis_id), fecha_generacion),
    )
    
    # Generar PDF
    try:
        generator = PropuestaPDFGenerator()
        pdf_bytes = generator.generar_propuesta(datos_propuesta)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando PDF: {str(e)}"
        )
    
    # Retornar como descarga
    filename = f"propuesta_ecofinanzas_{analysis_id}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(pdf_bytes)),
        }
    )
