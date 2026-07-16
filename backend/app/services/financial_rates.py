"""Centralised financial-rate conversions — single source of truth.

Every rate conversion in the system must use these functions.
All arithmetic stays in ``Decimal``; no ``float`` intermediaries.
"""
from __future__ import annotations

from decimal import Decimal, localcontext

ONE = Decimal("1")
TWELVE = Decimal("12")
HUNDRED = Decimal("100")
RATE_PRECISION = Decimal("0.000000000001")


def normalize_rate(rate: Decimal) -> Decimal:
    """Return a rate in decimal form (e.g. 0.05 for 5 %).

    If *rate* > 1 it is assumed to be expressed as a percentage.
    """
    if rate <= 0:
        return Decimal("0")
    return rate / HUNDRED if rate > ONE else rate


def annual_effective_to_monthly(rate: Decimal) -> Decimal:
    """Convert an annual effective rate to a monthly effective rate.

    Formula:  ``(1 + EA)^(1/12) - 1``  computed entirely in Decimal.
    """
    normalized = normalize_rate(rate)
    if normalized <= 0:
        return Decimal("0")
    with localcontext() as ctx:
        ctx.prec = 32
        monthly = ((ONE + normalized).ln() / TWELVE).exp() - ONE
    return monthly.quantize(RATE_PRECISION)


# Aliases used by domain callers for clarity.
inflacion_anual_a_mensual_efectiva = annual_effective_to_monthly
tasa_ea_a_mensual = annual_effective_to_monthly
