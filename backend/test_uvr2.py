import sys
from decimal import Decimal
from app.services.calc_service import CalculadoraFinanciera, DatosCredito

calc = CalculadoraFinanciera()
datos = DatosCredito(
    saldo_capital=Decimal("66348797.99"),
    valor_cuota_actual=Decimal("400881.46"),
    cuotas_pendientes=351,
    tasa_interes_ea=Decimal("0.0590"),
    valor_prestado_inicial=Decimal("65139675.00"),
    beneficio_frech=Decimal("0"),
    tasa_seguro_vida=Decimal("16293.00") / Decimal("66348797.99"),
    valor_seguro_incendio_fijo=Decimal("16576.00"),
    sistema_amortizacion="UVR",
    valor_uvr_actual=Decimal("403.3679"),
    saldo_uvr=Decimal("165385.1262")
)
abonos = [Decimal("107032"), Decimal("122032"), Decimal("142032")]
proyecciones = calc.generar_proyecciones_multiple(datos, abonos)

# Replace simple actual computation
res_actual = calc.generar_tabla_amortizacion(
    saldo_inicial=datos.saldo_capital,
    tasa_mensual=calc.tasa_ea_a_mensual(datos.tasa_interes_ea),
    cuota_fija=datos.valor_cuota_actual,
    tasa_seguro_vida=datos.tasa_seguro_vida,
    valor_seguro_incendio_fijo=datos.valor_seguro_incendio_fijo,
    sistema_amortizacion=datos.sistema_amortizacion,
    valor_uvr_actual=datos.valor_uvr_actual,
    ipc_anual_proyectado=datos.ipc_anual_proyectado,
)
baseline_banco = res_actual.total_pagado

print(f'ESTADO ACTUAL - Plazo Restante: {datos.cuotas_pendientes} meses')
print(f'Costo Total Base (Banco Hoy): ')
print('='*60)

for idx, p in enumerate(proyecciones):
    print(f'OPCION {idx + 1} - Abono adicional: ')
    print(f'Nueva Cuota: ')
    print(f'Nuevo Plazo: {p.cuotas_nuevas} meses (Ahorras {p.cuotas_reducidas} meses o {p.tiempo_ahorrado})')
    print(f'Nuevo Costo Total Proyectado Banco: ')
    print(f'Costo Cliente Acumulado (Amortizado real): ')
    print(f'Ahorro en Intereses: ')
    print(f'Veces Pagado (Frente al Saldo): {p.veces_pagado}')
    print('-'*60)
