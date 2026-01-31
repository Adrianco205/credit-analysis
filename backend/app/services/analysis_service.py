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
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.analisis import AnalisisHipotecario
from app.models.documento import DocumentoS3
from app.models.propuesta import PropuestaAhorro
from app.models.user import Usuario
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
from app.services.calc_service import (
    CalculadoraFinanciera, 
    crear_calculadora,
    DatosCredito,
    TiempoAhorro
)

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
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FLUJO PRINCIPAL: CREAR ANÁLISIS DESDE DOCUMENTO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def create_analysis_from_document(
        self,
        documento_id: uuid.UUID,
        usuario: Usuario,
        datos_usuario: DatosUsuarioInput,
        skip_name_validation: bool = False
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
            
            # ════════════════════════════════════════════════════════════════
            # MEJORA 1: VALIDACIÓN DE TIPO DE DOCUMENTO
            # ════════════════════════════════════════════════════════════════
            if extraction_result.status == ExtractionStatus.NOT_CREDIT_DOCUMENT:
                # Extraer el tipo de documento detectado del raw response
                tipo_detectado = extraction_result.data.get("tipo_documento_detectado", "Documento no reconocido")
                return AnalysisCreationResult(
                    success=False,
                    error_code="INVALID_DOCUMENT_TYPE",
                    error_message=f"El documento subido no es un extracto de crédito hipotecario. Se detectó: {tipo_detectado}",
                    invalid_document_type=True,
                    tipo_documento_detectado=tipo_detectado
                )
            
            if extraction_result.status == ExtractionStatus.API_ERROR:
                return AnalysisCreationResult(
                    success=False,
                    error_code="EXTRACTION_ERROR",
                    error_message=f"Error en extracción: {extraction_result.message}"
                )
            
            # 4. Validar nombre (si no se omite)
            name_match = True
            if not skip_name_validation and extraction_result.data.get("nombre_titular"):
                nombre_usuario = self._build_user_full_name(usuario)
                nombre_pdf = extraction_result.data.get("nombre_titular", "")
                
                comparison = await self.gemini.compare_names(nombre_pdf, nombre_usuario)
                name_match = comparison.match
                
                if not name_match:
                    logger.warning(
                        f"Nombre no coincide. PDF: {nombre_pdf}, Usuario: {nombre_usuario}"
                    )
            
            # ════════════════════════════════════════════════════════════════
            # MEJORA 4: VALIDACIÓN DE CÉDULA/IDENTIFICACIÓN
            # ════════════════════════════════════════════════════════════════
            id_match = True
            identificacion_pdf = extraction_result.data.get("identificacion_titular")
            if identificacion_pdf and usuario.identificacion:
                # Normalizar: quitar espacios, puntos, guiones
                id_pdf_normalized = str(identificacion_pdf).replace(".", "").replace("-", "").replace(" ", "").strip()
                id_user_normalized = str(usuario.identificacion).replace(".", "").replace("-", "").replace(" ", "").strip()
                
                id_match = id_pdf_normalized == id_user_normalized
                
                if not id_match:
                    logger.warning(
                        f"Cédula no coincide. PDF: {identificacion_pdf} ({id_pdf_normalized}), "
                        f"Usuario: {usuario.identificacion} ({id_user_normalized})"
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
            
            # Determinar estado inicial
            campos_faltantes = extraction_result.campos_faltantes or []
            requires_manual = self._check_requires_manual_input(
                extraction_result.data, 
                campos_faltantes
            )
            
            # ════════════════════════════════════════════════════════════════
            # DETERMINAR ESTADO CON NUEVA LÓGICA DE VALIDACIÓN
            # ════════════════════════════════════════════════════════════════
            if not name_match and not id_match:
                # Ambos no coinciden: potencial fraude crítico
                analisis_data["status"] = "ID_MISMATCH"  # Prioritario sobre NAME_MISMATCH
            elif not id_match:
                # Cédula no coincide (nombre puede coincidir): alerta crítica
                analisis_data["status"] = "ID_MISMATCH"
            elif not name_match:
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
            
            return AnalysisCreationResult(
                success=True,
                analisis=analisis,
                requires_manual_input=requires_manual,
                campos_faltantes=campos_faltantes if requires_manual else None,
                campos_extraidos=extraction_result.campos_encontrados,  # NUEVO
                name_mismatch=not name_match,
                id_mismatch=not id_match  # NUEVO
            )
            
        except Exception as e:
            logger.exception(f"Error creando análisis: {e}")
            self.db.rollback()
            return AnalysisCreationResult(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=str(e)
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
        campos_criticos = {
            "saldo_capital_pesos": analisis.saldo_capital_pesos,
            "valor_cuota_con_seguros": analisis.valor_cuota_con_seguros,
            "cuotas_pendientes": analisis.cuotas_pendientes,
            "tasa_interes_cobrada_ea": analisis.tasa_interes_cobrada_ea
        }
        return [campo for campo, valor in campos_criticos.items() if valor is None]
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # GENERACIÓN DE PROYECCIONES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def generate_projections(
        self,
        analisis_id: uuid.UUID,
        opciones: list[OpcionAbonoInput],
        usuario_id: uuid.UUID | None = None
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
            
            # Calcular estado actual (baseline)
            baseline = self._calculate_baseline(analisis)
            
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
            "valor_cuota_con_seguros", 
            "cuotas_pendientes",
            "tasa_interes_cobrada_ea"
        }
        
        # Verificar si algún campo crítico falta
        for campo in campos_criticos:
            if campo in campos_faltantes:
                return True
            if extracted_data.get(campo) is None:
                return True
        
        return False
    
    def _validate_analysis_for_projection(self, analisis: AnalisisHipotecario) -> bool:
        """Valida que el análisis tenga los datos mínimos para generar proyecciones."""
        required_fields = [
            analisis.saldo_capital_pesos,
            analisis.valor_cuota_con_seguros,
            analisis.cuotas_pendientes,
            analisis.tasa_interes_cobrada_ea,
            analisis.valor_prestado_inicial
        ]
        return all(f is not None for f in required_fields)
    
    def _calculate_baseline(self, analisis: AnalisisHipotecario) -> dict:
        """Calcula el estado actual del crédito (sin abono extra)."""
        # Crear objeto DatosCredito
        datos = DatosCredito(
            saldo_capital=analisis.saldo_capital_pesos,
            valor_cuota_actual=analisis.valor_cuota_con_seguros,
            cuotas_pendientes=analisis.cuotas_pendientes,
            tasa_interes_ea=analisis.tasa_interes_cobrada_ea,
            valor_prestado_inicial=analisis.valor_prestado_inicial,
            beneficio_frech=analisis.beneficio_frech_mensual or Decimal("0"),
            seguros_mensual=analisis.seguros_total_mensual or Decimal("0"),
            sistema_amortizacion=analisis.sistema_amortizacion or "PESOS"
        )
        
        # Calcular proyección actual (sin abono extra)
        proyeccion_actual = self.calc.calcular_proyeccion(
            datos=datos,
            abono_extra=Decimal("0"),
            numero_opcion=0,
            nombre_opcion="Actual"
        )
        
        return {
            "cuotas_actuales": analisis.cuotas_pendientes,
            "total_actual": proyeccion_actual.total_por_pagar,
            "datos": datos
        }
    
    def _calculate_projection_for_option(
        self,
        analisis: AnalisisHipotecario,
        opcion: OpcionAbonoInput,
        baseline: dict
    ) -> dict:
        """Calcula la proyección para una opción específica de abono."""
        datos = baseline["datos"]
        
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
            "total_por_pagar_aprox": proyeccion.total_por_pagar,
            "valor_ahorrado_intereses": proyeccion.valor_ahorrado_intereses,
            "veces_pagado": proyeccion.veces_pagado,
            "honorarios_calculados": proyeccion.honorarios,
            "honorarios_con_iva": proyeccion.honorarios_con_iva,
            "ingreso_minimo_requerido": proyeccion.ingreso_minimo_requerido
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_analysis_service(db: Session) -> AnalysisService:
    """Factory function para obtener el servicio de análisis."""
    return AnalysisService(db)
