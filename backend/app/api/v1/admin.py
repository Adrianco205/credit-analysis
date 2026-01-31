"""
API Endpoints para Panel Administrativo.
========================================

Endpoints para administradores:
- GET    /admin/analyses              → Listar todos los análisis (con filtros)
- GET    /admin/analyses/{id}         → Ver análisis detallado (con datos de contacto)
- PATCH  /admin/analyses/{id}         → Ajustar ingresos/abonos
- POST   /admin/analyses/{id}/calculate → Ejecutar motor financiero
- PUT    /admin/projections/{id}      → Recalcular propuesta individual
- GET    /admin/users                 → Listar usuarios con sus análisis
- GET    /admin/stats                 → Estadísticas generales
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import Usuario
from app.models.analisis import AnalisisHipotecario
from app.models.propuesta import PropuestaAhorro
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.propuestas_repo import PropuestasRepo
from app.services.analysis_service import (
    AnalysisService,
    OpcionAbonoInput,
    get_analysis_service
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY: VERIFICAR ROL ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

from app.api.deps import require_role

# Dependencia que verifica rol ADMIN usando la tabla de roles real
verify_admin = require_role("ADMIN")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class AdminAnalysisListItem(BaseModel):
    """Item de análisis para admin con datos adicionales."""
    id: UUID
    documento_id: UUID
    
    # Datos del usuario
    usuario_id: UUID
    usuario_nombre: str | None = None
    usuario_cedula: str | None = None
    usuario_email: str | None = None
    usuario_telefono: str | None = None
    
    # Datos del crédito
    numero_credito: str | None
    banco_nombre: str | None = None
    saldo_capital_pesos: Decimal | None
    sistema_amortizacion: str | None
    
    # Estado
    status: str
    nombre_coincide: bool | None
    fecha_extracto: date | None
    created_at: datetime | None
    
    # Propuestas
    tiene_propuestas: bool = False
    max_ahorro_potencial: Decimal | None = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminAnalysisDetail(BaseModel):
    """Detalle completo de análisis para admin."""
    id: UUID
    documento_id: UUID
    usuario_id: UUID
    status: str
    
    # Datos del usuario (contacto)
    usuario_nombre: str | None
    usuario_cedula: str | None
    usuario_email: str | None
    usuario_telefono: str | None
    
    # Validaciones
    nombre_coincide: bool | None
    nombre_titular_extracto: str | None
    es_extracto_hipotecario: bool
    
    # Datos del crédito
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
    valor_cuota_con_seguros: Decimal | None
    beneficio_frech_mensual: Decimal | None
    saldo_capital_pesos: Decimal | None
    
    # UVR
    saldo_capital_uvr: Decimal | None
    valor_uvr_fecha_extracto: Decimal | None
    
    # Seguros
    seguros_total_mensual: Decimal | None
    
    # Datos del usuario
    ingresos_mensuales: Decimal | None
    capacidad_pago_max: Decimal | None
    tipo_contrato_laboral: str | None
    
    # Cálculos derivados
    total_pagado_fecha: Decimal | None
    total_frech_recibido: Decimal | None
    ajuste_inflacion_pesos: Decimal | None
    
    # Metadata
    campos_manuales: list[str] | None
    created_at: datetime | None
    
    model_config = ConfigDict(from_attributes=True)


class AdminUpdateAnalysisRequest(BaseModel):
    """Request para que admin actualice análisis."""
    ingresos_mensuales: Decimal | None = Field(None, gt=0)
    capacidad_pago_max: Decimal | None = Field(None, gt=0)
    # Admin puede sobrescribir campos que el usuario no pudo llenar
    saldo_capital_pesos: Decimal | None = Field(None, gt=0)
    cuotas_pendientes: int | None = Field(None, gt=0)
    tasa_interes_cobrada_ea: Decimal | None = Field(None, ge=0, le=1)
    valor_cuota_con_seguros: Decimal | None = Field(None, gt=0)


class AdminGenerateProjectionsRequest(BaseModel):
    """Request para que admin genere proyecciones."""
    opciones: list[dict] = Field(
        ..., 
        min_length=1,
        description="Lista de opciones: [{numero_opcion: 1, abono_adicional_mensual: 500000}]"
    )
    ingresos_override: Decimal | None = Field(None, gt=0)


class RecalculateProjectionRequest(BaseModel):
    """Request para recalcular una propuesta."""
    nuevo_abono_adicional: Decimal = Field(..., gt=0)


class ProjectionAdminResponse(BaseModel):
    """Respuesta de propuesta para admin."""
    id: UUID
    analisis_id: UUID
    numero_opcion: int
    nombre_opcion: str | None
    abono_adicional_mensual: Decimal
    
    # Resultados
    cuotas_nuevas: int | None
    tiempo_restante_anios: int | None
    tiempo_restante_meses: int | None
    cuotas_reducidas: int | None
    tiempo_ahorrado_anios: int | None
    tiempo_ahorrado_meses: int | None
    
    nuevo_valor_cuota: Decimal | None
    total_por_pagar_aprox: Decimal | None
    valor_ahorrado_intereses: Decimal | None
    veces_pagado: Decimal | None
    
    honorarios_calculados: Decimal | None
    honorarios_con_iva: Decimal | None
    ingreso_minimo_requerido: Decimal | None
    
    origen: str
    es_opcion_seleccionada: bool
    created_at: datetime | None
    
    model_config = ConfigDict(from_attributes=True)


class UserWithAnalysesItem(BaseModel):
    """Usuario con resumen de análisis."""
    id: UUID
    nombres: str | None
    primer_apellido: str | None
    identificacion: str | None
    email: str | None
    telefono: str | None
    status: str
    created_at: datetime | None
    
    # Resumen de análisis
    total_analisis: int = 0
    analisis_validados: int = 0
    total_ahorro_potencial: Decimal | None = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminStatsResponse(BaseModel):
    """Estadísticas generales para dashboard admin."""
    # Usuarios
    total_usuarios: int
    usuarios_activos: int
    usuarios_pendientes: int
    
    # Análisis
    total_analisis: int
    analisis_pendientes: int
    analisis_validados: int
    analisis_con_propuestas: int
    
    # Financiero
    total_ahorro_potencial: Decimal
    promedio_ahorro: Decimal
    total_honorarios_potenciales: Decimal


class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica."""
    items: list
    total: int
    page: int
    pages: int


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analyses", response_model=PaginatedResponse)
def list_all_analyses(
    cedula: str | None = Query(None, description="Filtrar por cédula del usuario"),
    numero_credito: str | None = Query(None, description="Filtrar por número de crédito"),
    fecha_desde: date | None = Query(None, description="Fecha extracto desde"),
    fecha_hasta: date | None = Query(None, description="Fecha extracto hasta"),
    status: str | None = Query(None, description="Filtrar por estado"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Listar todos los análisis con filtros avanzados.
    
    Filtros disponibles:
    - cedula: Búsqueda parcial por cédula del usuario
    - numero_credito: Búsqueda parcial por número de crédito
    - fecha_desde/fecha_hasta: Rango de fechas de extracto
    - status: Estado del análisis
    """
    repo = AnalysesRepo(db)
    propuestas_repo = PropuestasRepo(db)
    
    skip = (page - 1) * page_size
    
    analyses, total = repo.search_admin(
        cedula=cedula,
        numero_credito=numero_credito,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        status=status,
        skip=skip,
        limit=page_size
    )
    
    # Enriquecer con datos del usuario
    items = []
    for a in analyses:
        # Obtener usuario
        usuario = db.execute(
            select(Usuario).where(Usuario.id == a.usuario_id)
        ).scalar_one_or_none()
        
        usuario_nombre = None
        if usuario:
            usuario_nombre = f"{usuario.nombres or ''} {usuario.primer_apellido or ''}".strip()
        
        max_ahorro = propuestas_repo.get_max_ahorro(a.id)
        
        item = AdminAnalysisListItem(
            id=a.id,
            documento_id=a.documento_id,
            usuario_id=a.usuario_id,
            usuario_nombre=usuario_nombre,
            usuario_cedula=usuario.identificacion if usuario else None,
            usuario_email=usuario.email if usuario else None,
            usuario_telefono=usuario.telefono if usuario else None,
            numero_credito=a.numero_credito,
            saldo_capital_pesos=a.saldo_capital_pesos,
            sistema_amortizacion=a.sistema_amortizacion,
            status=a.status,
            nombre_coincide=a.nombre_coincide,
            fecha_extracto=a.fecha_extracto,
            created_at=a.created_at,
            tiene_propuestas=propuestas_repo.has_propuestas(a.id),
            max_ahorro_potencial=max_ahorro
        )
        items.append(item)
    
    pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        page=page,
        pages=pages
    )


@router.get("/analyses/{analysis_id}", response_model=AdminAnalysisDetail)
def get_analysis_admin(
    analysis_id: UUID,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Obtener detalle completo de un análisis incluyendo datos de contacto del usuario."""
    repo = AnalysesRepo(db)
    
    analisis = repo.get_by_id(analysis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    # Obtener usuario
    usuario = db.execute(
        select(Usuario).where(Usuario.id == analisis.usuario_id)
    ).scalar_one_or_none()
    
    usuario_nombre = None
    if usuario:
        usuario_nombre = f"{usuario.nombres or ''} {usuario.primer_apellido or ''} {usuario.segundo_apellido or ''}".strip()
    
    return AdminAnalysisDetail(
        id=analisis.id,
        documento_id=analisis.documento_id,
        usuario_id=analisis.usuario_id,
        status=analisis.status,
        usuario_nombre=usuario_nombre,
        usuario_cedula=usuario.identificacion if usuario else None,
        usuario_email=usuario.email if usuario else None,
        usuario_telefono=usuario.telefono if usuario else None,
        nombre_coincide=analisis.nombre_coincide,
        nombre_titular_extracto=analisis.nombre_titular_extracto,
        es_extracto_hipotecario=analisis.es_extracto_hipotecario,
        numero_credito=analisis.numero_credito,
        sistema_amortizacion=analisis.sistema_amortizacion,
        plan_credito=analisis.plan_credito,
        fecha_desembolso=analisis.fecha_desembolso,
        fecha_extracto=analisis.fecha_extracto,
        plazo_total_meses=analisis.plazo_total_meses,
        cuotas_pactadas=analisis.cuotas_pactadas,
        cuotas_pagadas=analisis.cuotas_pagadas,
        cuotas_pendientes=analisis.cuotas_pendientes,
        cuotas_vencidas=analisis.cuotas_vencidas,
        tasa_interes_pactada_ea=analisis.tasa_interes_pactada_ea,
        tasa_interes_cobrada_ea=analisis.tasa_interes_cobrada_ea,
        tasa_interes_subsidiada_ea=analisis.tasa_interes_subsidiada_ea,
        valor_prestado_inicial=analisis.valor_prestado_inicial,
        valor_cuota_con_seguros=analisis.valor_cuota_con_seguros,
        beneficio_frech_mensual=analisis.beneficio_frech_mensual,
        saldo_capital_pesos=analisis.saldo_capital_pesos,
        saldo_capital_uvr=analisis.saldo_capital_uvr,
        valor_uvr_fecha_extracto=analisis.valor_uvr_fecha_extracto,
        seguros_total_mensual=analisis.seguros_total_mensual,
        ingresos_mensuales=analisis.ingresos_mensuales,
        capacidad_pago_max=analisis.capacidad_pago_max,
        tipo_contrato_laboral=analisis.tipo_contrato_laboral,
        total_pagado_fecha=analisis.total_pagado_fecha,
        total_frech_recibido=analisis.total_frech_recibido,
        ajuste_inflacion_pesos=analisis.ajuste_inflacion_pesos,
        campos_manuales=analisis.campos_manuales,
        created_at=analisis.created_at
    )


@router.patch("/analyses/{analysis_id}", response_model=AdminAnalysisDetail)
def update_analysis_admin(
    analysis_id: UUID,
    request: AdminUpdateAnalysisRequest,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar campos de un análisis como administrador.
    El admin puede modificar ingresos y campos críticos para recalcular.
    """
    repo = AnalysesRepo(db)
    
    analisis = repo.get_by_id(analysis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    # Actualizar campos proporcionados
    update_data = request.model_dump(exclude_none=True)
    for field, value in update_data.items():
        if hasattr(analisis, field):
            setattr(analisis, field, value)
    
    # Recalcular campos derivados
    repo.calculate_derived_fields(analisis)
    
    # Si estaba pendiente y ahora tiene datos completos, actualizar estado
    if analisis.status == "PENDING_MANUAL":
        campos_requeridos = [
            analisis.saldo_capital_pesos,
            analisis.valor_cuota_con_seguros,
            analisis.cuotas_pendientes,
            analisis.tasa_interes_cobrada_ea
        ]
        if all(f is not None for f in campos_requeridos):
            analisis.status = "EXTRACTED"
    
    repo.save(analisis)
    db.commit()
    
    # Devolver respuesta completa
    return get_analysis_admin(analysis_id, admin, db)


@router.post("/analyses/{analysis_id}/calculate", response_model=list[ProjectionAdminResponse])
def calculate_projections_admin(
    analysis_id: UUID,
    request: AdminGenerateProjectionsRequest,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Ejecutar el motor financiero y generar proyecciones.
    El admin puede definir las opciones de abono.
    """
    service = get_analysis_service(db)
    
    # Convertir opciones
    opciones = [
        OpcionAbonoInput(
            numero_opcion=o.get("numero_opcion", i + 1),
            abono_adicional_mensual=Decimal(str(o["abono_adicional_mensual"])),
            nombre_opcion=o.get("nombre_opcion")
        )
        for i, o in enumerate(request.opciones)
    ]
    
    # Si hay override de ingresos, actualizar primero
    if request.ingresos_override:
        repo = AnalysesRepo(db)
        analisis = repo.get_by_id(analysis_id)
        if analisis:
            analisis.ingresos_mensuales = request.ingresos_override
            repo.save(analisis)
    
    result = service.generate_projections(
        analisis_id=analysis_id,
        opciones=opciones,
        usuario_id=None  # Admin puede calcular sin verificar usuario
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)
    
    return [ProjectionAdminResponse.model_validate(p) for p in result.propuestas]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - PROPUESTAS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analyses/{analysis_id}/projections", response_model=list[ProjectionAdminResponse])
def get_projections_admin(
    analysis_id: UUID,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Obtener propuestas de un análisis."""
    repo = PropuestasRepo(db)
    propuestas = repo.list_by_analisis(analysis_id)
    return [ProjectionAdminResponse.model_validate(p) for p in propuestas]


@router.put("/projections/{projection_id}", response_model=ProjectionAdminResponse)
def recalculate_projection_admin(
    projection_id: UUID,
    request: RecalculateProjectionRequest,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Recalcular una propuesta individual con nuevo abono.
    Útil para ajustes rápidos sin regenerar todas las opciones.
    """
    service = get_analysis_service(db)
    
    propuesta = service.recalculate_projection(
        propuesta_id=projection_id,
        nuevo_abono=request.nuevo_abono_adicional,
        origen="ADMIN"
    )
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    return ProjectionAdminResponse.model_validate(propuesta)


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - USUARIOS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users", response_model=PaginatedResponse)
def list_users_admin(
    search: str | None = Query(None, description="Buscar por nombre, cédula o email"),
    status: str | None = Query(None, description="Filtrar por estado"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Listar usuarios con resumen de sus análisis."""
    from sqlalchemy import or_
    
    # Query base
    query = select(Usuario)
    count_query = select(func.count(Usuario.id))
    
    conditions = []
    
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Usuario.nombres.ilike(search_pattern),
                Usuario.primer_apellido.ilike(search_pattern),
                Usuario.identificacion.ilike(search_pattern),
                Usuario.email.ilike(search_pattern)
            )
        )
    
    if status:
        conditions.append(Usuario.status == status)
    
    if conditions:
        from sqlalchemy import and_
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # Contar total
    total = db.execute(count_query).scalar() or 0
    
    # Paginación
    skip = (page - 1) * page_size
    usuarios = db.execute(
        query.order_by(Usuario.created_at.desc())
        .offset(skip)
        .limit(page_size)
    ).scalars().all()
    
    # Enriquecer con datos de análisis
    analyses_repo = AnalysesRepo(db)
    propuestas_repo = PropuestasRepo(db)
    
    items = []
    for u in usuarios:
        # Contar análisis
        total_analisis = analyses_repo.count_by_user(u.id)
        
        # Contar validados
        analisis_validados = len([
            a for a in analyses_repo.list_by_user(u.id)
            if a.status == "VALIDATED"
        ])
        
        # Calcular ahorro total potencial
        total_ahorro = Decimal("0")
        for a in analyses_repo.list_by_user(u.id):
            max_ahorro = propuestas_repo.get_max_ahorro(a.id)
            if max_ahorro:
                total_ahorro += max_ahorro
        
        item = UserWithAnalysesItem(
            id=u.id,
            nombres=u.nombres,
            primer_apellido=u.primer_apellido,
            identificacion=u.identificacion,
            email=u.email,
            telefono=u.telefono,
            status=u.status,
            created_at=u.created_at,
            total_analisis=total_analisis,
            analisis_validados=analisis_validados,
            total_ahorro_potencial=total_ahorro if total_ahorro > 0 else None
        )
        items.append(item)
    
    pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        page=page,
        pages=pages
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas generales para el dashboard administrativo."""
    # Usuarios
    total_usuarios = db.execute(select(func.count(Usuario.id))).scalar() or 0
    usuarios_activos = db.execute(
        select(func.count(Usuario.id)).where(Usuario.status == "ACTIVE")
    ).scalar() or 0
    usuarios_pendientes = db.execute(
        select(func.count(Usuario.id)).where(Usuario.status == "PENDING")
    ).scalar() or 0
    
    # Análisis
    total_analisis = db.execute(
        select(func.count(AnalisisHipotecario.id))
    ).scalar() or 0
    analisis_pendientes = db.execute(
        select(func.count(AnalisisHipotecario.id))
        .where(AnalisisHipotecario.status.in_(["PENDING_EXTRACTION", "PENDING_MANUAL"]))
    ).scalar() or 0
    analisis_validados = db.execute(
        select(func.count(AnalisisHipotecario.id))
        .where(AnalisisHipotecario.status == "VALIDATED")
    ).scalar() or 0
    
    # Análisis con propuestas
    analisis_con_propuestas = db.execute(
        select(func.count(func.distinct(PropuestaAhorro.analisis_id)))
    ).scalar() or 0
    
    # Totales financieros
    total_ahorro = db.execute(
        select(func.sum(PropuestaAhorro.valor_ahorrado_intereses))
    ).scalar() or Decimal("0")
    
    total_honorarios = db.execute(
        select(func.sum(PropuestaAhorro.honorarios_con_iva))
    ).scalar() or Decimal("0")
    
    promedio_ahorro = Decimal("0")
    if analisis_con_propuestas > 0:
        promedio_ahorro = total_ahorro / analisis_con_propuestas
    
    return AdminStatsResponse(
        total_usuarios=total_usuarios,
        usuarios_activos=usuarios_activos,
        usuarios_pendientes=usuarios_pendientes,
        total_analisis=total_analisis,
        analisis_pendientes=analisis_pendientes,
        analisis_validados=analisis_validados,
        analisis_con_propuestas=analisis_con_propuestas,
        total_ahorro_potencial=total_ahorro,
        promedio_ahorro=promedio_ahorro,
        total_honorarios_potenciales=total_honorarios
    )
