"""Creación de análisis hipotecarios cargados manualmente por un admin.

Reutiliza exactamente la misma cadena de cálculo del flujo automático
(`calculate_derived_fields` → `normalize_credit_snapshot` → motores de
proyección).  Lo único que cambia es el origen de los datos: en vez de la
extracción con IA, los digita un administrador.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.analisis import AnalisisHipotecario
from app.models.banco import Banco
from app.models.user import Usuario
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.documents_repo import DocumentsRepo
from app.repositories.users_repo import UsersRepo
from app.schemas.manual_projection import ManualProjectionInput
from app.services.pdf_service import PDFStatus, PdfService, get_storage_service

logger = logging.getLogger(__name__)

# Estado con el que queda un crédito digitado y verificado por un administrador.
MANUAL_VALIDATION_STATUS = "VALIDATED_MANUAL"

# Campos que en el flujo automático vendrían de la extracción y que aquí
# provienen íntegramente del formulario.
MANUAL_FIELDS = (
    "numero_credito", "sistema_amortizacion", "plan_credito", "valor_prestado_inicial",
    "fecha_desembolso", "fecha_extracto", "plazo_total_meses", "cuotas_pactadas",
    "cuotas_pagadas", "cuotas_pendientes", "cuotas_vencidas", "tasa_interes_pactada_ea",
    "tasa_interes_cobrada_ea", "tasa_interes_subsidiada_ea", "tasa_mora_pactada_ea",
    "valor_cuota_sin_seguros", "valor_cuota_con_seguros", "beneficio_frech_mensual",
    "valor_cuota_con_subsidio", "saldo_capital_pesos", "total_por_pagar",
    "saldo_capital_uvr", "valor_uvr_fecha_extracto", "valor_cuota_uvr",
    "seguro_vida", "seguro_incendio", "seguro_terremoto", "capital_pagado_periodo",
    "intereses_corrientes_periodo", "intereses_mora", "otros_cargos",
    "total_pagado_fecha", "total_frech_recibido", "monto_real_pagado_banco",
)


class ManualProjectionError(Exception):
    """Error de negocio con un mensaje presentable para el admin."""

    def __init__(self, message: str, status_code: int = 400, payload: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.payload = payload
        super().__init__(message)


@dataclass
class ManualProjectionResult:
    analisis: AnalisisHipotecario
    customer: Usuario
    created_customer: bool


def _normalize_identity_value(value: str | None) -> str:
    if not value:
        return ""
    return value.replace(".", "").replace("-", "").replace(" ", "").strip()


def split_full_name(full_name: str) -> tuple[str, str | None, str | None]:
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


class ManualProjectionService:
    def __init__(self, db: Session):
        self.db = db
        self.users_repo = UsersRepo(db)
        self.documents_repo = DocumentsRepo(db)
        self.analyses_repo = AnalysesRepo(db)
        self.pdf_service = PdfService()
        self.storage_service = get_storage_service()

    # ── Cliente ────────────────────────────────────────────────────────────

    def resolve_customer(self, data: ManualProjectionInput) -> tuple[Usuario, bool]:
        """Reutiliza el cliente existente o lo crea como invitado."""
        identificacion = data.customer_id_number
        email = data.customer_email

        user_by_id = self.users_repo.get_by_identificacion(identificacion)
        user_by_email = self.users_repo.get_by_email(email)

        if user_by_id and user_by_email and user_by_id.id != user_by_email.id:
            raise ManualProjectionError(
                "La cédula y el correo pertenecen a clientes diferentes", status_code=409
            )

        if user_by_email:
            stored_id = _normalize_identity_value(user_by_email.identificacion)
            incoming_id = _normalize_identity_value(identificacion)
            if stored_id and incoming_id and stored_id != incoming_id:
                raise ManualProjectionError(
                    "El correo ya está asociado a otra cédula", status_code=409
                )

        if user_by_id:
            stored_email = (user_by_id.email or "").strip().lower()
            if stored_email and stored_email != email:
                raise ManualProjectionError(
                    "La cédula ya está asociada a otro correo", status_code=409
                )

        nombres, primer_apellido, segundo_apellido = split_full_name(data.customer_full_name)
        customer = user_by_id or user_by_email
        created = customer is None

        if created:
            customer = Usuario(
                tipo_identificacion="CC",
                status="INVITED",
                email_verificado=False,
                password_hash=None,
            )

        customer.nombres = nombres
        customer.primer_apellido = primer_apellido
        customer.segundo_apellido = segundo_apellido
        customer.identificacion = identificacion
        customer.email = email
        customer.telefono = data.customer_phone
        if customer.status != "ACTIVE":
            customer.status = "INVITED"
            customer.email_verificado = False
            customer.password_hash = None

        self.db.add(customer)
        self.db.flush()
        self.users_repo.ensure_role_assignment(customer.id, "CLIENT")

        return customer, created

    # ── PDF ────────────────────────────────────────────────────────────────

    def store_statement_pdf(
        self,
        *,
        customer: Usuario,
        banco_id: int,
        content: bytes,
        filename: str,
        password: str | None,
    ):
        """Valida, desencripta si aplica y persiste el extracto."""
        if not content:
            raise ManualProjectionError("El archivo PDF está vacío")

        file_stream = io.BytesIO(content)
        validation = self.pdf_service.validate_pdf(file_stream, check_keywords=False)

        if validation.status == PDFStatus.ENCRYPTED and not password:
            raise ManualProjectionError(
                "El PDF está protegido con contraseña. Ingresa la contraseña para continuar.",
                status_code=422,
                payload={"error": "PDF_PASSWORD_REQUIRED", "requires_password": True},
            )

        if not validation.is_valid and validation.status != PDFStatus.ENCRYPTED:
            raise ManualProjectionError(validation.message)

        content_to_save = content
        was_encrypted = False

        if validation.status == PDFStatus.ENCRYPTED and password:
            file_stream.seek(0)
            decrypted = self.pdf_service.decrypt_pdf(file_stream, password)
            if not decrypted.success:
                raise ManualProjectionError(
                    decrypted.message,
                    status_code=422,
                    payload={"error": "PDF_INVALID_PASSWORD", "requires_password": True},
                )
            content_to_save = decrypted.decrypted_content
            was_encrypted = True

        save_result = self.storage_service.save_pdf(
            content=content_to_save,
            user_id=str(customer.id),
            original_filename=filename,
        )

        if not save_result.success:
            raise ManualProjectionError(
                f"Error al guardar el archivo: {save_result.message}", status_code=500
            )

        return self.documents_repo.create(
            usuario_id=customer.id,
            original_filename=filename,
            file_size=save_result.file_size_bytes,
            s3_key=save_result.file_path,
            checksum=save_result.checksum,
            pdf_encrypted=was_encrypted,
            status="UPLOADED",
            banco_id=banco_id,
        )

    # ── Análisis ───────────────────────────────────────────────────────────

    def _build_raw_data(self, data: ManualProjectionInput) -> dict:
        """Traza de auditoría con los valores tal como los digitó el admin.

        También expone los campos que el resumen resuelve por sinónimos y que
        no tienen columna propia (p. ej. el número de cuota a cancelar).
        """
        return {
            "manual_entry": True,
            "created_by": "admin",
            "sistema_amortizacion": data.sistema_amortizacion,
            "plan_credito": data.plan_credito,
            "nro_cuota_a_cancelar": data.nro_cuota_a_cancelar,
            "cuotas_vencidas": data.cuotas_vencidas,
            "tiene_beneficio_frech": data.tiene_beneficio_frech,
            "totales_declarados": {
                "total_pagado_cliente": str(data.pagado_por_cliente),
                "total_frech_recibido": str(data.frech_acumulado),
                "total_abonado_credito": str(data.total_abonado_credito),
                "declarado_por_admin": data.declara_totales,
            },
        }

    def build_analysis_payload(
        self,
        data: ManualProjectionInput,
        *,
        documento_id,
        usuario_id,
    ) -> dict:
        pagado_cliente = data.pagado_por_cliente
        frech_acumulado = data.frech_acumulado

        return {
            "documento_id": documento_id,
            "usuario_id": usuario_id,
            # Datos del cliente
            "ingresos_mensuales": data.ingresos_mensuales,
            "capacidad_pago_max": data.capacidad_pago_max,
            "tipo_contrato_laboral": data.tipo_contrato_laboral,
            "opciones_abono_preferidas": [float(o) for o in data.opciones_abono_preferidas]
            if data.opciones_abono_preferidas
            else None,
            # Identificación del crédito
            "numero_credito": data.numero_credito,
            "banco_id": data.banco_id,
            "sistema_amortizacion": data.sistema_amortizacion,
            "plan_credito": data.plan_credito,
            "valor_prestado_inicial": data.valor_prestado_inicial,
            "fecha_desembolso": data.fecha_desembolso,
            "fecha_extracto": data.fecha_extracto,
            "plazo_total_meses": data.plazo_total_meses,
            # Cuotas
            "cuotas_pactadas": data.cuotas_pactadas,
            "cuotas_pagadas": data.cuotas_pagadas,
            "cuotas_pendientes": data.cuotas_pendientes,
            "cuotas_vencidas": data.cuotas_vencidas,
            # Tasas (ya normalizadas a fracción por el schema)
            "tasa_interes_pactada_ea": data.tasa_interes_pactada_ea,
            "tasa_interes_cobrada_ea": data.tasa_interes_cobrada_ea,
            "tasa_interes_subsidiada_ea": data.tasa_interes_subsidiada_ea,
            "tasa_mora_pactada_ea": data.tasa_mora_pactada_ea,
            # Montos mensuales
            "valor_cuota_sin_seguros": data.valor_cuota_sin_seguros,
            "valor_cuota_con_seguros": data.valor_cuota_con_seguros,
            "valor_cuota_con_subsidio": data.valor_cuota_con_subsidio,
            "beneficio_frech_mensual": data.beneficio_frech_mensual,
            "frech_fecha_inicio": data.frech_fecha_inicio,
            "frech_fecha_fin": data.frech_fecha_fin,
            "frech_vigencia_fuente": "manual" if data.frech_fecha_fin else None,
            "saldo_capital_pesos": data.saldo_capital_pesos,
            "total_por_pagar": data.total_por_pagar,
            # UVR
            "saldo_capital_uvr": data.saldo_capital_uvr,
            "valor_uvr_fecha_extracto": data.valor_uvr_fecha_extracto,
            "valor_cuota_uvr": data.valor_cuota_uvr,
            # Seguros
            "seguro_vida": data.seguro_vida,
            "seguro_incendio": data.seguro_incendio,
            "seguro_terremoto": data.seguro_terremoto,
            "seguros_total_mensual": data.seguros_total_mensual,
            # Componentes del período
            "capital_pagado_periodo": data.capital_pagado_periodo,
            "intereses_corrientes_periodo": data.intereses_corrientes_periodo,
            "intereses_mora": data.intereses_mora,
            "otros_cargos": data.otros_cargos,
            # Acumulados
            "total_pagado_fecha": pagado_cliente,
            "total_frech_recibido": frech_acumulado,
            "monto_real_pagado_banco": pagado_cliente + frech_acumulado,
            # Los totales digitados por el admin no son una estimación.
            "is_total_paid_estimated": not data.declara_totales,
            # Identidad y estado
            "nombre_titular_extracto": data.customer_full_name,
            "identificacion_extracto": data.customer_id_number,
            "nombre_coincide": True,
            "cedula_coincide": True,
            "es_extracto_hipotecario": True,
            "status": MANUAL_VALIDATION_STATUS,
            "projection_validation_status": "VALID",
            "campos_manuales": list(MANUAL_FIELDS),
            "campos_extraidos_ia": [],
            "datos_raw_gemini": None,
            "raw_data_json": self._build_raw_data(data),
        }

    def create(
        self,
        data: ManualProjectionInput,
        *,
        file_content: bytes,
        filename: str,
        pdf_password: str | None = None,
    ) -> ManualProjectionResult:
        banco = self.db.get(Banco, data.banco_id)
        if not banco or not banco.activo:
            raise ManualProjectionError("El banco seleccionado no es válido")

        customer, created_customer = self.resolve_customer(data)

        documento = self.store_statement_pdf(
            customer=customer,
            banco_id=data.banco_id,
            content=file_content,
            filename=filename,
            password=pdf_password,
        )

        analisis = self.analyses_repo.create(
            **self.build_analysis_payload(
                data, documento_id=documento.id, usuario_id=customer.id
            )
        )

        # Misma cadena de derivación que usa el flujo automático.
        self.analyses_repo.calculate_derived_fields(analisis)
        self.db.commit()
        self.db.refresh(analisis)

        logger.info(
            "Proyección manual creada: analisis=%s cliente=%s credito=%s",
            analisis.id,
            customer.id,
            data.numero_credito,
        )

        return ManualProjectionResult(
            analisis=analisis, customer=customer, created_customer=created_customer
        )


def get_manual_projection_service(db: Session) -> ManualProjectionService:
    return ManualProjectionService(db)
