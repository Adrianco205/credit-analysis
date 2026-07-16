"""PESOS V2: French amortization with separately auditable cash flows."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal("0.01")
EPSILON = Decimal("0.01")


class PesosProjectionInfeasibleError(ValueError):
    pass


from app.services.financial_rates import annual_effective_to_monthly as ea_to_monthly


@dataclass(frozen=True)
class PesosProjectionInput:
    principal_balance: Decimal
    annual_rate: Decimal
    contractual_debt_installment: Decimal
    insurance_monthly: Decimal
    non_amortizable_charges: Decimal
    frech_monthly: Decimal
    frech_remaining_months: int | None
    remaining_term: int
    extra_payment: Decimal = Decimal("0")


@dataclass(frozen=True)
class PesosProjectionResult:
    months: int
    total_client_payment: Decimal
    total_bank_flow: Decimal
    total_interest: Decimal
    total_insurance: Decimal
    total_frech: Decimal
    principal_amortized: Decimal
    remaining_balance: Decimal
    terminated: bool


def simulate_pesos(data: PesosProjectionInput) -> PesosProjectionResult:
    if data.frech_monthly > 0 and data.frech_remaining_months is None:
        raise PesosProjectionInfeasibleError("La vigencia del FRECH no está confirmada; no se puede proyectar su flujo.")
    if data.principal_balance <= 0 or data.contractual_debt_installment <= 0 or data.remaining_term <= 0:
        raise PesosProjectionInfeasibleError("Faltan términos contractuales verificables.")
    rate = ea_to_monthly(data.annual_rate)
    if data.contractual_debt_installment + data.extra_payment <= data.principal_balance * rate:
        raise PesosProjectionInfeasibleError("La cuota de deuda no cubre el interés inicial.")

    balance = data.principal_balance
    client = bank = interest_total = insurance_total = frech_total = principal_total = Decimal("0")
    months = 0
    # Remaining term is a contractual reference, not an iteration result.
    for month in range(1, data.remaining_term + 1):
        interest = (balance * rate).quantize(MONEY, rounding=ROUND_HALF_UP)
        debt_payment = data.contractual_debt_installment + data.extra_payment
        principal = debt_payment - interest
        if principal <= 0:
            raise PesosProjectionInfeasibleError("La cuota dejó de cubrir intereses durante la proyección.")
        if principal > balance:
            principal = balance
            debt_payment = interest + principal
        frech = data.frech_monthly if month <= (data.frech_remaining_months or 0) else Decimal("0")
        monthly_client = debt_payment + data.insurance_monthly + data.non_amortizable_charges - frech
        if monthly_client < 0:
            raise PesosProjectionInfeasibleError("El FRECH excede el flujo contractual; requiere revisión manual.")
        balance = (balance - principal).quantize(MONEY, rounding=ROUND_HALF_UP)
        client += monthly_client
        bank += debt_payment + data.insurance_monthly + data.non_amortizable_charges
        interest_total += interest
        insurance_total += data.insurance_monthly + data.non_amortizable_charges
        frech_total += frech
        principal_total += principal
        months = month
        if balance <= EPSILON:
            balance = Decimal("0")
            break
    return PesosProjectionResult(months, client.quantize(MONEY), bank.quantize(MONEY), interest_total.quantize(MONEY), insurance_total.quantize(MONEY), frech_total.quantize(MONEY), principal_total.quantize(MONEY), balance, balance <= EPSILON)
