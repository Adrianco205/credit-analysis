import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Boolean, Date, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalisisHipotecario(Base):
    """
    Modelo para análisis de crédito hipotecario.
    Almacena datos extraídos del PDF y proporcionados por el usuario.
    """
    __tablename__ = "analisis_hipotecario"

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
    
    # Datos proporcionados por el usuario
    ingresos_mensuales: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    capacidad_pago_max: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    tipo_contrato_laboral: Mapped[str | None] = mapped_column(String(80))
    
    # Datos básicos del crédito (extraídos del PDF)
    numero_credito: Mapped[str | None] = mapped_column(String(50))
    sistema_amortizacion: Mapped[str | None] = mapped_column(String(20))  # UVR, PESOS, etc.
    valor_prestado_inicial: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    fecha_desembolso: Mapped[date | None] = mapped_column(Date)
    
    # Estado del crédito
    cuotas_pactadas: Mapped[int | None] = mapped_column(Integer)
    cuotas_pagadas: Mapped[int | None] = mapped_column(Integer)
    cuotas_pendientes: Mapped[int | None] = mapped_column(Integer)
    
    # Montos actuales
    valor_cuota_actual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    beneficio_frech_mensual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    saldo_capital_hoy: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    
    # Ajustes y cargos
    ajuste_inflacion_pesos: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    intereses_mes_actual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    seguros_totales: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    
    # Validaciones
    es_analisis_real: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    validado_por_sistema: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    
    # Datos manuales ingresados por el usuario (JSON flexible)
    datos_manuales_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
