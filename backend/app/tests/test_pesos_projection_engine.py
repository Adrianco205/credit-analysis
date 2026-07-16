from decimal import Decimal
import pytest
from app.services.pesos_projection_engine import PesosProjectionInfeasibleError, PesosProjectionInput, simulate_pesos


def test_pesos_frech_flows_and_expiry_are_separated():
    result = simulate_pesos(PesosProjectionInput(
        principal_balance=Decimal("30586456.09"), annual_rate=Decimal("0.0621"),
        contractual_debt_installment=Decimal("388796.75"), insurance_monthly=Decimal("58145"),
        non_amortizable_charges=Decimal("0"), frech_monthly=Decimal("125036.62"),
        frech_remaining_months=12, remaining_term=175, extra_payment=Decimal("200000"),
    ))
    assert result.terminated
    assert result.total_bank_flow == result.total_client_payment + result.total_frech
    assert result.total_insurance > 0 and result.total_interest > 0


def test_pesos_frech_without_term_is_blocked():
    with pytest.raises(PesosProjectionInfeasibleError):
        simulate_pesos(PesosProjectionInput(Decimal("10000000"), Decimal("0.1"), Decimal("200000"), Decimal("0"), Decimal("0"), Decimal("10000"), None, 100))
