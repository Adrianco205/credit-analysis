import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Boolean, Date, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalisisHipotecario(Base):
    """
    Modelo para análisis de crédito hipotecario.
    Almacena datos extraídos del PDF y proporcionados por el usuario.
    """
    __tablename__ = "analisis_hipotecario"
    __table_args__ = (
        Index("ix_analisis_numero_credito", "numero_credito"),
        Index("ix_analisis_fecha_extracto", "fecha_extracto"),
        Index("ix_analisis_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documentos_s3.id", ondelete="CASCADE"),
        nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # DATOS PROPORCIONADOS POR EL USUARIO
    # ═══════════════════════════════════════════════════════════════════
    ingresos_mensuales: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    capacidad_pago_max: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    tipo_contrato_laboral: Mapped[str | None] = mapped_column(String(80))
    
    # ═══════════════════════════════════════════════════════════════════
    # DATOS BÁSICOS DEL CRÉDITO (Extraídos del PDF)
    # ═══════════════════════════════════════════════════════════════════
    nombre_titular_extracto: Mapped[str | None] = mapped_column(String(200))  # Para validar vs usuario
    numero_credito: Mapped[str | None] = mapped_column(String(50))
    banco_id: Mapped[int | None] = mapped_column(ForeignKey("bancos.id", ondelete="SET NULL"))
    
    sistema_amortizacion: Mapped[str | None] = mapped_column(String(20))  # UVR, PESOS
    plan_credito: Mapped[str | None] = mapped_column(String(100))  # Ej: CUOTA CONSTANTE EN UVR-VIVDA VIS
    valor_prestado_inicial: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    fecha_desembolso: Mapped[date | None] = mapped_column(Date)
    fecha_extracto: Mapped[date | None] = mapped_column(Date)  # Fecha del documento
    plazo_total_meses: Mapped[int | None] = mapped_column(Integer)  # 360, 180, etc.
    
    # ═══════════════════════════════════════════════════════════════════
    # ESTADO DEL CRÉDITO (Cuotas)
    # ═══════════════════════════════════════════════════════════════════
    cuotas_pactadas: Mapped[int | None] = mapped_column(Integer)
    cuotas_pagadas: Mapped[int | None] = mapped_column(Integer)
    cuotas_pendientes: Mapped[int | None] = mapped_column(Integer)
    cuotas_vencidas: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    
    # ═══════════════════════════════════════════════════════════════════
    # TASAS DE INTERÉS (Efectiva Anual)
    # ═══════════════════════════════════════════════════════════════════
    tasa_interes_pactada_ea: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))  # 9.53% -> 0.0953
    tasa_interes_cobrada_ea: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))  # 4.71%
    tasa_interes_subsidiada_ea: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))  # 4.00%
    tasa_mora_pactada_ea: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))  # 14.30%
    
    # ═══════════════════════════════════════════════════════════════════
    # MONTOS EN PESOS
    # ═══════════════════════════════════════════════════════════════════
    valor_cuota_sin_seguros: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    valor_cuota_con_seguros: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Cuota completa
    beneficio_frech_mensual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    valor_cuota_con_subsidio: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Lo que paga el cliente
    
    saldo_capital_pesos: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Saldo actual en COP
    total_por_pagar: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # A la fecha del extracto
    
    # ═══════════════════════════════════════════════════════════════════
    # DATOS UVR (Si aplica)
    # ═══════════════════════════════════════════════════════════════════
    saldo_capital_uvr: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))  # 149,292.3850
    valor_uvr_fecha_extracto: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))  # 376.1794
    valor_cuota_uvr: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))  # 810.8742
    
    # ═══════════════════════════════════════════════════════════════════
    # SEGUROS MENSUALES
    # ═══════════════════════════════════════════════════════════════════
    seguro_vida: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    seguro_incendio: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    seguro_terremoto: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    seguros_total_mensual: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    
    # ═══════════════════════════════════════════════════════════════════
    # CÁLCULOS DERIVADOS (Para el Resumen)
    # ═══════════════════════════════════════════════════════════════════
    total_pagado_fecha: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Cuota × meses pagados
    total_frech_recibido: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Subsidio × meses
    monto_real_pagado_banco: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Total + FRECH
    ajuste_inflacion_pesos: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Saldo - Valor prestado
    porcentaje_ajuste_inflacion: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))  # -24.05%
    total_intereses_seguros: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Costos extra
    
    # ═══════════════════════════════════════════════════════════════════
    # PREFERENCIAS DE ABONO DEL USUARIO (Capturadas antes de proyecciones)
    # ═══════════════════════════════════════════════════════════════════
    # Las opciones de abono extra que el usuario define (ej: [200000, 300000, 400000])
    opciones_abono_preferidas: Mapped[list | None] = mapped_column(JSONB)  # [200000, 300000, 400000]
    abono_adicional_actual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Siempre NULL en diagnóstico inicial
    
    # ═══════════════════════════════════════════════════════════════════
    # VALIDACIONES Y ESTADO
    # ═══════════════════════════════════════════════════════════════════
    nombre_coincide: Mapped[bool | None] = mapped_column(Boolean)  # Validación nombre PDF vs usuario
    cedula_coincide: Mapped[bool | None] = mapped_column(Boolean)  # Validación cédula PDF vs usuario (NUEVO)
    identificacion_extracto: Mapped[str | None] = mapped_column(String(20))  # Cédula extraída del PDF (NUEVO)
    tipo_documento_detectado: Mapped[str | None] = mapped_column(String(100))  # Tipo de documento si NO es hipotecario
    es_extracto_hipotecario: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    status: Mapped[str] = mapped_column(
        String(30), 
        server_default=text("'PENDING_EXTRACTION'")
    )  # PENDING_EXTRACTION, EXTRACTED, VALIDATED, NAME_MISMATCH, ID_MISMATCH, INVALID_DOCUMENT, ERROR
    
    # Campos que el usuario llenó manualmente (si Gemini no los detectó)
    campos_manuales: Mapped[list | None] = mapped_column(JSONB)  # ["tasa_interes", "seguros"]
    campos_extraidos_ia: Mapped[list | None] = mapped_column(JSONB)  # Campos exitosamente extraídos (READONLY)
    datos_raw_gemini: Mapped[dict | None] = mapped_column(JSONB)  # Respuesta cruda de Gemini
    
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))
