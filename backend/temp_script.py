
from decimal import Decimal
def test(data, uvr_mes):
    cuota_uvr_es_solo_deuda = data.cuota_uvr_actual is not None and data.cuota_uvr_actual > 0
    if not cuota_uvr_es_solo_deuda and data.uvr_actual and data.uvr_actual > 0:
        print('Case 1')
        cuota_uvr_calculada = data.cuota_actual / data.uvr_actual
        cuota_total_mes = cuota_uvr_calculada * uvr_mes
    return cuota_total_mes
