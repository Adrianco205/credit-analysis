"""
Analysis Service - Orquestador del flujo de análisis de crédito.
=================================================================

Este servicio coordina todo el proceso:
1. Recibe documento + datos del usuario
2. Extrae datos con Gemini
3. Valida identidad (nombre PDF vs usuario)
4. Crea/actualiza el análisis
5. Genera propuestas de ahorro
"""
import logging
import uuid
import io
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.analisis import AnalisisHipotecario
from app.models.documento import DocumentoS3
from app.models.propuesta import PropuestaAhorro
from app.models.user import Usuario
from app.models.banco import Banco
from app.repositories.analyses_repo import AnalysesRepo
from app.repositories.propuestas_repo import PropuestasRepo
from app.repositories.documents_repo import DocumentsRepo
from app.services.gemini_service import (
    GeminiService, 
    ExtractionResult, 
    ExtractionStatus,
    get_gemini_service,
    map_extraction_to_analysis
)
from app.services.pdf_service import LocalStorageService, get_storage_service
from app.services.pdf_service import PdfService
from app.services.calc_service import (
    CalculadoraFinanciera, 
    crear_calculadora,
    DatosCredito,
    TiempoAhorro,
    FRECH_MAX_MESES_DEFAULT,
)
from app.services.uvr_projection_engine import (
    UvrProjectionInput,
    compare_uvr_scenarios,
    simulate_uvr_scenario,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES PARA RESULTADOS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AnalysisCreationResult:
    """Resultado de la creación de un análisis."""
    success: bool
    analisis: AnalisisHipotecario | None = None
    error_code: str | None = None
    error_message: str | None = None
    requires_manual_input: bool = False
    campos_faltantes: list[str] | None = None
    campos_extraidos: list[str] | None = None  # Campos que sí fueron extraídos (READONLY)
    name_mismatch: bool = False
    id_mismatch: bool = False  # Nueva: cédula no coincide
    invalid_document_type: bool = False  # Nueva: documento no es hipotecario
    tipo_documento_detectado: str | None = None  # Qué tipo de documento es si no es hipotecario


def _normalize_identity(value: str | None) -> str:
    if not value:
        return ""
    return (
        str(value)
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
        .strip()
    )


def _normalize_document_id_for_display(value: str | None) -> str:
    normalized = _normalize_identity(value)
    if not normalized:
        return "N/A"
    if len(normalized) < 6 or len(normalized) > 12:
        return "N/A"
    return normalized


def _normalize_name_tokens(value: str | None) -> set[str]:
    if not value:
        return set()

    normalized = unicodedata.normalize("NFD", str(value))
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^A-Za-z\s]", " ", normalized.upper())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return set()

    connectors = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}
    return {
        token
        for token in normalized.split(" ")
        if token and token not in connectors and len(token) > 1
    }


def _names_look_equivalent(pdf_name: str | None, user_name: str | None) -> bool:
    pdf_tokens = _normalize_name_tokens(pdf_name)
    user_tokens = _normalize_name_tokens(user_name)

    if not pdf_tokens or not user_tokens:
        return False

    common = pdf_tokens & user_tokens
    if not common:
        return False

    shorter_size = min(len(pdf_tokens), len(user_tokens))
    if shorter_size == 0:
        return False

    overlap_ratio = len(common) / shorter_size
    if overlap_ratio >= 0.75 and len(common) >= 2:
        return True

    if pdf_tokens.issubset(user_tokens) or user_tokens.issubset(pdf_tokens):
        return len(common) >= 2

    return False


@dataclass
class ProjectionGenerationResult:
    """Resultado de la generación de proyecciones."""
    success: bool
    propuestas: list[PropuestaAhorro] | None = None
    error_message: str | None = None


@dataclass
class DatosUsuarioInput:
    """Datos que proporciona el usuario al crear análisis."""
    ingresos_mensuales: Decimal
    capacidad_pago_max: Decimal | None = None
    tipo_contrato_laboral: str | None = None
    # Preferencias de abono extra del usuario (se capturan antes de las proyecciones)
    opciones_abono_preferidas: list[Decimal] | None = None  # Ej: [200000, 300000, 400000]


@dataclass
class OpcionAbonoInput:
    """Una opción de abono para generar proyección."""
    numero_opcion: int
    abono_adicional_mensual: Decimal
    nombre_opcion: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICIO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class AnalysisService:
    """
    Servicio orquestador para el flujo completo de análisis de crédito.
    """
    
    def __init__(
        self,
        db: Session,
        gemini_service: GeminiService | None = None,
        storage_service: LocalStorageService | None = None,
        calculadora: CalculadoraFinanciera | None = None
    ):
        self.db = db
        self.analyses_repo = AnalysesRepo(db)
        self.propuestas_repo = PropuestasRepo(db)
        self.documents_repo = DocumentsRepo(db)
        self.gemini = gemini_service or get_gemini_service()
        self.storage = storage_service or get_storage_service()
        self.calc = calculadora or crear_calculadora()
        self.uvr_engine_v2_enabled = bool(getattr(settings, "UVR_ENGINE_V2_ENABLED", False))
        self.uvr_inflacion_anual_default = Decimal(str(getattr(settings, "UVR_INFLACION_ANUAL_ESTIMADA_DEFAULT", 0.022)))
    
    def _serialize_for_json(self, data: dict) -> dict:
        """
        Convierte tipos no serializables a JSON (date, Decimal) a tipos compatibles.
        """
        from datetime import date as date_type
        from decimal import Decimal as DecimalType
        
        result = {}
        for key, value in data.items():
            if isinstance(value, date_type):
                result[key] = value.isoformat()
            elif isinstance(value, DecimalType):
                result[key] = float(value)
            elif isinstance(value, dict):
                result[key] = self._serialize_for_json(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_for_json(item) if isinstance(item, dict) 
                    else (item.isoformat() if isinstance(item, date_type) 
                          else (float(item) if isinstance(item, DecimalType) else item))
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _cleanup_document_on_identity_failure(self, documento: DocumentoS3) -> None:
        """Elimina archivo físico y registro de documento cuando falla validación de identidad."""
        try:
            if documento.s3_key:
                self.storage.delete_pdf(documento.s3_key)
        except Exception as error:
            logger.warning(f"No se pudo eliminar archivo del documento {documento.id}: {error}")

        try:
            self.documents_repo.delete(documento.id)
        except Exception as error:
            logger.warning(f"No se pudo eliminar registro de documento {documento.id}: {error}")

    def _aplicar_guardia_tasa_extraida(self, extraction_result: ExtractionResult) -> None:
        """Corrige tasas sospechosamente bajas interpretadas como E.A. cuando parecen mensuales."""
        tasa_extraida = extraction_result.data.get("tasa_interes_cobrada_ea")
        if tasa_extraida is None:
            return

        try:
            tasa_decimal = Decimal(str(tasa_extraida))
        except Exception:
            return

        # Si la tasa viene en porcentaje (ej: 7.47), la normalización posterior la convertirá.
        # Este guard solo aplica cuando ya parece decimal y cae por debajo del rango típico de E.A.
        if Decimal("0") < tasa_decimal < Decimal("0.04"):
            calc_engine = getattr(self, "calc", None) or crear_calculadora()
            tasa_ea_equivalente = calc_engine.tasa_mensual_a_ea(tasa_decimal)
            extraction_result.data["tasa_interes_cobrada_ea"] = tasa_ea_equivalente
            logger.info(
                "Guardia de tasa aplicada: tasa_interes_cobrada_ea %s interpretada como mensual; convertida a E.A. %s",
                tasa_decimal,
                tasa_ea_equivalente,
            )

    def _resolve_ipc_anual_proyectado(self, ipc_proyectado: Decimal | float | None) -> Decimal:
        """Convierte IPC comercial (% o decimal) a tasa anual decimal para el motor."""
        default_ipc = Decimal("0.022")
        if ipc_proyectado is None:
            return default_ipc

        try:
            ipc_normalizado = Decimal(str(ipc_proyectado))
        except Exception:
            return default_ipc

        if ipc_normalizado <= 0:
            return default_ipc

        if ipc_normalizado > 1:
            ipc_normalizado = ipc_normalizado / Decimal("100")

        return ipc_normalizado.quantize(Decimal("0.000001"))

    def _extract_identity_from_pdf_text(self, pdf_content: bytes) -> tuple[str | None, str | None]:
        """Extrae nombre y CC con heurísticas desde texto plano del PDF."""
        try:
            raw_text = PdfService.extract_text_basic(io.BytesIO(pdf_content))
        except Exception:
            return None, None

        if not raw_text:
            return None, None

        text = raw_text.replace("\r", "\n")
        compact_text = re.sub(r"\s+", " ", text)

        identity_keywords = [
            "CC",
            "C.C",
            "CEDULA",
            "CÉDULA",
            "IDENTIFICACION",
            "IDENTIFICACIÓN",
            "NIT",
        ]
        credit_keywords = ["CREDITO", "CRÉDITO", "NUMERO DE CREDITO", "NÚMERO DE CRÉDITO"]

        detected_id = None
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue

            line_upper = line.upper()
            if any(keyword in line_upper for keyword in credit_keywords):
                continue

            if not any(keyword in line_upper for keyword in identity_keywords):
                continue

            matches = re.findall(r"([0-9][0-9\.\-\s]{5,})", line)
            for match in matches:
                candidate = _normalize_identity(match)
                if 6 <= len(candidate) <= 12:
                    detected_id = candidate
                    break

            if detected_id:
                break

        name_patterns = [
            r"(?:NOMBRE(?:\s+DEL\s+(?:CLIENTE|TITULAR))?|TITULAR|DEUDOR)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,})",
            r"(?:SEÑOR(?:A)?|SR\.?|SRA\.?)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,})",
        ]

        detected_name = None
        for pattern in name_patterns:
            match = re.search(pattern, compact_text.upper(), re.IGNORECASE)
            if not match:
                continue
            candidate = re.sub(r"\s+", " ", match.group(1)).strip(" -:;")
            words = [w for w in candidate.split(" ") if len(w) > 1]
            if len(words) >= 2:
                detected_name = " ".join(words)
                break

        return detected_name, detected_id

    def _enrich_identity_from_fallback(self, pdf_content: bytes, extraction_result: ExtractionResult) -> None:
        """Completa nombre/CC faltantes con heurísticas locales de OCR/texto."""
        current_name = str(extraction_result.data.get("nombre_titular") or "").strip()
        current_id = str(extraction_result.data.get("identificacion_titular") or "").strip()

        if current_name and current_id:
            return

        fallback_name, fallback_id = self._extract_identity_from_pdf_text(pdf_content)

        if not current_name and fallback_name:
            extraction_result.data["nombre_titular"] = fallback_name
            if "nombre_titular" not in extraction_result.campos_encontrados:
                extraction_result.campos_encontrados.append("nombre_titular")

        if not current_id and fallback_id:
            extraction_result.data["identificacion_titular"] = fallback_id
            if "identificacion_titular" not in extraction_result.campos_encontrados:
                extraction_result.campos_encontrados.append("identificacion_titular")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FLUJO PRINCIPAL: CREAR ANÁLISIS DESDE DOCUMENTO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def create_analysis_from_document(
        self,
        documento_id: uuid.UUID,
        usuario: Usuario,
        datos_usuario: DatosUsuarioInput,
        skip_name_validation: bool = False,
        skip_id_validation: bool = False,
        allow_non_credit_document: bool = False,
        banco_id: int | None = None  # ID del banco seleccionado por el usuario
    ) -> AnalysisCreationResult:
        """
        Crea un análisis completo a partir de un documento PDF.
        
        Flujo:
        1. Verificar que el documento existe y pertenece al usuario
        2. Obtener el PDF del storage
        3. Extraer datos con Gemini
        4. Validar nombre del titular vs usuario
        5. Crear registro de análisis
        6. Calcular campos derivados
        
        Args:
            documento_id: ID del documento PDF
            usuario: Usuario autenticado
            datos_usuario: Datos socioeconómicos del usuario
            skip_name_validation: Omitir validación de nombre (para testing)
            skip_id_validation: Omitir validación de cédula/identificación
            allow_non_credit_document: Permitir documentos no hipotecarios y continuar en estado manual
            banco_id: ID del banco seleccionado por el usuario (prioridad sobre detección automática)
            
        Returns:
            AnalysisCreationResult con el análisis creado o error
        """
        try:
            # 1. Verificar documento
            documento = self.documents_repo.get_by_id_and_user(
                documento_id, 
                usuario.id
            )
            if not documento:
                return AnalysisCreationResult(
                    success=False,
                    error_code="DOCUMENT_NOT_FOUND",
                    error_message="Documento no encontrado o no pertenece al usuario"
                )
            
            # Verificar que no exista ya un análisis para este documento
            existing = self.analyses_repo.get_by_documento(documento_id)
            if existing:
                return AnalysisCreationResult(
                    success=False,
                    error_code="ANALYSIS_EXISTS",
                    error_message="Ya existe un análisis para este documento",
                    analisis=existing
                )
            
            # 2. Obtener PDF del storage
            # El s3_key ya contiene la ruta relativa completa: pdfs/{user_id}/{filename}
            pdf_content = self.storage.get_pdf(documento.s3_key)
            if not pdf_content:
                return AnalysisCreationResult(
                    success=False,
                    error_code="PDF_NOT_FOUND",
                    error_message="No se pudo obtener el archivo PDF"
                )
            
            # 3. Extraer datos con Gemini
            extraction_result = await self.gemini.extract_credit_data(pdf_content)
            self._enrich_identity_from_fallback(pdf_content, extraction_result)
            
            # ════════════════════════════════════════════════════════════════
            # MEJORA 1: VALIDACIÓN DE TIPO DE DOCUMENTO
            # ════════════════════════════════════════════════════════════════
            if extraction_result.status == ExtractionStatus.NOT_CREDIT_DOCUMENT:
                if allow_non_credit_document:
                    logger.warning(
                        "Documento no hipotecario permitido por configuración. "
                        f"Documento={documento_id} Usuario={usuario.id}"
                    )
                else:
                    # Extraer el tipo de documento detectado del raw response
                    tipo_detectado = extraction_result.data.get("tipo_documento_detectado", "Documento no reconocido")
                    return AnalysisCreationResult(
                        success=False,
                        error_code="INVALID_DOCUMENT_TYPE",
                        error_message=f"El documento subido no es un extracto de crédito hipotecario. Se detectó: {tipo_detectado}",
                        invalid_document_type=True,
                        tipo_documento_detectado=tipo_detectado
                    )

            tipo_detectado = extraction_result.data.get("tipo_documento_detectado")

            if extraction_result.status == ExtractionStatus.NOT_CREDIT_DOCUMENT and allow_non_credit_document:
                # Extraer el tipo de documento detectado del raw response
                extraction_result.campos_faltantes = extraction_result.campos_faltantes or [
                    "saldo_capital_pesos",
                    "valor_cuota_con_seguros",
                    "cuotas_pendientes",
                    "tasa_interes_cobrada_ea",
                ]
            
            if extraction_result.status == ExtractionStatus.API_ERROR:
                return AnalysisCreationResult(
                    success=False,
                    error_code="EXTRACTION_ERROR",
                    error_message=f"Error en extracción: {extraction_result.message}"
                )

            self._aplicar_guardia_tasa_extraida(extraction_result)

            nombre_pdf_detectado = str(extraction_result.data.get("nombre_titular") or "").strip()
            identificacion_pdf = extraction_result.data.get("identificacion_titular")
            identificacion_pdf_detectada = str(identificacion_pdf or "").strip()
            tipo_identificacion_pdf = str(extraction_result.data.get("tipo_identificacion_titular") or "").upper().strip()
            numero_credito_detectado = _normalize_identity(str(extraction_result.data.get("numero_credito") or ""))

            if not skip_name_validation and not nombre_pdf_detectado:
                self._cleanup_document_on_identity_failure(documento)
                return AnalysisCreationResult(
                    success=False,
                    error_code="OCR_IDENTITY_NOT_READABLE",
                    error_message=(
                        "No fue posible leer claramente el nombre en el documento. "
                        "Por favor carga un archivo de mejor calidad para continuar."
                    ),
                )
            
            # 4. Validar nombre (si no se omite)
            name_match = True
            if not skip_name_validation and nombre_pdf_detectado:
                nombre_usuario = self._build_user_full_name(usuario)
                nombre_pdf = nombre_pdf_detectado
                
                comparison = await self.gemini.compare_names(nombre_pdf, nombre_usuario)
                name_match = comparison.match

                if not name_match and _names_look_equivalent(nombre_pdf, nombre_usuario):
                    logger.info(
                        "Nombre validado por fallback local tras falso negativo de comparación IA. "
                        f"PDF='{nombre_pdf}' Usuario='{nombre_usuario}'"
                    )
                    name_match = True
                
                if not name_match:
                    logger.warning(
                        f"Nombre no coincide. PDF: {nombre_pdf}, Usuario: {nombre_usuario}"
                    )
            
            # ════════════════════════════════════════════════════════════════
            # MEJORA 4: VALIDACIÓN DE CÉDULA/IDENTIFICACIÓN
            # ════════════════════════════════════════════════════════════════
            id_match = True
            detected_id_normalized = _normalize_identity(identificacion_pdf_detectada)
            id_is_explicit = bool(tipo_identificacion_pdf in {"CC", "CE", "NIT", "TI", "PAS", "PA"})
            if detected_id_normalized and numero_credito_detectado and detected_id_normalized == numero_credito_detectado:
                id_is_explicit = False

            if not skip_id_validation and identificacion_pdf and usuario.identificacion:
                # Normalizar: quitar espacios, puntos, guiones
                id_pdf_normalized = detected_id_normalized
                id_user_normalized = _normalize_identity(str(usuario.identificacion))
                
                id_match = id_pdf_normalized == id_user_normalized
                
                if not id_match:
                    logger.warning(
                        f"Cédula no coincide. PDF: {identificacion_pdf} ({id_pdf_normalized}), "
                        f"Usuario: {usuario.identificacion} ({id_user_normalized})"
                    )

            if not skip_name_validation and not name_match:
                self._cleanup_document_on_identity_failure(documento)
                suggestion = ""
                if id_is_explicit and detected_id_normalized:
                    usuario_por_cc = self.db.execute(
                        select(Usuario).where(
                            func.replace(
                                func.replace(
                                    func.replace(func.coalesce(Usuario.identificacion, ""), ".", ""),
                                    "-",
                                    "",
                                ),
                                " ",
                                "",
                            )
                            == detected_id_normalized
                        )
                    ).scalar_one_or_none()
                    if usuario_por_cc and usuario_por_cc.id != usuario.id:
                        suggestion = " Inicia sesión con la cuenta asociada a este titular."

                return AnalysisCreationResult(
                    success=False,
                    error_code="IDENTITY_MISMATCH",
                    error_message=(
                        f"Los datos del documento (Nombre: {nombre_pdf_detectado or 'No detectado'}) no coinciden con tu cuenta. "
                        "Para procesar este análisis, por favor inicia sesión con la cuenta correspondiente "
                        "o crea una nueva cuenta para este titular."
                        f"{suggestion}"
                    ),
                    name_mismatch=not name_match,
                    id_mismatch=not id_match,
                )
            
            # 5. Crear análisis
            # Serializar datos para JSONB (convertir date y Decimal a tipos serializables)
            datos_raw_serializables = self._serialize_for_json(extraction_result.data)
            
            # ════════════════════════════════════════════════════════════════
            # MEJORA 2: CAPTURAR PREFERENCIAS DE ABONO DEL USUARIO
            # ════════════════════════════════════════════════════════════════
            opciones_abono = None
            if datos_usuario.opciones_abono_preferidas:
                opciones_abono = [float(o) for o in datos_usuario.opciones_abono_preferidas]
            
            analisis_data = {
                "documento_id": documento_id,
                "usuario_id": usuario.id,
                "ingresos_mensuales": datos_usuario.ingresos_mensuales,
                "capacidad_pago_max": datos_usuario.capacidad_pago_max,
                "tipo_contrato_laboral": datos_usuario.tipo_contrato_laboral,
                "nombre_coincide": name_match,
                "cedula_coincide": id_match,  # NUEVO
                "identificacion_extracto": str(identificacion_pdf) if identificacion_pdf else None,  # NUEVO
                "es_extracto_hipotecario": extraction_result.es_extracto_hipotecario,
                "tipo_documento_detectado": tipo_detectado,
                "datos_raw_gemini": datos_raw_serializables,
                "campos_extraidos_ia": extraction_result.campos_encontrados,  # NUEVO: para readonly
                "opciones_abono_preferidas": opciones_abono,  # NUEVO
                "abono_adicional_actual": None,  # MEJORA 3: siempre NULL en diagnóstico inicial
            }
            
            # Mapear datos extraídos
            extraction_mapping = map_extraction_to_analysis(
                extraction_result,
                str(documento_id),
                str(usuario.id)
            )
            
            # Combinar datos
            for key, value in extraction_mapping.items():
                if key not in ["documento_id", "usuario_id"] and value is not None:
                    analisis_data[key] = value
            
            # Resolver banco_id: prioridad al ID proporcionado por el usuario
            if banco_id:
                # El usuario seleccionó un banco explícitamente
                analisis_data["banco_id"] = banco_id
                logger.info(f"Banco asignado por usuario: ID {banco_id}")
            else:
                # Fallback: intentar detectar desde el nombre extraído del PDF
                banco_detectado = extraction_result.data.get("banco")
                if banco_detectado:
                    # Buscar banco por nombre (case-insensitive, partial match)
                    stmt = select(Banco).where(
                        func.lower(Banco.nombre).contains(func.lower(banco_detectado))
                    )
                    banco = self.db.execute(stmt).scalar_one_or_none()
                    if banco:
                        analisis_data["banco_id"] = banco.id
                        logger.info(f"Banco detectado automáticamente: {banco_detectado} -> ID {banco.id}")
                    else:
                        logger.warning(f"Banco detectado pero no encontrado en BD: {banco_detectado}")
            
            # Determinar estado inicial
            campos_faltantes = extraction_result.campos_faltantes or []
            requires_manual = self._check_requires_manual_input(
                extraction_result.data, 
                campos_faltantes
            )
            
            # ════════════════════════════════════════════════════════════════
            # DETERMINAR ESTADO CON NUEVA LÓGICA DE VALIDACIÓN
            # ════════════════════════════════════════════════════════════════
            if not name_match:
                # Solo nombre no coincide (cédula sí): podría ser formato de nombre diferente
                analisis_data["status"] = "NAME_MISMATCH"
            elif requires_manual:
                analisis_data["status"] = "PENDING_MANUAL"
            else:
                analisis_data["status"] = "EXTRACTED"
            
            analisis = self.analyses_repo.create(**analisis_data)
            
            # 6. Calcular campos derivados (si tenemos datos suficientes)
            if not requires_manual:
                self.analyses_repo.calculate_derived_fields(analisis)
            
            self.db.commit()
            
            campos_faltantes_actuales = self._get_remaining_required_fields(analisis) if requires_manual else None

            return AnalysisCreationResult(
                success=True,
                analisis=analisis,
                requires_manual_input=requires_manual,
                campos_faltantes=campos_faltantes_actuales,
                campos_extraidos=extraction_result.campos_encontrados,  # NUEVO
                name_mismatch=not name_match,
                id_mismatch=not id_match  # NUEVO
            )
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error creando análisis:\n{error_trace}")
            self.db.rollback()
            # Devolver información del error más detallada para debugging
            error_msg = f"{type(e).__name__}: {str(e)}"
            return AnalysisCreationResult(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=error_msg
            )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ACTUALIZACIÓN CON DATOS MANUALES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def update_manual_fields(
        self,
        analisis_id: uuid.UUID,
        usuario_id: uuid.UUID,
        manual_data: dict
    ) -> AnalysisCreationResult:
        """
        Actualiza un análisis con campos proporcionados manualmente.
        
        MEJORA 5: Solo permite actualizar campos que NO fueron extraídos por Gemini.
        Los campos en `campos_extraidos_ia` son de solo lectura (readonly).
        """
        try:
            analisis = self.analyses_repo.get_by_id_and_user(analisis_id, usuario_id)
            if not analisis:
                return AnalysisCreationResult(
                    success=False,
                    error_code="ANALYSIS_NOT_FOUND",
                    error_message="Análisis no encontrado"
                )
            
            # Permitir actualización en más estados para flexibilidad
            estados_permitidos = ["PENDING_MANUAL", "EXTRACTED", "NAME_MISMATCH", "ID_MISMATCH"]
            if analisis.status not in estados_permitidos:
                return AnalysisCreationResult(
                    success=False,
                    error_code="INVALID_STATUS",
                    error_message=f"No se puede actualizar análisis en estado {analisis.status}"
                )
            
            # ════════════════════════════════════════════════════════════════
            # MEJORA 5: CAMPOS READONLY - No permitir editar campos extraídos por IA
            # ════════════════════════════════════════════════════════════════
            campos_readonly = analisis.campos_extraidos_ia or []
            raw_data = analisis.datos_raw_gemini or {}
            
            campos_permitidos = {}
            campos_rechazados = []
            
            for field, value in manual_data.items():
                if value is not None:
                    # REGLA: Si el campo fue extraído exitosamente por IA, NO se puede editar
                    if field in campos_readonly:
                        campos_rechazados.append(field)
                        logger.warning(f"Intento de editar campo readonly: {field}")
                        continue
                    
                    # Doble verificación: también revisar si hay valor en raw_data
                    gemini_value = raw_data.get(field)
                    current_value = getattr(analisis, field, None)
                    
                    # Solo permitir si:
                    # 1. El campo NO está en la lista de extraídos
                    # 2. Y (el valor actual es None O el valor de Gemini es None)
                    if current_value is None or gemini_value is None:
                        campos_permitidos[field] = value
                    else:
                        campos_rechazados.append(field)
            
            # Informar sobre campos rechazados
            if campos_rechazados:
                logger.info(
                    f"Campos rechazados por ser readonly (extraídos por IA): {campos_rechazados}"
                )
            
            if campos_permitidos:
                # Registrar qué campos se llenaron manualmente
                campos_manuales_actuales = analisis.campos_manuales or []
                nuevos_campos_manuales = list(set(campos_manuales_actuales + list(campos_permitidos.keys())))
                campos_permitidos["campos_manuales"] = nuevos_campos_manuales
                
                analisis = self.analyses_repo.update_manual_fields(
                    analisis, 
                    campos_permitidos
                )
                self.analyses_repo.calculate_derived_fields(analisis)
            
            self.db.commit()
            
            # Calcular campos que aún faltan
            campos_faltantes_actuales = self._get_remaining_required_fields(analisis)
            
            return AnalysisCreationResult(
                success=True,
                analisis=analisis,
                requires_manual_input=(analisis.status == "PENDING_MANUAL"),
                campos_faltantes=campos_faltantes_actuales if campos_faltantes_actuales else None,
                campos_extraidos=campos_readonly  # Devolver lista de campos readonly
            )
            
        except Exception as e:
            logger.exception(f"Error actualizando campos manuales: {e}")
            self.db.rollback()
            return AnalysisCreationResult(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=str(e)
            )
    
    def _get_remaining_required_fields(self, analisis: AnalisisHipotecario) -> list[str]:
        """Obtiene los campos requeridos que aún faltan por llenar."""
        campos_faltantes: list[str] = []

        if analisis.saldo_capital_pesos is None:
            campos_faltantes.append("saldo_capital_pesos")

        cuota_disponible = (
            analisis.valor_cuota_con_subsidio
            or analisis.valor_cuota_con_seguros
            or analisis.valor_cuota_sin_seguros
        )
        if cuota_disponible is None:
            campos_faltantes.append("valor_cuota_con_seguros")

        if analisis.cuotas_pendientes is None:
            campos_faltantes.append("cuotas_pendientes")

        if analisis.tasa_interes_cobrada_ea is None:
            campos_faltantes.append("tasa_interes_cobrada_ea")

        if analisis.valor_prestado_inicial is None:
            campos_faltantes.append("valor_prestado_inicial")

        return campos_faltantes
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # GENERACIÓN DE PROYECCIONES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def generate_projections(
        self,
        analisis_id: uuid.UUID,
        opciones: list[OpcionAbonoInput],
        usuario_id: uuid.UUID | None = None,
        valor_uvr_para_calculo: Decimal | None = None,
        ipc_proyectado: Decimal | float | None = None,
    ) -> ProjectionGenerationResult:
        """
        Genera proyecciones de ahorro para un análisis.
        
        Args:
            analisis_id: ID del análisis
            opciones: Lista de opciones de abono adicional
            usuario_id: ID del usuario (para validación de permisos)
            
        Returns:
            ProjectionGenerationResult con las propuestas generadas
        """
        try:
            # Obtener análisis
            if usuario_id:
                analisis = self.analyses_repo.get_by_id_and_user(analisis_id, usuario_id)
            else:
                analisis = self.analyses_repo.get_by_id(analisis_id)
            
            if not analisis:
                return ProjectionGenerationResult(
                    success=False,
                    error_message="Análisis no encontrado"
                )
            
            # Validar estado
            if analisis.status not in ["EXTRACTED", "VALIDATED", "NAME_MISMATCH"]:
                return ProjectionGenerationResult(
                    success=False,
                    error_message=f"El análisis debe estar validado. Estado actual: {analisis.status}"
                )
            
            # Validar datos mínimos para cálculo
            if not self._validate_analysis_for_projection(analisis):
                return ProjectionGenerationResult(
                    success=False,
                    error_message="El análisis no tiene los datos mínimos requeridos para generar proyecciones"
                )
            
            # Eliminar propuestas anteriores
            self.propuestas_repo.delete_by_analisis(analisis_id)

            ipc_anual_proyectado = self._resolve_ipc_anual_proyectado(ipc_proyectado)
            
            # Calcular estado actual (baseline)
            baseline = self._calculate_baseline(
                analisis,
                valor_uvr_para_calculo=valor_uvr_para_calculo,
                ipc_anual_proyectado=ipc_anual_proyectado,
            )
            
            # Generar cada opción
            propuestas_creadas = []
            
            for opcion in opciones:
                resultado = self._calculate_projection_for_option(
                    analisis,
                    opcion,
                    baseline
                )
                
                propuesta_data = {
                    "analisis_id": analisis_id,
                    "numero_opcion": opcion.numero_opcion,
                    "nombre_opcion": opcion.nombre_opcion or f"Opción {opcion.numero_opcion}",
                    "abono_adicional_mensual": opcion.abono_adicional_mensual,
                    "origen": "USER",
                    **resultado
                }
                
                propuesta = self.propuestas_repo.create(**propuesta_data)
                propuestas_creadas.append(propuesta)
            
            # Actualizar estado del análisis si es necesario
            if analisis.status == "EXTRACTED":
                analisis.status = "VALIDATED"
                self.analyses_repo.save(analisis)
            
            self.db.commit()
            
            return ProjectionGenerationResult(
                success=True,
                propuestas=propuestas_creadas
            )
            
        except Exception as e:
            logger.exception(f"Error generando proyecciones: {e}")
            self.db.rollback()
            return ProjectionGenerationResult(
                success=False,
                error_message=str(e)
            )
    
    def recalculate_projection(
        self,
        propuesta_id: uuid.UUID,
        nuevo_abono: Decimal,
        origen: str = "ADMIN"
    ) -> PropuestaAhorro | None:
        """
        Recalcula una propuesta individual con nuevo abono.
        Usado por el admin para ajustes.
        """
        try:
            propuesta = self.propuestas_repo.get_by_id(propuesta_id)
            if not propuesta:
                return None
            
            analisis = self.analyses_repo.get_by_id(propuesta.analisis_id)
            if not analisis:
                return None
            
            baseline = self._calculate_baseline(analisis)
            
            opcion = OpcionAbonoInput(
                numero_opcion=propuesta.numero_opcion,
                abono_adicional_mensual=nuevo_abono,
                nombre_opcion=propuesta.nombre_opcion
            )
            
            resultado = self._calculate_projection_for_option(
                analisis,
                opcion,
                baseline
            )
            
            # Actualizar propuesta
            propuesta.abono_adicional_mensual = nuevo_abono
            propuesta.origen = origen
            self.propuestas_repo.update_calculo(propuesta, resultado)
            
            self.db.commit()
            return propuesta
            
        except Exception as e:
            logger.exception(f"Error recalculando propuesta: {e}")
            self.db.rollback()
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _build_user_full_name(self, usuario: Usuario) -> str:
        """Construye el nombre completo del usuario."""
        parts = [
            usuario.nombres or "",
            usuario.primer_apellido or "",
            usuario.segundo_apellido or ""
        ]
        return " ".join(p for p in parts if p).strip()
    
    def _check_requires_manual_input(
        self,
        extracted_data: dict,
        campos_faltantes: list[str]
    ) -> bool:
        """Verifica si se requiere input manual del usuario."""
        # Campos críticos que DEBEN estar para poder calcular
        campos_criticos = {
            "saldo_capital_pesos",
            "cuotas_pendientes",
            "tasa_interes_cobrada_ea",
            "valor_prestado_inicial",
        }

        cuota_disponible = (
            extracted_data.get("valor_cuota_con_subsidio")
            or extracted_data.get("valor_cuota_con_seguros")
            or extracted_data.get("valor_cuota_sin_seguros")
        )
        
        # Verificar si algún campo crítico falta
        for campo in campos_criticos:
            if campo in campos_faltantes:
                return True
            if extracted_data.get(campo) is None:
                return True

        if cuota_disponible is None:
            return True
        
        return False
    
    def _validate_analysis_for_projection(self, analisis: AnalisisHipotecario) -> bool:
        """Valida que el análisis tenga los datos mínimos para generar proyecciones."""
        cuota_disponible = (
            analisis.valor_cuota_con_subsidio
            or analisis.valor_cuota_con_seguros
            or analisis.valor_cuota_sin_seguros
        )
        required_fields = [
            analisis.saldo_capital_pesos,
            cuota_disponible,
            analisis.cuotas_pendientes,
            analisis.tasa_interes_cobrada_ea,
            analisis.valor_prestado_inicial
        ]
        return all(f is not None for f in required_fields)
    
    def _calculate_baseline(
        self,
        analisis: AnalisisHipotecario,
        valor_uvr_para_calculo: Decimal | None = None,
        ipc_anual_proyectado: Decimal | None = None,
    ) -> dict:
        """Calcula el estado actual del credito (sin abono extra).

        Mantiene una separacion explicita:
        - datos_visible: cuota del extracto para UI y opciones visibles
        - datos_proyeccion: copia calibrable para cerrar amortizacion del baseline
        """
        frech = analisis.beneficio_frech_mensual or Decimal("0")
        ipc_anual_proyectado_resuelto = self._resolve_ipc_anual_proyectado(ipc_anual_proyectado)

        cuota_cliente = (
            analisis.valor_cuota_con_subsidio
            or analisis.valor_cuota_con_seguros
            or analisis.valor_cuota_sin_seguros
        )
        cuota_base_source = "valor_cuota_con_subsidio"

        if analisis.valor_cuota_con_subsidio is None:
            if analisis.valor_cuota_con_seguros is not None:
                cuota_base_source = "valor_cuota_con_seguros"
            elif analisis.valor_cuota_sin_seguros is not None:
                cuota_base_source = "valor_cuota_sin_seguros"

        if (
            analisis.valor_cuota_con_subsidio is None
            and frech > 0
            and analisis.valor_cuota_con_seguros
        ):
            posible_cliente = analisis.valor_cuota_con_seguros - frech
            if Decimal("0") < posible_cliente < analisis.valor_cuota_con_seguros:
                total_por_pagar = analisis.total_por_pagar
                if total_por_pagar is None:
                    cuota_cliente = posible_cliente
                    cuota_base_source = "valor_cuota_con_seguros_menos_frech"
                else:
                    delta_actual = abs(total_por_pagar - analisis.valor_cuota_con_seguros)
                    delta_posible = abs(total_por_pagar - posible_cliente)
                    if delta_posible <= delta_actual:
                        cuota_cliente = posible_cliente
                        cuota_base_source = "valor_cuota_con_seguros_menos_frech"

        if cuota_cliente is None:
            raise ValueError("No hay cuota base disponible para generar proyecciones")

        sistema_amortizacion = (analisis.sistema_amortizacion or "PESOS").upper().strip()
        valor_uvr_actual = None
        if sistema_amortizacion == "UVR":
            if valor_uvr_para_calculo is not None and valor_uvr_para_calculo > 0:
                valor_uvr_actual = valor_uvr_para_calculo
            elif analisis.valor_uvr_fecha_extracto is not None and analisis.valor_uvr_fecha_extracto > 0:
                valor_uvr_actual = analisis.valor_uvr_fecha_extracto

        # Crear objeto DatosCredito
        cargos_no_amortizables = self._estimar_cargos_no_amortizables_mensuales(
            analisis=analisis,
            cuota_cliente=cuota_cliente,
            frech=frech,
        )

        frech_meses_restantes = self._resolve_frech_meses_restantes(analisis)

        datos_visible = DatosCredito(
            saldo_capital=analisis.saldo_capital_pesos,
            valor_cuota_actual=cuota_cliente,
            cuotas_pendientes=analisis.cuotas_pendientes,
            tasa_interes_ea=analisis.tasa_interes_cobrada_ea,
            valor_prestado_inicial=analisis.valor_prestado_inicial,
            beneficio_frech=frech,
            tasa_seguro_vida=Decimal("0"),
            valor_seguro_incendio_fijo=analisis.seguros_total_mensual or Decimal("0"),
            tasa_cobertura_frech=getattr(analisis, "tasa_cobertura_frech", Decimal("0")) or Decimal("0"),
            cargos_no_amortizables_mensuales=cargos_no_amortizables,
            sistema_amortizacion=sistema_amortizacion,
            valor_uvr_actual=valor_uvr_actual,
            frech_meses_restantes=frech_meses_restantes,
            ipc_anual_proyectado=ipc_anual_proyectado_resuelto,
        )

        # Datos usados para amortizacion del baseline (pueden calibrarse).
        # Nunca deben reemplazar la cuota visible mostrada en UI.
        # Se clona explicitamente para evitar alias accidental entre visible/proyeccion.
        datos_proyeccion = replace(datos_visible)
        
        # Calcular proyección actual (sin abono extra)
        proyeccion_actual = self.calc.calcular_proyeccion(
            datos=datos_proyeccion,
            abono_extra=Decimal("0"),
            numero_opcion=0,
            nombre_opcion="Actual"
        )

        # Consistencia UVR: baseline con el mismo enfoque del engine V2 para
        # evitar que baseline y opciones provengan de motores distintos.
        if sistema_amortizacion == "UVR" and bool(getattr(self, "uvr_engine_v2_enabled", False)) and valor_uvr_actual and valor_uvr_actual > 0:
            try:
                payload_baseline = UvrProjectionInput(
                    saldo_inicial=datos_visible.saldo_capital,
                    tasa_efectiva_anual=datos_visible.tasa_interes_ea,
                    tasa_efectiva_anual_subsidiada=getattr(analisis, "tasa_interes_subsidiada_ea", None),
                    plazo_meses=datos_visible.cuotas_pendientes,
                    cuota_actual=datos_visible.valor_cuota_actual,
                    abono_adicional=Decimal("0"),
                    uvr_actual=valor_uvr_actual,
                    inflacion_anual_estimada=ipc_anual_proyectado_resuelto,
                    subsidio_frech=datos_visible.beneficio_frech,
                    seguro_mensual=(
                        datos_visible.valor_seguro_incendio_fijo
                        + (datos_visible.saldo_capital * datos_visible.tasa_seguro_vida)
                    ).quantize(Decimal("0.01")),
                    cuota_uvr_actual=getattr(analisis, "valor_cuota_uvr", None),
                    frech_meses_restantes=datos_visible.frech_meses_restantes,
                )

                baseline_uvr = simulate_uvr_scenario(payload_baseline, abono_adicional_override=Decimal("0"))
                costo_total_proyectado = baseline_uvr.total_pagado_cliente
                total_subsidio_frech_proyectado = self.calc.calcular_flujo_frech(
                    beneficio_frech_mensual=datos_visible.beneficio_frech,
                    cuotas_proyectadas=baseline_uvr.meses_totales,
                    frech_meses_restantes=datos_visible.frech_meses_restantes,
                )
                costo_total_proyectado_banco = (costo_total_proyectado + total_subsidio_frech_proyectado).quantize(Decimal("0.01"))

                proyeccion_actual = replace(
                    proyeccion_actual,
                    cuotas_nuevas=baseline_uvr.meses_totales,
                    costo_total_proyectado=costo_total_proyectado,
                    costo_total_proyectado_banco=costo_total_proyectado_banco,
                    total_subsidio_frech_proyectado=total_subsidio_frech_proyectado,
                    total_por_pagar=costo_total_proyectado,
                )
            except Exception as exc:
                logger.exception(
                    "Fallo baseline UVR V2; se conserva baseline clasico. analisis_id=%s error=%s",
                    getattr(analisis, "id", None),
                    exc,
                )

        total_actual_simple = proyeccion_actual.costo_total_proyectado_banco

        # Indicador comercial de relacion costo/saldo para el escenario "hoy".
        # Semantica unificada: costo total integral (cliente + FRECH) / saldo.
        # Se conserva la clave legacy `veces_pagado_actual` por compatibilidad.
        if datos_proyeccion.saldo_capital > 0:
            veces_pagado_actual = (proyeccion_actual.costo_total_proyectado_banco / datos_proyeccion.saldo_capital).quantize(Decimal("0.01"))
        else:
            veces_pagado_actual = Decimal("0")

        logger.info(
            "UVR/PESOS baseline comparativo analisis_id=%s sistema=%s cuotas_baseline=%s total_banco_baseline=%s tasa_usada=%s valor_uvr_usado=%s inflacion_anual=%s frech_aplicado=%s frech_meses_restantes=%s",
            getattr(analisis, "id", None),
            sistema_amortizacion,
            proyeccion_actual.cuotas_nuevas,
            proyeccion_actual.costo_total_proyectado_banco,
            datos_visible.tasa_interes_ea,
            valor_uvr_actual,
            ipc_anual_proyectado_resuelto,
            datos_visible.beneficio_frech,
            datos_visible.frech_meses_restantes,
        )
        
        return {
            "cuotas_actuales": analisis.cuotas_pendientes,
            "total_actual": proyeccion_actual.costo_total_proyectado,
            "total_actual_simple": total_actual_simple,
            "costo_total_proyectado": proyeccion_actual.costo_total_proyectado,
            "costo_total_proyectado_banco": proyeccion_actual.costo_total_proyectado_banco,
            "total_subsidio_frech_proyectado": proyeccion_actual.total_subsidio_frech_proyectado,
            "veces_pagado_actual": veces_pagado_actual,
            "cuota_actual_visible": datos_visible.valor_cuota_actual,
            "cuota_actual_proyeccion": datos_proyeccion.valor_cuota_actual,
            "cuota_base_source": cuota_base_source,
            "ipc_anual_proyectado": ipc_anual_proyectado_resuelto,
            "datos": datos_visible,
            "datos_visible": datos_visible,
            "datos_proyeccion": datos_proyeccion,
        }

    def _resolve_frech_meses_restantes(self, analisis: AnalisisHipotecario) -> int | None:
        """Resuelve meses FRECH restantes con prioridad al dato explicito.

        Orden de prioridad:
        1) `analisis.frech_meses_restantes` cuando es valido.
        2) Inferencia con `cuotas_pagadas` usando tope FRECH oficial.
        3) `None` para conservar fallback historico en calculadora.
        """
        frech = getattr(analisis, "beneficio_frech_mensual", None) or Decimal("0")
        if frech <= 0:
            return 0

        def _coerce_int(value: object | None) -> int | None:
            if value is None:
                return None
            if isinstance(value, Decimal):
                return int(value)
            if isinstance(value, (int, float, str)):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
            return None

        explicit_value = getattr(analisis, "frech_meses_restantes", None)
        explicit_parsed = _coerce_int(explicit_value)
        if explicit_parsed is not None:
            return max(0, explicit_parsed)
        if explicit_value is not None:
            logger.warning(
                "frech_meses_restantes invalido (%s); se intentara inferir por cuotas_pagadas",
                explicit_value,
            )

        cuotas_pagadas = getattr(analisis, "cuotas_pagadas", None)
        cuotas_pagadas_parsed = _coerce_int(cuotas_pagadas)
        if cuotas_pagadas_parsed is not None:
            pagadas = max(0, cuotas_pagadas_parsed)
            restantes = max(0, FRECH_MAX_MESES_DEFAULT - pagadas)
            logger.info(
                "Inferidos meses FRECH restantes=%s desde cuotas_pagadas=%s (tope=%s)",
                restantes,
                pagadas,
                FRECH_MAX_MESES_DEFAULT,
            )
            return restantes
        if cuotas_pagadas is not None:
            logger.warning(
                "No se pudo inferir FRECH restante desde cuotas_pagadas=%s",
                cuotas_pagadas,
            )

        return None

    def _estimar_cargos_no_amortizables_mensuales(
        self,
        analisis: AnalisisHipotecario,
        cuota_cliente: Decimal,
        frech: Decimal,
    ) -> Decimal:
        """
        Estima cargos mensuales recurrentes. Si no hay datos extraídos de capital/interés,
        usa ingeniería inversa sobre la cuota teórica francesa para aislar los seguros.
        """
        def _as_decimal(value: object | None) -> Decimal:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float, str)):
                try:
                    return Decimal(str(value))
                except Exception:
                    return Decimal("0")
            return Decimal("0")

        seguros_base = _as_decimal(getattr(analisis, "seguros_total_mensual", None))
        otros_cargos = _as_decimal(getattr(analisis, "otros_cargos", None))
        capital_periodo = _as_decimal(getattr(analisis, "capital_pagado_periodo", None))
        interes_periodo = _as_decimal(getattr(analisis, "intereses_corrientes_periodo", None))

        cuota_operativa_raw = getattr(analisis, "valor_cuota_con_seguros", None)
        cuota_operativa = _as_decimal(cuota_operativa_raw)
        if cuota_operativa_raw is None:
            cuota_operativa = cuota_cliente + frech

        cargos_inferidos = Decimal("0")

        # 1. Si tenemos los datos exactos del extracto
        if cuota_operativa > 0 and (capital_periodo > 0 or interes_periodo > 0):
            no_amortizable_observado = cuota_operativa - capital_periodo - interes_periodo
            if no_amortizable_observado > seguros_base:
                cargos_inferidos = no_amortizable_observado - seguros_base

        # 2. Inferencia matemática para PESOS (amortización francesa)
        else:
            sistema = self.calc._normalizar_sistema_amortizacion(getattr(analisis, "sistema_amortizacion", None))
            if sistema == "PESOS":
                tasa_mensual = self.calc.tasa_ea_a_mensual(analisis.tasa_interes_cobrada_ea or Decimal("0"))
                cuotas_restantes = analisis.cuotas_pendientes

                if (
                    tasa_mensual > 0
                    and cuotas_restantes
                    and cuotas_restantes > 0
                    and (analisis.saldo_capital_pesos or Decimal("0")) > 0
                ):
                    cuota_pura_teorica = self.calc.calcular_cuota_fija(
                        capital=analisis.saldo_capital_pesos or Decimal("0"),
                        tasa_mensual=tasa_mensual,
                        num_cuotas=cuotas_restantes,
                    )

                    diferencia = cuota_operativa - cuota_pura_teorica
                    if diferencia > seguros_base:
                        cargos_inferidos = diferencia - seguros_base

        return max(otros_cargos, cargos_inferidos).quantize(Decimal("0.01"))
    
    def _calculate_projection_for_option(
        self,
        analisis: AnalisisHipotecario,
        opcion: OpcionAbonoInput,
        baseline: dict
    ) -> dict:
        """Calcula la proyección para una opción específica de abono."""
        sistema_normalizado = self.calc._normalizar_sistema_amortizacion(analisis.sistema_amortizacion)
        if sistema_normalizado == "UVR" and bool(getattr(self, "uvr_engine_v2_enabled", False)):
            resultado_uvr = self._calculate_projection_for_option_uvr_engine(analisis, opcion, baseline)
            if resultado_uvr is not None:
                return resultado_uvr

        # Politica A: las opciones parten de la cuota visible del extracto.
        datos = baseline.get("datos_visible", baseline["datos"])
        
        # Calcular proyección con abono extra
        proyeccion = self.calc.calcular_proyeccion(
            datos=datos,
            abono_extra=opcion.abono_adicional_mensual,
            numero_opcion=opcion.numero_opcion,
            nombre_opcion=opcion.nombre_opcion or f"Opción {opcion.numero_opcion}"
        )
        
        return {
            "cuotas_nuevas": proyeccion.cuotas_nuevas,
            "tiempo_restante_anios": proyeccion.tiempo_restante.anios,
            "tiempo_restante_meses": proyeccion.tiempo_restante.meses,
            "cuotas_reducidas": proyeccion.cuotas_reducidas,
            "tiempo_ahorrado_anios": proyeccion.tiempo_ahorrado.anios,
            "tiempo_ahorrado_meses": proyeccion.tiempo_ahorrado.meses,
            "nuevo_valor_cuota": proyeccion.nuevo_valor_cuota,
            "total_por_pagar_aprox": proyeccion.total_por_pagar_simple,
            "total_por_pagar_simple": proyeccion.total_por_pagar_simple,
            "costo_total_proyectado": proyeccion.costo_total_proyectado,
            "costo_total_proyectado_banco": proyeccion.costo_total_proyectado_banco,
            "total_subsidio_frech_proyectado": proyeccion.total_subsidio_frech_proyectado,
            "valor_ahorrado_intereses": proyeccion.valor_ahorrado_intereses,
            "veces_pagado": proyeccion.veces_pagado,
            "honorarios_calculados": proyeccion.honorarios,
            "honorarios_con_iva": proyeccion.honorarios_con_iva,
            "ingreso_minimo_requerido": proyeccion.ingreso_minimo_requerido
        }

    def _calculate_projection_for_option_uvr_engine(
        self,
        analisis: AnalisisHipotecario,
        opcion: OpcionAbonoInput,
        baseline: dict,
    ) -> dict | None:
        """Calcula opcion UVR con engine V2 cuando el feature flag esta activo.

        Si falta informacion minima para UVR, retorna None para usar fallback
        al motor actual sin interrumpir el flujo de negocio.
        """
        datos_visible = baseline.get("datos_visible", baseline["datos"])
        ipc_anual_proyectado = baseline.get("ipc_anual_proyectado", self._resolve_ipc_anual_proyectado(None))
        valor_uvr_actual = datos_visible.valor_uvr_actual or analisis.valor_uvr_fecha_extracto

        if not valor_uvr_actual or valor_uvr_actual <= 0:
            logger.warning(
                "UVR engine V2 habilitado pero sin valor UVR valido; usando fallback clasico. analisis_id=%s",
                getattr(analisis, "id", None),
            )
            return None

        try:
            payload = UvrProjectionInput(
                saldo_inicial=datos_visible.saldo_capital,
                tasa_efectiva_anual=datos_visible.tasa_interes_ea,
                tasa_efectiva_anual_subsidiada=getattr(analisis, "tasa_interes_subsidiada_ea", None),
                plazo_meses=datos_visible.cuotas_pendientes,
                cuota_actual=datos_visible.valor_cuota_actual,
                abono_adicional=opcion.abono_adicional_mensual,
                uvr_actual=valor_uvr_actual,
                inflacion_anual_estimada=ipc_anual_proyectado,
                subsidio_frech=datos_visible.beneficio_frech,
                seguro_mensual=(
                    datos_visible.valor_seguro_incendio_fijo
                    + (datos_visible.saldo_capital * datos_visible.tasa_seguro_vida)
                ).quantize(Decimal("0.01")),
                cuota_uvr_actual=getattr(analisis, "valor_cuota_uvr", None),
                frech_meses_restantes=datos_visible.frech_meses_restantes,
            )

            comparacion = compare_uvr_scenarios(payload)

            cuotas_nuevas = comparacion.escenario_con_abono.meses_totales
            tiempo_restante = TiempoAhorro.desde_meses(cuotas_nuevas)
            cuotas_reducidas = max(0, datos_visible.cuotas_pendientes - cuotas_nuevas)
            tiempo_ahorrado = TiempoAhorro.desde_meses(cuotas_reducidas)

            nueva_cuota = (datos_visible.valor_cuota_actual + opcion.abono_adicional_mensual).quantize(Decimal("0.01"))

            costo_total_proyectado = comparacion.escenario_con_abono.total_pagado_cliente
            total_subsidio_frech_proyectado = self.calc.calcular_flujo_frech(
                beneficio_frech_mensual=datos_visible.beneficio_frech,
                cuotas_proyectadas=cuotas_nuevas,
                frech_meses_restantes=datos_visible.frech_meses_restantes,
            )
            costo_total_proyectado_banco = (costo_total_proyectado + total_subsidio_frech_proyectado).quantize(Decimal("0.01"))
            
            total_simple = costo_total_proyectado_banco

            if datos_visible.saldo_capital > 0:
                veces_pagado = (costo_total_proyectado_banco / datos_visible.saldo_capital).quantize(Decimal("0.01"))
            else:
                veces_pagado = Decimal("0")

            baseline_total_banco = baseline.get("costo_total_proyectado_banco")
            if baseline_total_banco is None:
                baseline_total_banco = comparacion.escenario_original.total_pagado_banco
            ahorro_intereses = (baseline_total_banco - costo_total_proyectado_banco).quantize(Decimal("0.01"))
            honorarios = self.calc.calcular_honorarios(ahorro_intereses)
            honorarios_con_iva = self.calc.calcular_honorarios_con_iva(honorarios)
            ingreso_minimo = self.calc.calcular_ingreso_minimo(nueva_cuota)

            logger.info(
                "UVR opcion comparativo analisis_id=%s opcion=%s cuotas_opcion=%s total_banco_opcion=%s tasa_usada=%s valor_uvr_usado=%s inflacion_anual=%s frech_aplicado=%s frech_meses_restantes=%s",
                getattr(analisis, "id", None),
                opcion.numero_opcion,
                cuotas_nuevas,
                costo_total_proyectado_banco,
                datos_visible.tasa_interes_ea,
                valor_uvr_actual,
                ipc_anual_proyectado,
                datos_visible.beneficio_frech,
                datos_visible.frech_meses_restantes,
            )

            return {
                "cuotas_nuevas": cuotas_nuevas,
                "tiempo_restante_anios": tiempo_restante.anios,
                "tiempo_restante_meses": tiempo_restante.meses,
                "cuotas_reducidas": cuotas_reducidas,
                "tiempo_ahorrado_anios": tiempo_ahorrado.anios,
                "tiempo_ahorrado_meses": tiempo_ahorrado.meses,
                "nuevo_valor_cuota": nueva_cuota,
                "total_por_pagar_aprox": total_simple,
                "total_por_pagar_simple": total_simple,
                "costo_total_proyectado": costo_total_proyectado,
                "costo_total_proyectado_banco": costo_total_proyectado_banco,
                "total_subsidio_frech_proyectado": total_subsidio_frech_proyectado,
                "valor_ahorrado_intereses": ahorro_intereses,
                "veces_pagado": veces_pagado,
                "honorarios_calculados": honorarios,
                "honorarios_con_iva": honorarios_con_iva,
                "ingreso_minimo_requerido": ingreso_minimo,
            }
        except Exception as exc:
            logger.exception(
                "Fallo UVR engine V2 en opcion %s; aplicando fallback clasico. analisis_id=%s error=%s",
                opcion.numero_opcion,
                getattr(analisis, "id", None),
                exc,
            )
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_analysis_service(db: Session) -> AnalysisService:
    """Factory function para obtener el servicio de análisis."""
    return AnalysisService(db)
