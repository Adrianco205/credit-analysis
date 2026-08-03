import asyncio
from decimal import Decimal
import sys
sys.path.append("d:\\Perfinanzas\\credit-analysis")
from backend.app.services.uvr_projection_engine import calcular_ahorro_intereses_inflado_v1, compare_uvr_scenarios, UvrProjectionInput

data = UvrProjectionInput(
    saldo_inicial=Decimal("66348798"),
    cuota_actual=Decimal("400881"),
    tasa_efectiva_anual=Decimal("0.0525"),
    uvr_actual=Decimal("364.5"),
    inflacion_anual_estimada=Decimal("0.04"),
    seguro_mensual=Decimal("32869"),
    valor_seguro_incendio_fijo=Decimal("0"),
    cargos_no_amortizables_mensuales=Decimal("0"),
    abono_adicional=Decimal("157032")
)

res = calcular_ahorro_intereses_inflado_v1(data, Decimal("157032"))
print("Ahorro Option 1:", res)

res2 = calcular_ahorro_intereses_inflado_v1(data, Decimal("182032"))
print("Ahorro Option 2:", res2)

res3 = calcular_ahorro_intereses_inflado_v1(data, Decimal("202032"))
print("Ahorro Option 3:", res3)
