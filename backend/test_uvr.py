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

baseline_banco = calc.calcular_total_por_pagar_simple_actual(datos.valor_cuota_actual, datos.cuotas_pendientes, datos.sistema_amortizacion, Decimal('0.05'))
print(f'ESTADO ACTUAL - Plazo Restante: {datos.cuotas_pendientes} meses')
print(f'Costo Total Base (Banco Hoy): ${baseline_banco:,.2f}')
print('='*60)

for idx, p in enumerate(proyecciones):
    print(f'OPCION {idx + 1} - Abono adicional: ${p.abono_adicional:,.2f}')
    print(f'Nueva Cuota: ${p.nuevo_valor_cuota:,.2f}')
    print(f'Nuevo Plazo: {p.cuotas_nuevas} meses (Ahorras {p.cuotas_reducidas} meses o {p.tiempo_ahorrado})')
    print(f'Nuevo Costo Total Proyectado Banco: ${p.costo_total_proyectado_banco:,.2f}')
    print(f'Costo Cliente Acumulado (Amortizado real): ${p.costo_total_proyectado:,.2f}')
    print(f'Ahorro en Intereses: ${p.valor_ahorrado_intereses:,.2f}')
    print(f'Veces Pagado (Frente al Saldo): {p.veces_pagado}')
    print('-'*60)
