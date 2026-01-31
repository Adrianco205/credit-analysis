"""
Repository para Análisis Hipotecario.
CRUD y consultas especializadas para la tabla analisis_hipotecario.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from app.models.analisis import AnalisisHipotecario
from app.models.documento import DocumentoS3
from app.models.user import Usuario


class AnalysesRepo:
    """Repository para operaciones de Análisis Hipotecario."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CRUD BÁSICO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def create(self, **kwargs) -> AnalisisHipotecario:
        """Crear un nuevo análisis."""
        analisis = AnalisisHipotecario(**kwargs)
        self.db.add(analisis)
        self.db.flush()
        return analisis
    
    def save(self, analisis: AnalisisHipotecario) -> AnalisisHipotecario:
        """Guardar cambios en un análisis existente."""
        self.db.add(analisis)
        self.db.flush()
        return analisis
    
    def get_by_id(self, analisis_id: uuid.UUID) -> AnalisisHipotecario | None:
        """Obtener análisis por ID."""
        return self.db.execute(
            select(AnalisisHipotecario).where(AnalisisHipotecario.id == analisis_id)
        ).scalar_one_or_none()
    
    def get_by_id_and_user(
        self, 
        analisis_id: uuid.UUID, 
        usuario_id: uuid.UUID
    ) -> AnalisisHipotecario | None:
        """Obtener análisis verificando que pertenezca al usuario."""
        return self.db.execute(
            select(AnalisisHipotecario).where(
                and_(
                    AnalisisHipotecario.id == analisis_id,
                    AnalisisHipotecario.usuario_id == usuario_id
                )
            )
        ).scalar_one_or_none()
    
    def get_by_documento(self, documento_id: uuid.UUID) -> AnalisisHipotecario | None:
        """Obtener análisis por documento asociado."""
        return self.db.execute(
            select(AnalisisHipotecario).where(
                AnalisisHipotecario.documento_id == documento_id
            )
        ).scalar_one_or_none()
    
    def delete(self, analisis: AnalisisHipotecario) -> None:
        """Eliminar un análisis."""
        self.db.delete(analisis)
        self.db.flush()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CONSULTAS POR USUARIO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def list_by_user(
        self, 
        usuario_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Sequence[AnalisisHipotecario]:
        """Listar análisis de un usuario."""
        return self.db.execute(
            select(AnalisisHipotecario)
            .where(AnalisisHipotecario.usuario_id == usuario_id)
            .order_by(AnalisisHipotecario.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    
    def count_by_user(self, usuario_id: uuid.UUID) -> int:
        """Contar análisis de un usuario."""
        result = self.db.execute(
            select(func.count(AnalisisHipotecario.id))
            .where(AnalisisHipotecario.usuario_id == usuario_id)
        ).scalar()
        return result or 0
    
    def get_latest_by_user(self, usuario_id: uuid.UUID) -> AnalisisHipotecario | None:
        """Obtener el análisis más reciente de un usuario."""
        return self.db.execute(
            select(AnalisisHipotecario)
            .where(AnalisisHipotecario.usuario_id == usuario_id)
            .order_by(AnalisisHipotecario.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CONSULTAS POR ESTADO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def list_by_status(
        self, 
        status: str,
        skip: int = 0,
        limit: int = 50
    ) -> Sequence[AnalisisHipotecario]:
        """Listar análisis por estado."""
        return self.db.execute(
            select(AnalisisHipotecario)
            .where(AnalisisHipotecario.status == status)
            .order_by(AnalisisHipotecario.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    
    def list_pending_manual(
        self, 
        usuario_id: uuid.UUID | None = None
    ) -> Sequence[AnalisisHipotecario]:
        """Listar análisis que requieren datos manuales."""
        query = select(AnalisisHipotecario).where(
            AnalisisHipotecario.status == "PENDING_MANUAL"
        )
        if usuario_id:
            query = query.where(AnalisisHipotecario.usuario_id == usuario_id)
        return self.db.execute(query).scalars().all()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CONSULTAS ADMIN (Filtros avanzados)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def search_admin(
        self,
        cedula: str | None = None,
        numero_credito: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[Sequence[AnalisisHipotecario], int]:
        """
        Búsqueda avanzada para panel administrativo.
        Retorna (resultados, total_count).
        """
        # Query base con joins para filtrar por cédula
        query = select(AnalisisHipotecario)
        count_query = select(func.count(AnalisisHipotecario.id))
        
        conditions = []
        
        # Filtro por cédula (requiere join con usuarios)
        if cedula:
            query = query.join(Usuario, AnalisisHipotecario.usuario_id == Usuario.id)
            count_query = count_query.join(Usuario, AnalisisHipotecario.usuario_id == Usuario.id)
            conditions.append(Usuario.identificacion.ilike(f"%{cedula}%"))
        
        # Filtro por número de crédito
        if numero_credito:
            conditions.append(
                AnalisisHipotecario.numero_credito.ilike(f"%{numero_credito}%")
            )
        
        # Filtro por rango de fechas
        if fecha_desde:
            conditions.append(AnalisisHipotecario.fecha_extracto >= fecha_desde)
        if fecha_hasta:
            conditions.append(AnalisisHipotecario.fecha_extracto <= fecha_hasta)
        
        # Filtro por estado
        if status:
            conditions.append(AnalisisHipotecario.status == status)
        
        # Aplicar condiciones
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Contar total
        total = self.db.execute(count_query).scalar() or 0
        
        # Ejecutar con paginación
        results = self.db.execute(
            query.order_by(AnalisisHipotecario.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        
        return results, total
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ACTUALIZACIONES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def update_status(
        self, 
        analisis_id: uuid.UUID, 
        new_status: str
    ) -> AnalisisHipotecario | None:
        """Actualizar estado de un análisis."""
        analisis = self.get_by_id(analisis_id)
        if analisis:
            analisis.status = new_status
            self.db.flush()
        return analisis
    
    def update_from_extraction(
        self,
        analisis_id: uuid.UUID,
        extraction_data: dict,
        confidence: float,
        campos_faltantes: list[str] | None = None
    ) -> AnalisisHipotecario | None:
        """
        Actualizar análisis con datos extraídos de Gemini.
        """
        analisis = self.get_by_id(analisis_id)
        if not analisis:
            return None
        
        # Mapear campos de extracción al modelo
        field_mapping = {
            "nombre_titular": "nombre_titular_extracto",
            "numero_credito": "numero_credito",
            "sistema_amortizacion": "sistema_amortizacion",
            "plan_credito": "plan_credito",
            "fecha_desembolso": "fecha_desembolso",
            "fecha_extracto": "fecha_extracto",
            "plazo_total_meses": "plazo_total_meses",
            "cuotas_pactadas": "cuotas_pactadas",
            "cuotas_pagadas": "cuotas_pagadas",
            "cuotas_pendientes": "cuotas_pendientes",
            "cuotas_vencidas": "cuotas_vencidas",
            "tasa_interes_pactada_ea": "tasa_interes_pactada_ea",
            "tasa_interes_cobrada_ea": "tasa_interes_cobrada_ea",
            "tasa_interes_subsidiada_ea": "tasa_interes_subsidiada_ea",
            "tasa_mora_ea": "tasa_mora_pactada_ea",
            "valor_prestado_inicial": "valor_prestado_inicial",
            "valor_cuota_sin_seguros": "valor_cuota_sin_seguros",
            "valor_cuota_con_seguros": "valor_cuota_con_seguros",
            "beneficio_frech_mensual": "beneficio_frech_mensual",
            "valor_cuota_con_subsidio": "valor_cuota_con_subsidio",
            "saldo_capital_pesos": "saldo_capital_pesos",
            "total_por_pagar": "total_por_pagar",
            "saldo_capital_uvr": "saldo_capital_uvr",
            "valor_uvr_fecha_extracto": "valor_uvr_fecha_extracto",
            "valor_cuota_uvr": "valor_cuota_uvr",
            "seguro_vida": "seguro_vida",
            "seguro_incendio": "seguro_incendio",
            "seguro_terremoto": "seguro_terremoto",
        }
        
        for ext_field, model_field in field_mapping.items():
            if ext_field in extraction_data and extraction_data[ext_field] is not None:
                setattr(analisis, model_field, extraction_data[ext_field])
        
        # Calcular seguros totales
        seguros = [
            extraction_data.get("seguro_vida"),
            extraction_data.get("seguro_incendio"),
            extraction_data.get("seguro_terremoto")
        ]
        seguros_validos = [s for s in seguros if s is not None]
        if seguros_validos:
            analisis.seguros_total_mensual = sum(seguros_validos)
        
        # Guardar respuesta raw de Gemini
        analisis.datos_raw_gemini = extraction_data
        
        # Determinar estado
        if campos_faltantes and len(campos_faltantes) > 0:
            # Campos críticos que DEBEN estar presentes
            campos_criticos = {
                "saldo_capital_pesos", "valor_cuota_con_seguros",
                "cuotas_pendientes", "tasa_interes_cobrada_ea"
            }
            faltantes_criticos = campos_criticos & set(campos_faltantes)
            if faltantes_criticos:
                analisis.status = "PENDING_MANUAL"
            else:
                analisis.status = "EXTRACTED"
        else:
            analisis.status = "EXTRACTED"
        
        self.db.flush()
        return analisis
    
    def update_manual_fields(
        self,
        analisis: AnalisisHipotecario,
        manual_data: dict
    ) -> AnalisisHipotecario:
        """
        Actualizar campos proporcionados manualmente por el usuario.
        Solo permite campos que NO fueron extraídos automáticamente.
        """
        campos_actualizados = []
        
        for field, value in manual_data.items():
            if value is not None and hasattr(analisis, field):
                setattr(analisis, field, value)
                campos_actualizados.append(field)
        
        # Registrar qué campos fueron manuales
        analisis.campos_manuales = campos_actualizados
        
        # Verificar si ya está completo
        campos_requeridos = [
            "saldo_capital_pesos", "valor_cuota_con_seguros",
            "cuotas_pendientes", "tasa_interes_cobrada_ea"
        ]
        completo = all(
            getattr(analisis, campo) is not None 
            for campo in campos_requeridos
        )
        
        if completo and analisis.status == "PENDING_MANUAL":
            analisis.status = "EXTRACTED"
        
        self.db.flush()
        return analisis
    
    def validate_name_match(
        self,
        analisis: AnalisisHipotecario,
        match_result: bool,
        similarity: float
    ) -> AnalisisHipotecario:
        """Registrar resultado de validación de nombre."""
        analisis.nombre_coincide = match_result
        
        if not match_result:
            analisis.status = "NAME_MISMATCH"
        elif analisis.status == "EXTRACTED":
            analisis.status = "VALIDATED"
        
        self.db.flush()
        return analisis
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CÁLCULOS DERIVADOS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def calculate_derived_fields(
        self,
        analisis: AnalisisHipotecario
    ) -> AnalisisHipotecario:
        """
        Calcular campos derivados para el resumen del crédito.
        Debe llamarse después de tener todos los datos básicos.
        """
        # Total pagado a la fecha
        if analisis.valor_cuota_con_seguros and analisis.cuotas_pagadas:
            analisis.total_pagado_fecha = (
                analisis.valor_cuota_con_seguros * analisis.cuotas_pagadas
            )
        
        # Total FRECH recibido
        if analisis.beneficio_frech_mensual and analisis.cuotas_pagadas:
            analisis.total_frech_recibido = (
                analisis.beneficio_frech_mensual * analisis.cuotas_pagadas
            )
        
        # Monto real pagado al banco (incluyendo FRECH)
        if analisis.total_pagado_fecha and analisis.total_frech_recibido:
            analisis.monto_real_pagado_banco = (
                analisis.total_pagado_fecha + analisis.total_frech_recibido
            )
        
        # Ajuste por inflación (solo UVR)
        if analisis.sistema_amortizacion == "UVR":
            if analisis.saldo_capital_pesos and analisis.valor_prestado_inicial:
                analisis.ajuste_inflacion_pesos = (
                    analisis.saldo_capital_pesos - analisis.valor_prestado_inicial
                )
                if analisis.valor_prestado_inicial > 0:
                    analisis.porcentaje_ajuste_inflacion = (
                        analisis.ajuste_inflacion_pesos / analisis.valor_prestado_inicial
                    )
        
        self.db.flush()
        return analisis


def get_analyses_repo(db: Session) -> AnalysesRepo:
    """Factory function para obtener el repositorio."""
    return AnalysesRepo(db)
