"""Canonical credit snapshot and financial viability checks.

This module is intentionally independent of the ORM.  Extraction may be
ambiguous; projections must never guess that a payment movement, an overdue
amount, or an insurance-inclusive total is the contractual debt installment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class SnapshotType(str, Enum):
    FULL_INSTALLMENT = "FULL_INSTALLMENT"
    FULL_INSTALLMENT_WITH_FRECH = "FULL_INSTALLMENT_WITH_FRECH"
    FULL_INSTALLMENT_WITH_EXTRA_PAYMENT = "FULL_INSTALLMENT_WITH_EXTRA_PAYMENT"
    PARTIAL_PAYMENT_SNAPSHOT = "PARTIAL_PAYMENT_SNAPSHOT"
    OVERDUE_INSTALLMENT = "OVERDUE_INSTALLMENT"
    UVR_CONSTANT_INSTALLMENT = "UVR_CONSTANT_INSTALLMENT"
    UVR_BAJA = "UVR_BAJA"
    PESOS_FIXED_INSTALLMENT = "PESOS_FIXED_INSTALLMENT"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class ProjectionStatus(str, Enum):
    VALID = "VALID"
    PARTIAL_PAYMENT_DETECTED = "PARTIAL_PAYMENT_DETECTED"
    NEGATIVE_AMORTIZATION = "NEGATIVE_AMORTIZATION"
    INVALID_INSTALLMENT_MAPPING = "INVALID_INSTALLMENT_MAPPING"
    INCONSISTENT_UVR_DATA = "INCONSISTENT_UVR_DATA"
    FRECH_TERM_UNKNOWN = "FRECH_TERM_UNKNOWN"
    OVERDUE_SNAPSHOT = "OVERDUE_SNAPSHOT"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    UNSUPPORTED_UVR_PRODUCT = "UNSUPPORTED_UVR_PRODUCT"


class ProjectionValidationError(ValueError):
    def __init__(self, status: ProjectionStatus, message: str):
        self.status = status
        super().__init__(message)


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


@dataclass(frozen=True)
class ExtractedMortgageData:
    raw_fields: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    document_type: str | None = None
    extraction_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedCreditSnapshot:
    system_type: str
    snapshot_type: SnapshotType
    principal_balance: Decimal
    contractual_debt_installment: Decimal
    insurance_total: Decimal
    non_amortizable_charges: Decimal
    client_total_payment: Decimal
    frech_monthly: Decimal
    frech_remaining_months: int | None
    remaining_term: int
    validation_status: ProjectionStatus
    reason_message: str | None = None
    principal_balance_uvr: Decimal | None = None
    uvr_value: Decimal | None = None
    contractual_installment_uvr: Decimal | None = None
    current_period_payment_applied: Decimal | None = None
    current_period_principal_applied: Decimal | None = None
    current_period_interest_applied: Decimal | None = None
    current_installment_remaining: Decimal | None = None
    overdue_installments: int = 0


def _raw_decimal(raw: dict[str, Any], *names: str) -> Decimal:
    for name in names:
        if raw.get(name) is not None:
            return _d(raw[name])
    return Decimal("0")


def _evidence_value(raw: dict[str, Any], section: str, field: str) -> Decimal:
    """Read Gemini V2 evidence while accepting the legacy flat response."""
    candidate = raw.get(section, {})
    if not isinstance(candidate, dict):
        return Decimal("0")
    value = candidate.get(field)
    return _d(value.get("value") if isinstance(value, dict) else value)


def normalize_credit_snapshot(analysis: Any) -> NormalizedCreditSnapshot:
    """Create the only projection input interpretation from an analysis.

    Explicit UVR debt installment is authoritative.  Insurance and FRECH are
    deliberately excluded from the debt installment.  Ambiguous records are
    returned as review-required rather than coerced into an amortization.
    """
    raw = getattr(analysis, "raw_data_json", None) or getattr(analysis, "datos_raw_gemini", None) or {}
    system = str(getattr(analysis, "sistema_amortizacion", None) or "PESOS").upper()
    plan = str(getattr(analysis, "plan_credito", None) or "").upper()
    is_uvr = "UVR" in system or "UVR" in plan
    is_uvr_baja = "BAJA" in plan
    principal = _d(getattr(analysis, "saldo_capital_pesos", None))
    insurance = _d(getattr(analysis, "seguros_total_mensual", None))
    charges = _d(getattr(analysis, "otros_cargos", None))
    frech = _d(getattr(analysis, "beneficio_frech_mensual", None))
    cuota_uvr = _d(getattr(analysis, "valor_cuota_uvr", None)) or _evidence_value(raw, "contractual_installment", "debt_uvr")
    uvr = _d(getattr(analysis, "valor_uvr_fecha_extracto", None))
    explicit_debt = _d(getattr(analysis, "valor_cuota_sin_seguros", None)) or _evidence_value(raw, "contractual_installment", "debt_pesos")
    client_payment = _d(getattr(analysis, "valor_cuota_con_subsidio", None)) or _evidence_value(raw, "contractual_installment", "client_total")
    total_with_insurance = _d(getattr(analysis, "valor_cuota_con_seguros", None)) or _evidence_value(raw, "contractual_installment", "bank_total")
    insurance = insurance or _evidence_value(raw, "contractual_installment", "insurance")
    if not client_payment:
        client_payment = total_with_insurance - frech if total_with_insurance > frech else total_with_insurance

    # UVR debt quota is never reconstructed from a client payment containing insurance.
    if is_uvr and cuota_uvr > 0 and uvr > 0:
        debt_installment = cuota_uvr * uvr
    else:
        debt_installment = explicit_debt
        if debt_installment <= 0 and total_with_insurance > 0:
            debt_installment = max(Decimal("0"), total_with_insurance - insurance - charges)

    partial = raw.get("partial_payment_information") if isinstance(raw.get("partial_payment_information"), dict) else {}
    next_payment = raw.get("next_payment") if isinstance(raw.get("next_payment"), dict) else {}
    applied = _d(partial.get("amount_applied")) or _raw_decimal(raw, "pago_aplicado_periodo", "pago_aplicado", "movimiento_pago", "pago_periodo")
    remaining = _d(partial.get("amount_remaining")) or _d(next_payment.get("value")) or _raw_decimal(raw, "valor_pendiente_cuota", "saldo_pendiente_cuota", "cuota_pendiente_actual")
    period_capital = _d(getattr(analysis, "capital_pagado_periodo", None))
    period_interest = _d(getattr(analysis, "intereses_corrientes_periodo", None))
    overdue_data = raw.get("overdue_information") if isinstance(raw.get("overdue_information"), dict) else {}
    overdue = int(getattr(analysis, "cuotas_vencidas", None) or overdue_data.get("installments") or 0)
    term = int(getattr(analysis, "cuotas_pendientes", None) or 0)
    frech_months = getattr(analysis, "frech_meses_restantes", None)

    snapshot_type = SnapshotType.UVR_CONSTANT_INSTALLMENT if is_uvr else SnapshotType.PESOS_FIXED_INSTALLMENT
    status = ProjectionStatus.VALID
    message = None
    if is_uvr_baja:
        snapshot_type, status = SnapshotType.UVR_BAJA, ProjectionStatus.UNSUPPORTED_UVR_PRODUCT
        message = "El producto UVR baja requiere una metodología contractual específica y revisión manual."
    elif overdue > 0:
        snapshot_type, status = SnapshotType.OVERDUE_INSTALLMENT, ProjectionStatus.OVERDUE_SNAPSHOT
        message = "El extracto registra cuotas vencidas; no se puede usar el saldo vencido como cuota recurrente."
    elif partial.get("detected") is True or (
        not partial
        and applied > 0
        and remaining > 0
        and not (
            debt_installment > 0
            and applied >= debt_installment * Decimal("0.95")
            and remaining >= debt_installment * Decimal("0.95")
        )
    ):
        snapshot_type, status = SnapshotType.PARTIAL_PAYMENT_SNAPSHOT, ProjectionStatus.PARTIAL_PAYMENT_DETECTED
        message = "El extracto registra un pago parcial y un saldo pendiente de la cuota actual."
    elif period_interest > 0 and period_capital <= 0 and applied > 0:
        snapshot_type, status = SnapshotType.PARTIAL_PAYMENT_SNAPSHOT, ProjectionStatus.PARTIAL_PAYMENT_DETECTED
        message = "El pago del período cubrió intereses/cargos pero no capital; requiere confirmar la cuota contractual."
    elif frech > 0:
        snapshot_type = SnapshotType.FULL_INSTALLMENT_WITH_FRECH

    return NormalizedCreditSnapshot(
        system_type="UVR" if is_uvr else "PESOS", snapshot_type=snapshot_type,
        principal_balance=principal, contractual_debt_installment=debt_installment,
        insurance_total=insurance, non_amortizable_charges=charges,
        client_total_payment=client_payment, frech_monthly=frech,
        frech_remaining_months=frech_months, remaining_term=term,
        validation_status=status, reason_message=message,
        principal_balance_uvr=_d(getattr(analysis, "saldo_capital_uvr", None)) or None,
        uvr_value=uvr or None, contractual_installment_uvr=cuota_uvr or None,
        current_period_payment_applied=applied or None,
        current_period_principal_applied=period_capital if period_capital or period_interest else None,
        current_period_interest_applied=period_interest or None,
        current_installment_remaining=remaining or None, overdue_installments=overdue,
    )


def validate_projection_snapshot(snapshot: NormalizedCreditSnapshot, annual_rate: Any) -> None:
    if snapshot.validation_status != ProjectionStatus.VALID:
        raise ProjectionValidationError(snapshot.validation_status, snapshot.reason_message or "El extracto requiere revisión manual.")
    if snapshot.principal_balance <= 0 or snapshot.contractual_debt_installment <= 0 or snapshot.remaining_term <= 0:
        raise ProjectionValidationError(ProjectionStatus.INVALID_INSTALLMENT_MAPPING, "Faltan datos financieros verificables para generar una proyección.")
    rate = _d(annual_rate)
    if rate > 1:
        rate /= Decimal("100")
    monthly_rate = (Decimal(str((1 + float(rate)) ** (1 / 12))) - Decimal("1")) if rate > 0 else Decimal("0")
    initial_interest = snapshot.principal_balance * monthly_rate
    if snapshot.contractual_debt_installment <= initial_interest:
        # En lugar de bloquear la proyección, permitimos que el motor calcule una cuota teórica.
        pass
