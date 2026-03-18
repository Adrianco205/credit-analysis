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
import io

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, Form, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import Usuario
from app.models.analisis import AnalisisHipotecario
from app.models.banco import Banco
from app.models.propuesta import PropuestaAhorro
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.documents_repo import DocumentsRepo
from app.repositories.propuestas_repo import PropuestasRepo
from app.repositories.admin_repo import AdminAnalysesRepo
from app.repositories.users_repo import UsersRepo
from app.schemas.admin_analysis import AdminAnalysesListResponse, AdminAnalysesParams
from app.schemas.documentos import PDFValidationResponse, PDFUploadStatus
from app.schemas.analisis import (
    ResumenCreditoResponse,
)
from app.services.analysis_service import (
    AnalysisService,
    DatosUsuarioInput,
    OpcionAbonoInput,
    get_analysis_service
)
from app.services.mortgage_summary_service import build_mortgage_summary_payload
from app.services.admin_analysis_service import AdminAnalysisService
from app.services.pdf_service import PDFStatus, PdfService
from app.services.pdf_service import get_storage_service
from app.services.proposal_pdf_service import (
    PropuestaPDFGenerator,
    DatosPropuesta,
    DatosCliente,
    DatosCredito,
    OpcionAhorro,
    generar_numero_propuesta,
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
    banco_nombre: str | None
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
    valor_cuota_con_subsidio: Decimal | None
    valor_cuota_sin_seguros: Decimal | None
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
    opciones_abono_preferidas: list[Decimal] | None
    
    # Cálculos derivados
    total_por_pagar: Decimal | None
    total_por_pagar_proyectado: Decimal | None  # Legacy
    total_por_pagar_simple: Decimal | None
    costo_total_proyectado: Decimal | None
    costo_total_proyectado_banco: Decimal | None
    total_subsidio_frech_proyectado: Decimal | None
    veces_pagado_actual: Decimal | None
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
    tasa_interes_cobrada_ea: Decimal | None = Field(None, ge=0, le=100)
    valor_prestado_inicial: Decimal | None = Field(None, gt=0)
    valor_cuota_con_subsidio: Decimal | None = Field(None, gt=0)
    valor_cuota_con_seguros: Decimal | None = Field(None, gt=0)
    valor_cuota_sin_seguros: Decimal | None = Field(None, gt=0)
    capital_pagado_periodo: Decimal | None = Field(None, ge=0)
    intereses_corrientes_periodo: Decimal | None = Field(None, ge=0)
    intereses_mora: Decimal | None = Field(None, ge=0)
    otros_cargos: Decimal | None = Field(None, ge=0)

    @model_validator(mode="after")
    def normalize_interest_rates(self):
        if self.tasa_interes_cobrada_ea is not None and self.tasa_interes_cobrada_ea > 1:
            self.tasa_interes_cobrada_ea = self.tasa_interes_cobrada_ea / Decimal("100")
        return self


class AdminGenerateProjectionsRequest(BaseModel):
    """Request para que admin genere proyecciones."""
    opciones: list[dict] = Field(
        ..., 
        min_length=1,
        description="Lista de opciones: [{numero_opcion: 1, abono_adicional_mensual: 500000}]"
    )
    ingresos_override: Decimal | None = Field(None, gt=0)
    uvr_mode: str | None = Field(
        default="extracto",
        description="Modo UVR para créditos UVR: 'extracto' o 'manual'"
    )
    uvr_manual_value: Decimal | None = Field(
        default=None,
        gt=0,
        description="Valor UVR manual a usar en proyecciones cuando uvr_mode='manual'"
    )

    @model_validator(mode="after")
    def validate_uvr_mode(self):
        mode = (self.uvr_mode or "extracto").lower().strip()
        if mode not in {"extracto", "manual"}:
            raise ValueError("uvr_mode debe ser 'extracto' o 'manual'")
        if mode == "manual" and self.uvr_manual_value is None:
            raise ValueError("uvr_manual_value es requerido cuando uvr_mode='manual'")
        self.uvr_mode = mode
        return self


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
    total_por_pagar_simple: Decimal | None = None
    costo_total_proyectado: Decimal | None = None
    costo_total_proyectado_banco: Decimal | None = None
    total_subsidio_frech_proyectado: Decimal | None = None
    valor_ahorrado_intereses: Decimal | None
    veces_pagado: Decimal | None
    
    honorarios_calculados: Decimal | None
    honorarios_con_iva: Decimal | None
    ingreso_minimo_requerido: Decimal | None
    
    origen: str
    es_opcion_seleccionada: bool
    created_at: datetime | None
    
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def derive_total_por_pagar_simple(self):
        if self.total_por_pagar_simple is None and self.nuevo_valor_cuota and self.cuotas_nuevas:
            self.total_por_pagar_simple = (self.nuevo_valor_cuota * Decimal(self.cuotas_nuevas)).quantize(Decimal("0.01"))

        # Compatibilidad legacy temporal:
        # en registros historicos, total_por_pagar_aprox almaceno costo proyectado real.
        # Esta ruta se puede retirar cuando no existan filas con:
        # costo_total_proyectado IS NULL AND total_por_pagar_aprox IS NOT NULL.
        if self.costo_total_proyectado is None and self.total_por_pagar_aprox is not None:
            if self.total_por_pagar_simple is None or self.total_por_pagar_aprox != self.total_por_pagar_simple:
                self.costo_total_proyectado = self.total_por_pagar_aprox
                if self.total_por_pagar_simple is not None:
                    self.total_por_pagar_aprox = self.total_por_pagar_simple

        if self.costo_total_proyectado is None:
            self.costo_total_proyectado = self.total_por_pagar_aprox

        if self.total_por_pagar_aprox is None:
            self.total_por_pagar_aprox = self.total_por_pagar_simple

        if self.costo_total_proyectado_banco is None:
            self.costo_total_proyectado_banco = self.costo_total_proyectado

        return self


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


class AdminCreateClientAnalysisResponse(BaseModel):
    success: bool
    analisis_id: UUID | None = None
    status: str | None = None
    message: str | None = None
    requires_manual_input: bool = False
    campos_faltantes: list[str] | None = None
    campos_extraidos: list[str] | None = None
    name_mismatch: bool = False
    id_mismatch: bool = False
    invalid_document_type: bool = False
    tipo_documento_detectado: str | None = None


def _normalize_rate_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value / Decimal("100") if value > 1 else value


def _split_full_name(full_name: str) -> tuple[str, str | None, str | None]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return "", None, None
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) == 3:
        return " ".join(parts[:2]), parts[2], None
    return " ".join(parts[:-2]), parts[-2], parts[-1]


@router.post("/clients/upload-analysis", response_model=AdminCreateClientAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def upload_client_analysis_for_admin(
    customer_full_name: str = Form(..., min_length=3, max_length=200),
    customer_id_number: str = Form(..., min_length=5, max_length=30),
    customer_email: str = Form(..., min_length=5, max_length=255),
    customer_phone: str = Form(..., min_length=7, max_length=30),
    ingresos_mensuales: Decimal = Form(..., gt=0),
    capacidad_pago_max: Decimal | None = Form(None, gt=0),
    tipo_contrato_laboral: str | None = Form(None, max_length=80),
    banco_id: int = Form(...),
    opcion_abono_1: Decimal | None = Form(None, gt=0),
    opcion_abono_2: Decimal | None = Form(None, gt=0),
    opcion_abono_3: Decimal | None = Form(None, gt=0),
    file: UploadFile = File(..., description="Archivo PDF del análisis del cliente"),
    password: str | None = Form(None, description="Contraseña del PDF, si aplica"),
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    _ = admin

    normalized_name = customer_full_name.strip()
    normalized_id = customer_id_number.strip()
    normalized_email = customer_email.strip().lower()
    normalized_phone = customer_phone.strip()

    if not normalized_name:
        raise HTTPException(status_code=400, detail="El nombre del cliente es obligatorio")
    if not normalized_id:
        raise HTTPException(status_code=400, detail="La cédula del cliente es obligatoria")
    if not normalized_email:
        raise HTTPException(status_code=400, detail="El correo del cliente es obligatorio")
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="El teléfono del cliente es obligatorio")

    banco = db.get(Banco, banco_id)
    if not banco or not banco.activo:
        raise HTTPException(status_code=400, detail="El banco seleccionado no es válido")

    users_repo = UsersRepo(db)
    user_by_id = users_repo.get_by_identificacion(normalized_id)
    user_by_email = users_repo.get_by_email(normalized_email)

    if user_by_id and user_by_email and user_by_id.id != user_by_email.id:
        raise HTTPException(
            status_code=409,
            detail="La cédula y el correo pertenecen a clientes diferentes",
        )

    customer_user = user_by_id or user_by_email

    nombres, primer_apellido, segundo_apellido = _split_full_name(normalized_name)

    if customer_user:
        customer_user.nombres = nombres
        customer_user.primer_apellido = primer_apellido
        customer_user.segundo_apellido = segundo_apellido
        customer_user.identificacion = normalized_id
        customer_user.email = normalized_email
        customer_user.telefono = normalized_phone
        if customer_user.status != "ACTIVE":
            customer_user.status = "INVITED"
            customer_user.email_verificado = False
            customer_user.password_hash = None
        db.add(customer_user)
        db.commit()
        db.refresh(customer_user)
    else:
        customer_user = Usuario(
            nombres=nombres,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            tipo_identificacion="CC",
            identificacion=normalized_id,
            email=normalized_email,
            telefono=normalized_phone,
            status="INVITED",
            email_verificado=False,
            password_hash=None,
        )
        customer_user = users_repo.create_user(customer_user)

    users_repo.ensure_role_assignment(customer_user.id, "CLIENT")

    if file.content_type and file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo debe ser un PDF. Tipo recibido: {file.content_type}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")

    pdf_service = PdfService()
    storage_service = get_storage_service()
    documents_repo = DocumentsRepo(db)

    file_stream = io.BytesIO(content)
    validation_result = pdf_service.validate_pdf(file_stream, check_keywords=False)

    validation_response = PDFValidationResponse(
        is_valid=validation_result.is_valid,
        status=PDFUploadStatus(validation_result.status.value),
        message=validation_result.message,
        requires_password=validation_result.status == PDFStatus.ENCRYPTED,
        page_count=validation_result.page_count,
        file_size_bytes=validation_result.file_size_bytes,
        has_credit_keywords=validation_result.has_credit_keywords,
        keyword_confidence=validation_result.keyword_confidence,
    )

    if validation_result.status == PDFStatus.ENCRYPTED and not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "PDF_PASSWORD_REQUIRED",
                "message": "El PDF está protegido con contraseña. Por favor proporciona la contraseña.",
                "requires_password": True,
            },
        )

    if not validation_result.is_valid and validation_result.status != PDFStatus.ENCRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation_result.message)

    content_to_save = content
    was_encrypted = False

    if validation_result.status == PDFStatus.ENCRYPTED and password:
        file_stream.seek(0)
        decrypt_result = pdf_service.decrypt_pdf(file_stream, password)
        if not decrypt_result.success:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "PDF_INVALID_PASSWORD",
                    "message": decrypt_result.message,
                    "requires_password": True,
                },
            )

        content_to_save = decrypt_result.decrypted_content
        was_encrypted = True
        validation_response.status = PDFUploadStatus.DECRYPTED
        validation_response.message = "PDF desencriptado y guardado sin contraseña"
        validation_response.page_count = decrypt_result.page_count
        validation_response.requires_password = False

    save_result = storage_service.save_pdf(
        content=content_to_save,
        user_id=str(customer_user.id),
        original_filename=file.filename or "extracto.pdf",
    )

    if not save_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo: {save_result.message}",
        )

    documento = documents_repo.create(
        usuario_id=customer_user.id,
        original_filename=file.filename or "extracto.pdf",
        file_size=save_result.file_size_bytes,
        s3_key=save_result.file_path,
        checksum=save_result.checksum,
        pdf_encrypted=was_encrypted,
        status="UPLOADED",
        banco_id=banco_id,
    )

    service = get_analysis_service(db)
    opciones_abono_preferidas = [
        option for option in [opcion_abono_1, opcion_abono_2, opcion_abono_3] if option is not None
    ] or None

    result = await service.create_analysis_from_document(
        documento_id=documento.id,
        usuario=customer_user,
        datos_usuario=DatosUsuarioInput(
            ingresos_mensuales=ingresos_mensuales,
            capacidad_pago_max=capacidad_pago_max,
            tipo_contrato_laboral=tipo_contrato_laboral,
            opciones_abono_preferidas=opciones_abono_preferidas,
        ),
        skip_name_validation=True,
        skip_id_validation=True,
        allow_non_credit_document=True,
        banco_id=banco_id,
    )

    if not result.success:
        raise HTTPException(
            status_code=422,
            detail=result.error_message or "No se pudo crear el análisis para el cliente",
        )

    return AdminCreateClientAnalysisResponse(
        success=True,
        analisis_id=result.analisis.id if result.analisis else None,
        status=result.analisis.status if result.analisis else None,
        message="Análisis del cliente creado exitosamente",
        requires_manual_input=result.requires_manual_input,
        campos_faltantes=result.campos_faltantes,
        campos_extraidos=result.campos_extraidos,
        name_mismatch=result.name_mismatch,
        id_mismatch=result.id_mismatch,
        invalid_document_type=result.invalid_document_type,
        tipo_documento_detectado=result.tipo_documento_detectado,
    )


@router.post("/analyses/manual-projection", response_model=AdminCreateClientAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_projection_analysis(
    customer_full_name: str = Form(..., min_length=3, max_length=200),
    customer_id_number: str = Form(..., min_length=5, max_length=30),
    customer_email: str = Form(..., min_length=5, max_length=255),
    customer_phone: str = Form(..., min_length=7, max_length=30),
    ingresos_mensuales: Decimal = Form(..., gt=0),
    capacidad_pago_max: Decimal | None = Form(None, gt=0),
    tipo_contrato_laboral: str | None = Form(None, max_length=80),
    banco_id: int = Form(...),
    opcion_abono_1: Decimal | None = Form(None, gt=0),
    opcion_abono_2: Decimal | None = Form(None, gt=0),
    opcion_abono_3: Decimal | None = Form(None, gt=0),
    numero_credito: str = Form(..., min_length=3, max_length=50),
    sistema_amortizacion: str = Form(..., min_length=3, max_length=20),
    plan_credito: str | None = Form(None, max_length=100),
    valor_prestado_inicial: Decimal = Form(..., gt=0),
    fecha_desembolso: date | None = Form(None),
    fecha_extracto: date = Form(...),
    plazo_total_meses: int = Form(..., gt=0),
    cuotas_pactadas: int = Form(..., gt=0),
    cuotas_pagadas: int = Form(..., ge=0),
    cuotas_pendientes: int = Form(..., ge=0),
    tasa_interes_pactada_ea: Decimal | None = Form(None, ge=0),
    tasa_interes_cobrada_ea: Decimal = Form(..., ge=0),
    tasa_interes_subsidiada_ea: Decimal | None = Form(None, ge=0),
    tasa_mora_pactada_ea: Decimal | None = Form(None, ge=0),
    valor_cuota_sin_seguros: Decimal | None = Form(None, ge=0),
    valor_cuota_con_seguros: Decimal = Form(..., gt=0),
    beneficio_frech_mensual: Decimal | None = Form(None, ge=0),
    valor_cuota_con_subsidio: Decimal | None = Form(None, ge=0),
    saldo_capital_pesos: Decimal = Form(..., gt=0),
    total_por_pagar: Decimal | None = Form(None, ge=0),
    saldo_capital_uvr: Decimal | None = Form(None, ge=0),
    valor_uvr_fecha_extracto: Decimal | None = Form(None, ge=0),
    valor_cuota_uvr: Decimal | None = Form(None, ge=0),
    seguro_vida: Decimal | None = Form(None, ge=0),
    seguro_incendio: Decimal | None = Form(None, ge=0),
    seguro_terremoto: Decimal | None = Form(None, ge=0),
    capital_pagado_periodo: Decimal | None = Form(None, ge=0),
    intereses_corrientes_periodo: Decimal | None = Form(None, ge=0),
    intereses_mora: Decimal | None = Form(None, ge=0),
    otros_cargos: Decimal | None = Form(None, ge=0),
    file: UploadFile = File(..., description="Archivo PDF del análisis del cliente"),
    password: str | None = Form(None, description="Contraseña del PDF, si aplica"),
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    _ = admin

    normalized_name = customer_full_name.strip()
    normalized_id = customer_id_number.strip()
    normalized_email = customer_email.strip().lower()
    normalized_phone = customer_phone.strip()

    if not normalized_name:
        raise HTTPException(status_code=400, detail="El nombre del cliente es obligatorio")
    if not normalized_id:
        raise HTTPException(status_code=400, detail="La cédula del cliente es obligatoria")
    if not normalized_email:
        raise HTTPException(status_code=400, detail="El correo del cliente es obligatorio")
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="El teléfono del cliente es obligatorio")

    banco = db.get(Banco, banco_id)
    if not banco or not banco.activo:
        raise HTTPException(status_code=400, detail="El banco seleccionado no es válido")

    users_repo = UsersRepo(db)
    customer_user = users_repo.get_by_email(normalized_email)
    if customer_user is None:
        existing_by_id = users_repo.get_by_identificacion(normalized_id)
        if existing_by_id:
            customer_user = existing_by_id

    if customer_user is None:
        nombres, primer_apellido, segundo_apellido = _split_full_name(normalized_name)
        customer_user = Usuario(
            nombres=nombres,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            tipo_identificacion="CC",
            identificacion=normalized_id,
            email=normalized_email,
            telefono=normalized_phone,
            status="INVITED",
            email_verificado=False,
        )
        db.add(customer_user)
        db.flush()
    else:
        updated = False
        if not customer_user.identificacion:
            customer_user.identificacion = normalized_id
            updated = True
        if not customer_user.telefono:
            customer_user.telefono = normalized_phone
            updated = True
        if updated:
            db.add(customer_user)
            db.flush()

    pdf_service = PdfService()
    storage_service = get_storage_service()
    documents_repo = DocumentsRepo(db)
    analyses_repo = AnalysesRepo(db)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo PDF está vacío")

    validation = pdf_service.validate_and_prepare_pdf(file_bytes, password=password)
    if validation.status == PDFStatus.PASSWORD_REQUIRED:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "El PDF está protegido con contraseña. Debes suministrarla para continuar.",
                "requires_password": True,
            },
        )

    if validation.status == PDFStatus.INVALID_PASSWORD:
        raise HTTPException(status_code=400, detail="Contraseña de PDF inválida")

    if validation.status != PDFStatus.OK or not validation.content_to_store:
        raise HTTPException(
            status_code=400,
            detail=validation.message or "No se pudo procesar el archivo PDF",
        )

    content_to_save = validation.content_to_store
    was_encrypted = validation.was_encrypted

    save_result = storage_service.save_pdf(
        content=content_to_save,
        user_id=str(customer_user.id),
        original_filename=file.filename or "extracto.pdf",
    )

    if not save_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo: {save_result.message}",
        )

    documento = documents_repo.create(
        usuario_id=customer_user.id,
        original_filename=file.filename or "extracto.pdf",
        file_size=save_result.file_size_bytes,
        s3_key=save_result.file_path,
        checksum=save_result.checksum,
        pdf_encrypted=was_encrypted,
        status="UPLOADED",
        banco_id=banco_id,
    )

    opciones_abono_preferidas = [
        option for option in [opcion_abono_1, opcion_abono_2, opcion_abono_3] if option is not None
    ] or None

    seguros_total_mensual = (seguro_vida or Decimal("0")) + (seguro_incendio or Decimal("0")) + (seguro_terremoto or Decimal("0"))

    analisis_data = {
        "documento_id": documento.id,
        "usuario_id": customer_user.id,
        "ingresos_mensuales": ingresos_mensuales,
        "capacidad_pago_max": capacidad_pago_max,
        "tipo_contrato_laboral": tipo_contrato_laboral,
        "numero_credito": numero_credito.strip(),
        "banco_id": banco_id,
        "sistema_amortizacion": sistema_amortizacion.strip().upper(),
        "plan_credito": plan_credito,
        "valor_prestado_inicial": valor_prestado_inicial,
        "fecha_desembolso": fecha_desembolso,
        "fecha_extracto": fecha_extracto,
        "plazo_total_meses": plazo_total_meses,
        "cuotas_pactadas": cuotas_pactadas,
        "cuotas_pagadas": cuotas_pagadas,
        "cuotas_pendientes": cuotas_pendientes,
        "tasa_interes_pactada_ea": _normalize_rate_decimal(tasa_interes_pactada_ea),
        "tasa_interes_cobrada_ea": _normalize_rate_decimal(tasa_interes_cobrada_ea),
        "tasa_interes_subsidiada_ea": _normalize_rate_decimal(tasa_interes_subsidiada_ea),
        "tasa_mora_pactada_ea": _normalize_rate_decimal(tasa_mora_pactada_ea),
        "valor_cuota_sin_seguros": valor_cuota_sin_seguros,
        "valor_cuota_con_seguros": valor_cuota_con_seguros,
        "beneficio_frech_mensual": beneficio_frech_mensual,
        "valor_cuota_con_subsidio": valor_cuota_con_subsidio,
        "saldo_capital_pesos": saldo_capital_pesos,
        "total_por_pagar": total_por_pagar,
        "saldo_capital_uvr": saldo_capital_uvr,
        "valor_uvr_fecha_extracto": valor_uvr_fecha_extracto,
        "valor_cuota_uvr": valor_cuota_uvr,
        "seguro_vida": seguro_vida,
        "seguro_incendio": seguro_incendio,
        "seguro_terremoto": seguro_terremoto,
        "seguros_total_mensual": seguros_total_mensual,
        "capital_pagado_periodo": capital_pagado_periodo,
        "intereses_corrientes_periodo": intereses_corrientes_periodo,
        "intereses_mora": intereses_mora,
        "otros_cargos": otros_cargos,
        "opciones_abono_preferidas": opciones_abono_preferidas,
        "nombre_titular_extracto": normalized_name,
        "identificacion_extracto": normalized_id,
        "nombre_coincide": True,
        "cedula_coincide": True,
        "status": "EXTRACTED",
        "campos_manuales": [
            "numero_credito", "sistema_amortizacion", "plan_credito", "valor_prestado_inicial",
            "fecha_desembolso", "fecha_extracto", "plazo_total_meses", "cuotas_pactadas",
            "cuotas_pagadas", "cuotas_pendientes", "tasa_interes_pactada_ea", "tasa_interes_cobrada_ea",
            "tasa_interes_subsidiada_ea", "tasa_mora_pactada_ea", "valor_cuota_sin_seguros",
            "valor_cuota_con_seguros", "beneficio_frech_mensual", "valor_cuota_con_subsidio",
            "saldo_capital_pesos", "total_por_pagar", "saldo_capital_uvr", "valor_uvr_fecha_extracto",
            "valor_cuota_uvr", "seguro_vida", "seguro_incendio", "seguro_terremoto",
            "capital_pagado_periodo", "intereses_corrientes_periodo", "intereses_mora", "otros_cargos"
        ],
        "campos_extraidos_ia": [],
        "raw_data_json": {"manual_entry": True, "created_by": "admin"},
        "computed_summary_json": {"manual_entry": True},
        "datos_raw_gemini": None,
    }

    analisis = analyses_repo.create(**analisis_data)
    analyses_repo.calculate_derived_fields(analisis)
    db.commit()

    return AdminCreateClientAnalysisResponse(
        success=True,
        analisis_id=analisis.id,
        status=analisis.status,
        message="Análisis manual creado exitosamente",
        requires_manual_input=False,
        campos_faltantes=None,
        campos_extraidos=[],
        name_mismatch=False,
        id_mismatch=False,
        invalid_document_type=False,
        tipo_documento_detectado=None,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS - ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analyses", response_model=AdminAnalysesListResponse)
def list_all_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    customer_id_number: str | None = Query(None, description="Filtro por cédula (contiene)"),
    customer_name: str | None = Query(None, description="Filtro por nombre/apellidos (contiene, case-insensitive)"),
    credit_number: str | None = Query(None, description="Filtro por número de crédito"),
    bank_id: int | None = Query(None, description="Filtro por banco"),
    uploaded_from: datetime | None = Query(None, description="Fecha/hora inicial de subida"),
    uploaded_to: datetime | None = Query(None, description="Fecha/hora final de subida"),
    sort_by: str = Query("uploaded_at", description="uploaded_at|customer_name|bank_name|credit_number"),
    sort_dir: str = Query("desc", description="asc|desc"),
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Historial administrativo de análisis (server-side: paginación, filtros y orden)."""
    _ = admin
    params = AdminAnalysesParams(
        page=page,
        page_size=page_size,
        customer_id_number=customer_id_number,
        customer_name=customer_name,
        credit_number=credit_number,
        bank_id=bank_id,
        uploaded_from=uploaded_from,
        uploaded_to=uploaded_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    service = AdminAnalysisService(AdminAnalysesRepo(db))
    return service.list_analyses(params)


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
        analisis = repo.get_by_documento(analysis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    # Obtener usuario
    usuario = db.execute(
        select(Usuario).where(Usuario.id == analisis.usuario_id)
    ).scalar_one_or_none()
    
    usuario_nombre = None
    if usuario:
        usuario_nombre = f"{usuario.nombres or ''} {usuario.primer_apellido or ''} {usuario.segundo_apellido or ''}".strip()

    banco_nombre = None
    if analisis.banco_id:
        banco = db.get(Banco, analisis.banco_id)
        if banco and banco.nombre:
            banco_nombre = banco.nombre

    total_por_pagar_proyectado: Decimal | None = None
    costo_total_proyectado: Decimal | None = None
    costo_total_proyectado_banco: Decimal | None = None
    total_subsidio_frech_proyectado: Decimal | None = None
    total_por_pagar_simple: Decimal | None = None
    veces_pagado_actual: Decimal | None = None
    try:
        # Fuente de verdad para "Límites hoy": proyección financiera mes a mes (abono = 0).
        service = get_analysis_service(db)
        baseline = service._calculate_baseline(analisis)
        total_por_pagar_proyectado = baseline.get("total_actual")
        costo_total_proyectado = baseline.get("costo_total_proyectado")
        costo_total_proyectado_banco = baseline.get("costo_total_proyectado_banco")
        total_subsidio_frech_proyectado = baseline.get("total_subsidio_frech_proyectado")
        total_por_pagar_simple = baseline.get("total_actual_simple")
        veces_pagado_actual = baseline.get("veces_pagado_actual")
    except Exception as exc:
        logger.warning("No se pudo calcular baseline proyectado para admin detail %s: %s", analysis_id, exc)

    if veces_pagado_actual is None:
        veces_pagado_actual = (
            (analisis.total_por_pagar / analisis.saldo_capital_pesos).quantize(Decimal("0.01"))
            if analisis.total_por_pagar is not None and analisis.saldo_capital_pesos and analisis.saldo_capital_pesos > 0
            else None
        )
    
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
        banco_nombre=banco_nombre,
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
        valor_cuota_con_subsidio=analisis.valor_cuota_con_subsidio,
        valor_cuota_sin_seguros=analisis.valor_cuota_sin_seguros,
        valor_cuota_con_seguros=analisis.valor_cuota_con_seguros,
        beneficio_frech_mensual=analisis.beneficio_frech_mensual,
        saldo_capital_pesos=analisis.saldo_capital_pesos,
        saldo_capital_uvr=analisis.saldo_capital_uvr,
        valor_uvr_fecha_extracto=analisis.valor_uvr_fecha_extracto,
        seguros_total_mensual=analisis.seguros_total_mensual,
        ingresos_mensuales=analisis.ingresos_mensuales,
        capacidad_pago_max=analisis.capacidad_pago_max,
        tipo_contrato_laboral=analisis.tipo_contrato_laboral,
        opciones_abono_preferidas=analisis.opciones_abono_preferidas,
        total_por_pagar=analisis.total_por_pagar,
        total_por_pagar_proyectado=total_por_pagar_proyectado,
        total_por_pagar_simple=total_por_pagar_simple,
        costo_total_proyectado=costo_total_proyectado,
        costo_total_proyectado_banco=costo_total_proyectado_banco,
        total_subsidio_frech_proyectado=total_subsidio_frech_proyectado,
        veces_pagado_actual=veces_pagado_actual,
        total_pagado_fecha=analisis.total_pagado_fecha,
        total_frech_recibido=analisis.total_frech_recibido,
        ajuste_inflacion_pesos=analisis.ajuste_inflacion_pesos,
        campos_manuales=analisis.campos_manuales,
        created_at=analisis.created_at
    )


@router.get("/analyses/{analysis_id}/summary", response_model=ResumenCreditoResponse)
def get_analysis_admin_summary(
    analysis_id: UUID,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Resumen del análisis para admin (equivalente al flujo cliente, pero sin restricción de propietario)."""
    _ = admin
    repo = AnalysesRepo(db)

    analisis = repo.get_by_id(analysis_id)
    if not analisis:
        analisis = repo.get_by_documento(analysis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    repo.calculate_derived_fields(analisis)
    db.commit()

    summary_payload = build_mortgage_summary_payload(analisis)

    sistema_completo = analisis.sistema_amortizacion or ""
    if analisis.plan_credito:
        sistema_completo = f"{analisis.sistema_amortizacion} - {analisis.plan_credito}"

    return ResumenCreditoResponse(
        analisis_id=analisis.id,
        numero_credito=analisis.numero_credito,
        nombre_titular=analisis.nombre_titular_extracto,
        banco_nombre=None,
        sistema_amortizacion=sistema_completo,
        fecha_extracto=analisis.fecha_extracto,
        datos_basicos=summary_payload["datos_basicos"],
        limites_banco=summary_payload["limites_banco"],
        ajuste_inflacion=summary_payload["ajuste_inflacion"],
        costos_extra=summary_payload["costos_extra"],
        mortgage_summary=summary_payload["mortgage_summary"],
        warnings=summary_payload["warnings"],
        debug=summary_payload["debug"],
        tasa_cobrada_con_frech=analisis.tasa_interes_subsidiada_ea,
        seguros_actuales_mensual=analisis.seguros_total_mensual,
        ingresos_mensuales=analisis.ingresos_mensuales,
        capacidad_pago_max=analisis.capacidad_pago_max,
        is_total_paid_estimated=analisis.is_total_paid_estimated,
    )


@router.get("/documents/{document_id}/download")
def admin_download_document(
    document_id: UUID,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """Descarga PDF para admin sin restricción de propietario."""
    _ = admin
    documents_repo = DocumentsRepo(db)
    storage_service = get_storage_service()

    documento = documents_repo.get_by_id(document_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if not documento.s3_key:
        raise HTTPException(status_code=404, detail="El documento no tiene archivo asociado")

    pdf_content = storage_service.get_pdf(documento.s3_key)
    if not pdf_content:
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en storage")

    filename = documento.original_filename or "extracto.pdf"
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    campos_manuales_actualizados: list[str] = []

    campos_no_manual = {"ingresos_mensuales", "capacidad_pago_max", "tipo_contrato_laboral", "opciones_abono_preferidas"}
    for field, value in update_data.items():
        if hasattr(analisis, field):
            setattr(analisis, field, value)
            if field not in campos_no_manual:
                campos_manuales_actualizados.append(field)

    if campos_manuales_actualizados:
        existentes = analisis.campos_manuales or []
        analisis.campos_manuales = list(set(existentes + campos_manuales_actualizados))
    
    # Recalcular campos derivados
    repo.calculate_derived_fields(analisis)
    
    # Si estaba pendiente y ahora tiene datos completos, actualizar estado
    if analisis.status == "PENDING_MANUAL":
        cuota_disponible = (
            analisis.valor_cuota_con_subsidio
            or analisis.valor_cuota_con_seguros
            or analisis.valor_cuota_sin_seguros
        )
        campos_requeridos = [
            analisis.saldo_capital_pesos,
            cuota_disponible,
            analisis.cuotas_pendientes,
            analisis.tasa_interes_cobrada_ea,
            analisis.valor_prestado_inicial,
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
        usuario_id=None,  # Admin puede calcular sin verificar usuario
        valor_uvr_para_calculo=request.uvr_manual_value if request.uvr_mode == "manual" else None,
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


@router.get(
    "/analyses/{analysis_id}/proposal/pdf",
    summary="Descargar propuesta PDF (admin)",
    description="Genera y descarga el PDF de proyecciones para uso administrativo.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF de propuesta administrativa"
        }
    }
)
def download_admin_proposal_pdf(
    analysis_id: UUID,
    admin: Usuario = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Genera y descarga el PDF de propuesta para administradores.
    Incluye datos del cliente, crédito, proyecciones y honorarios.
    """
    _ = admin
    analyses_repo = AnalysesRepo(db)
    analisis = analyses_repo.get_by_id(analysis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    propuestas_repo = PropuestasRepo(db)
    propuestas = propuestas_repo.list_by_analisis(analysis_id)

    if not propuestas:
        raise HTTPException(
            status_code=400,
            detail="El análisis no tiene proyecciones generadas para exportar."
        )

    usuario = db.execute(
        select(Usuario).where(Usuario.id == analisis.usuario_id)
    ).scalar_one_or_none()

    nombre_completo = "No registrado"
    if usuario:
        nombre_completo = " ".join(
            [
                usuario.nombres or "",
                usuario.primer_apellido or "",
                usuario.segundo_apellido or "",
            ]
        ).strip() or "No registrado"

    datos_cliente = DatosCliente(
        nombre_completo=nombre_completo,
        cedula=usuario.identificacion if usuario and usuario.identificacion else "No registrada",
        email=usuario.email if usuario and usuario.email else "No registrado",
        telefono=usuario.telefono if usuario else None,
        ingresos_mensuales=analisis.ingresos_mensuales or Decimal("0"),
    )

    banco_nombre = "No especificado"
    if analisis.banco_id:
        banco = db.get(Banco, analisis.banco_id)
        if banco and banco.nombre:
            banco_nombre = banco.nombre

    cuota_mensual = analisis.valor_cuota_con_seguros or analisis.valor_cuota_sin_seguros or Decimal("0")
    tasa_interes = analisis.tasa_interes_cobrada_ea or analisis.tasa_interes_pactada_ea or Decimal("0")

    baseline = None
    try:
        service = get_analysis_service(db)
        baseline = service._calculate_baseline(analisis)
    except Exception as exc:
        logger.warning("No se pudo calcular baseline para PDF admin %s: %s", analysis_id, exc)

    cuota_visible = baseline.get("cuota_actual_visible") if baseline else None
    costo_total_proyectado_banco_actual = baseline.get("costo_total_proyectado_banco") if baseline else None
    veces_pagado_actual = baseline.get("veces_pagado_actual") if baseline else None

    datos_credito = DatosCredito(
        numero_credito=analisis.numero_credito or "No especificado",
        banco=banco_nombre,
        saldo_capital=analisis.saldo_capital_pesos or Decimal("0"),
        tasa_interes_ea=tasa_interes,
        cuota_mensual=cuota_visible or cuota_mensual,
        cuotas_pendientes=analisis.cuotas_pendientes or 0,
        cuotas_pagadas=analisis.cuotas_pagadas or 0,
        fecha_desembolso=analisis.fecha_desembolso,
        sistema_amortizacion=analisis.sistema_amortizacion or "PESOS",
        costo_total_proyectado_banco_actual=costo_total_proyectado_banco_actual,
        veces_pagado_actual=veces_pagado_actual,
    )

    opciones: list[OpcionAhorro] = []
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
            costo_total_proyectado_banco=p.costo_total_proyectado_banco or p.costo_total_proyectado,
            veces_pagado=p.veces_pagado,
            cuotas_reducidas=p.cuotas_reducidas or 0,
        )
        opciones.append(opcion)

    opciones.sort(key=lambda x: x.numero_opcion)

    fecha_generacion = datetime.now()
    datos_propuesta = DatosPropuesta(
        cliente=datos_cliente,
        credito=datos_credito,
        opciones=opciones,
        fecha_generacion=fecha_generacion,
        numero_propuesta=generar_numero_propuesta(str(analysis_id), fecha_generacion),
    )

    try:
        generator = PropuestaPDFGenerator()
        pdf_bytes = generator.generar_propuesta(datos_propuesta)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando PDF: {str(e)}"
        )

    filename = f"propuesta_admin_perfinanzas_{analysis_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(pdf_bytes)),
        }
    )


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



