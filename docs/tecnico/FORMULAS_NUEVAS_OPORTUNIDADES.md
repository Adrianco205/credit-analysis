# Formulas y funciones - Tabla "Nuevas Oportunidades"

Este documento explica, de punta a punta, como se calcula la tabla de "Nuevas Oportunidades" en PerFinanzas: funciones involucradas, formulas financieras y mapeo exacto hacia cada fila que ve el usuario/admin.

## 1. Flujo general de calculo

1. Se recibe el `analisis_id` y las opciones de abono adicional.
2. Se construye el escenario base (credito actual, sin abono extra).
3. Se simula cada opcion de abono:
   - Ruta estandar: motor de amortizacion en `calc_service.py`.
   - Ruta UVR V2 (si aplica): motor UVR en `uvr_projection_engine.py`.
4. Se persisten los resultados en propuestas.
5. La API normaliza campos de compatibilidad.
6. Frontend renderiza la tabla "Nuevas Oportunidades" usando esos campos.

## 2. Orquestacion principal (backend)

### `backend/app/services/analysis_service.py`

- `generate_projections(...)`
  - Entrada principal para generar proyecciones de un analisis.
  - Llama a `_calculate_baseline(...)`.
  - Itera opciones y llama `_calculate_projection_for_option(...)`.

- `_calculate_baseline(...)`
  - Define la cuota base visible del cliente.
  - Construye `DatosCredito` base.
  - Calcula escenario actual con `calcular_proyeccion(..., abono_extra=0)`.
  - Calcula:
    - `total_por_pagar_simple` actual.
    - `costo_total_proyectado` actual.
    - `costo_total_proyectado_banco` actual.
    - `veces_pagado_actual`.

- `_calculate_projection_for_option(...)`
  - Para cada opcion decide motor:
    - Si es UVR y flag activo: `_calculate_projection_for_option_uvr_engine(...)`.
    - Si no: `calc.calcular_proyeccion(...)`.
  - Retorna todos los campos que consume la tabla.

- `_calculate_projection_for_option_uvr_engine(...)`
  - Arma `UvrProjectionInput`.
  - Llama `compare_uvr_scenarios(...)`.
  - Calcula campos finales para tabla (cuotas nuevas, ahorro intereses, costos, honorarios, ingreso minimo).

## 3. Motor estandar de proyecciones (PESOS/CAPITAL y fallback)

### `backend/app/services/calc_service.py`

## 3.1 Conversion de tasa

- `tasa_ea_a_mensual(tasa_ea)`
- Formula:

```text
rm = (1 + EA)^(1/12) - 1
```

Donde `EA` puede venir en porcentaje (ej. 4.71) o fraccion (ej. 0.0471), y se normaliza antes de calcular.

## 3.2 Cuota fija (sistema frances)

- `calcular_cuota_fija(capital, tasa_mensual, num_cuotas)`
- Formula:

```text
C = P * [r(1+r)^n] / [(1+r)^n - 1]
```

- `P`: capital/saldo.
- `r`: tasa mensual.
- `n`: numero de cuotas.

## 3.3 Tabla de amortizacion mensual

- `generar_tabla_amortizacion(...)`

Por cada mes calcula:

```text
interes_mes = saldo * tasa_mensual
abono_capital_base = cuota_fija - seguros - cargos_no_amortizables - interes_mes
abono_capital_base = max(abono_capital_base, 0)
```

Ajuste de ultima cuota:

```text
si saldo <= abono_capital_base + abono_extra:
    abono_capital_real = saldo
    abono_extra_real = 0
si no:
    abono_capital_real = abono_capital_base
    abono_extra_real = abono_extra

saldo_final = saldo - abono_capital_real - abono_extra_real
```

Acumula:

- `total_pagado`
- `total_intereses`
- `total_costos_no_amortizables`
- `total_capital`

## 3.4 Proyeccion completa por opcion

- `calcular_proyeccion(datos, abono_extra, ...)`

Simula dos escenarios:

1. Actual sin abono.
2. Con abono extra.

Con eso calcula:

- `cuotas_nuevas`
- `cuotas_reducidas`
- `tiempo_restante`
- `tiempo_ahorrado`
- `valor_ahorrado_intereses`

### Formula de ahorro de intereses (motor estandar)

```text
valor_ahorrado_intereses = intereses_escenario_actual - intereses_escenario_con_abono
```

### Total simple (estimado comercial)

- `calcular_total_por_pagar_simple_actual(cuota_actual, cuotas_pendientes)`

```text
total_por_pagar_simple_actual = cuota_actual * cuotas_pendientes
```

- `calcular_total_por_pagar_simple_opcion(nueva_cuota, cuotas_nuevas)`

```text
total_por_pagar_simple_opcion = nueva_cuota * cuotas_nuevas
```

### Costo proyectado real (cliente/banco)

- `calcular_flujo_frech(beneficio_frech_mensual, cuotas_proyectadas, frech_meses_restantes)`

```text
meses_subsidiados = min(cuotas_proyectadas, frech_meses_restantes)   # si existe dato
meses_subsidiados = min(cuotas_proyectadas, 84)                      # fallback actual

total_subsidio_frech_proyectado = beneficio_frech_mensual * meses_subsidiados
```

- `calcular_costo_total_proyectado(total_flujo_cliente, beneficio_frech_mensual, cuotas_proyectadas, frech_meses_restantes)`

```text
costo_total_proyectado = total_flujo_cliente
costo_total_proyectado_banco = costo_total_proyectado + total_subsidio_frech_proyectado
```

### Indicador comercial "No. Veces Pagado"

```text
veces_pagado = costo_total_proyectado / saldo_capital    # si saldo_capital > 0
```

### Honorarios e ingreso minimo

- `calcular_honorarios(ahorro_total)`

```text
honorarios = max(ahorro_total * 0.06, TARIFA_MINIMA_HONORARIOS)
```

- `calcular_honorarios_con_iva(honorarios)`

```text
honorarios_con_iva = honorarios * 1.19
```

- `calcular_ingreso_minimo(cuota_mensual)`

```text
ingreso_minimo_requerido = cuota_mensual / 0.30
```

## 4. Motor UVR V2 (cuando el flag esta activo)

### `backend/app/services/uvr_projection_engine.py`

## 4.1 Conversiones

- `tasa_ea_a_mensual(...)`

```text
rm = (1 + EA)^(1/12) - 1
```

- `inflacion_anual_a_mensual_lineal(...)`

```text
inflacion_mensual = inflacion_anual / 12
```

## 4.2 Simulacion mensual UVR

- `simulate_uvr_scenario(data, abono_adicional_override=None)`

Reglas clave:

1. La UVR crece cada mes por inflacion estimada.
2. Interes mensual sobre saldo indexado en pesos.
3. Pago aplicable a deuda incluye subsidio FRECH.
4. Seguro suma al flujo del cliente, pero no amortiza capital.

Formulas relevantes:

```text
uvr_mes = uvr_mes * (1 + inflacion_mensual)
saldo_inicial_pesos = saldo_uvr * uvr_mes
interes_mes = saldo_inicial_pesos * tasa_mensual

pago_cliente_mes = cuota_actual + abono_adicional + seguro_mensual
pago_para_deuda = cuota_actual + abono_adicional + subsidio_frech
capital_mes = max(pago_para_deuda - interes_mes, 0)
```

## 4.3 Comparacion de escenarios UVR

- `compare_uvr_scenarios(data)`

Corre dos simulaciones:

1. Escenario original (`abono = 0`).
2. Escenario con abono.

Formula principal de ahorro UVR (metodologia correcta):

```text
ahorro_intereses_real = intereses_original - intereses_con_abono
```

Nota importante: en UVR V2 el ahorro principal se basa en diferencia de intereses, no en delta de total pagado.

## 5. Normalizacion de API (compatibilidad de campos)

### `backend/app/api/v1/admin.py`

- `derive_total_por_pagar_simple()`

### `backend/app/api/v1/analyses.py`

- `normalize_totals_semantics()`

Reglas aplicadas:

```text
si total_por_pagar_simple es null:
    total_por_pagar_simple = nuevo_valor_cuota * cuotas_nuevas

si costo_total_proyectado_banco es null:
    costo_total_proyectado_banco = costo_total_proyectado
```

Esto evita romper tablas/reportes cuando hay datos historicos o payloads incompletos.

## 6. Mapeo exacto a la tabla "Nuevas Oportunidades"

### `frontend/components/dashboard/admin/AnalysisProjectionDetail.tsx`

- `InstitutionalOpportunitiesTable(...)` renderiza las filas visibles.
- `buildLegacyProposal(...)` ajusta compatibilidad de respuestas legacy.
- `monthsToTime(...)` transforma meses a anios/meses para mostrar.

Filas y origen de datos:

1. `Saldo Credito`
   - Base: `proposal.limites_actuales.saldo_credito`

2. `Cuotas Pendientes`
   - Base: `proposal.limites_actuales.cuotas_pendientes`
   - Opcion: `opcion.cuotas_nuevas`

3. `Tiempo Pendiente`
   - Base: `proposal.limites_actuales.tiempo_pendiente`
   - Opcion: `opcion.tiempo_restante`

4. `Abono adicional a cuota`
   - Base: `proposal.limites_actuales.abono_adicional_cuota`
   - Opcion: `opcion.abono_adicional_mensual`

5. `Cuota actual a cancelar aprox.`
   - Base: `proposal.limites_actuales.valor_cuota`
   - Opcion: `opcion.nuevo_valor_cuota`

6. `Costo total proyectado al banco`
   - Base: `limites_actuales.costo_total_proyectado_banco` (fallback a `costo_total_proyectado`)
   - Opcion: `opcion.costo_total_proyectado_banco` (fallback a `opcion.costo_total_proyectado`)

7. `No. Veces Pagado`
   - Base: `proposal.limites_actuales.veces_pagado`
   - Opcion: `opcion.veces_pagado`

8. `Valor Ahorrado en Intereses`
   - Opcion: `opcion.valor_ahorrado_intereses`

9. `Cuotas Reducidas`
   - Opcion: `opcion.cuotas_reducidas`

10. `Tiempo Ahorrado`
    - Opcion: `opcion.tiempo_ahorrado`

11. `Valor Honorarios`
    - Opcion: `opcion.honorarios_con_iva`

12. `Ingresos Minimos`
    - Opcion: `opcion.ingreso_minimo_requerido`

## 7. Resumen corto de semantica de costos

- `total_por_pagar_simple`: estimacion simple (`cuota x cuotas`).
- `costo_total_proyectado`: costo real del cliente (sumatoria mensual de la amortizacion).
- `costo_total_proyectado_banco`: costo cliente + subsidio FRECH proyectado.

Esa separacion es la base de la tabla y del PDF para mantener consistencia financiera y comercial.

## 8. Operaciones exactas (paso a paso por funcion)

Esta seccion baja a nivel operativo: que variables se crean, que decision toma cada `if`, y como se arma cada salida.

### 8.1 `_calculate_baseline(...)` en `analysis_service.py`

```text
1) frech = analisis.beneficio_frech_mensual or 0

2) cuota_cliente se elige por prioridad:
   cuota_cliente = valor_cuota_con_subsidio
                  o valor_cuota_con_seguros
                  o valor_cuota_sin_seguros

3) Si no hay cuota con subsidio pero hay FRECH y cuota con seguros:
   posible_cliente = valor_cuota_con_seguros - frech
   si posible_cliente > 0 y < valor_cuota_con_seguros:
      comparar contra total_por_pagar del analisis (si existe)
      y usar posible_cliente cuando ajusta mejor.

4) Construir DatosCredito visible:
   saldo_capital = analisis.saldo_capital_pesos
   valor_cuota_actual = cuota_cliente
   cuotas_pendientes = analisis.cuotas_pendientes
   tasa_interes_ea = analisis.tasa_interes_cobrada_ea
   beneficio_frech = frech
   seguros_mensual = analisis.seguros_total_mensual or 0
   cargos_no_amortizables_mensuales = _estimar_cargos_no_amortizables_mensuales(...)

4.1) Resolver meses FRECH restantes:
   - si `frech_meses_restantes` viene en el analisis, usarlo
   - si no viene y hay `cuotas_pagadas`, inferir: `max(0, 84 - cuotas_pagadas)`
   - si no se puede inferir, dejar `None` y la calculadora aplica fallback conservador

5) datos_proyeccion = copia de datos_visible

6) proyeccion_actual = calcular_proyeccion(datos_proyeccion, abono_extra=0)

7) Si sistema es PESOS y cuotas_nuevas > cuotas_pendientes:
   calcular cuota objetivo minima para cerrar en cuotas_pendientes,
   recalcular proyeccion y hacer ajuste fino (+50) hasta converger.

8) total_actual_simple = cuota_visible * cuotas_pendientes

9) veces_pagado_actual:
   si saldo_capital > 0:
      veces_pagado_actual = costo_total_proyectado / saldo_capital
   si no:
      veces_pagado_actual = 0

10) retorna diccionario baseline con:
    total_simple, costo_proyectado_cliente, costo_proyectado_banco,
    subsidio_frech, cuota_visible y datos base.
```

### 8.2 `_calculate_projection_for_option(...)` ruta estandar

```text
1) Si sistema UVR y flag V2 activo:
   intentar _calculate_projection_for_option_uvr_engine(...)
   si retorna valor -> usarlo
   si retorna None -> fallback a motor estandar

2) datos = baseline["datos_visible"]

3) proyeccion = calc.calcular_proyeccion(datos, abono_extra=opcion.abono_adicional_mensual)

4) mapear salida:
   cuotas_nuevas = proyeccion.cuotas_nuevas
   nuevo_valor_cuota = proyeccion.nuevo_valor_cuota
   total_por_pagar_simple = proyeccion.total_por_pagar_simple
   costo_total_proyectado = proyeccion.costo_total_proyectado
   costo_total_proyectado_banco = proyeccion.costo_total_proyectado_banco
   valor_ahorrado_intereses = proyeccion.valor_ahorrado_intereses
   veces_pagado = proyeccion.veces_pagado
   honorarios_con_iva = proyeccion.honorarios_con_iva
   ingreso_minimo_requerido = proyeccion.ingreso_minimo_requerido
```

### 8.3 `calcular_proyeccion(...)` en `calc_service.py`

```text
1) tasa_mensual = tasa_ea_a_mensual(datos.tasa_interes_ea)

2) resultado_actual = generar_tabla_amortizacion(..., abono_extra=0)
3) resultado_con_abono = generar_tabla_amortizacion(..., abono_extra=abono_extra)

4) costo_total_proyectado = resultado_con_abono.total_pagado

5) total_subsidio_frech_proyectado = calcular_flujo_frech(
      beneficio_frech_mensual=datos.beneficio_frech,
      cuotas_proyectadas=resultado_con_abono.cuotas_totales,
      frech_meses_restantes=datos.frech_meses_restantes
   )

6) costo_total_proyectado_banco =
      costo_total_proyectado + total_subsidio_frech_proyectado

7) cuotas_reducidas = max(0, datos.cuotas_pendientes - resultado_con_abono.cuotas_totales)

8) ahorro_intereses =
      resultado_actual.total_intereses - resultado_con_abono.total_intereses

9) nueva_cuota = datos.valor_cuota_actual + abono_extra

10) total_por_pagar_simple = nueva_cuota * resultado_con_abono.cuotas_totales

11) veces_pagado:
    si datos.saldo_capital > 0:
       veces_pagado = costo_total_proyectado / datos.saldo_capital
    si no:
       veces_pagado = 0

12) honorarios = max(ahorro_intereses * 0.06, tarifa_minima)
13) honorarios_con_iva = honorarios * 1.19
14) ingreso_minimo_requerido = nueva_cuota / 0.30

15) retornar ResultadoProyeccion con todos esos campos.
```

### 8.4 `_calculate_projection_for_option_uvr_engine(...)` (UVR V2)

```text
1) payload UVR:
   saldo_inicial = datos_visible.saldo_capital
   tasa_efectiva_anual = datos_visible.tasa_interes_ea
   plazo_meses = datos_visible.cuotas_pendientes
   cuota_actual = datos_visible.valor_cuota_actual
   abono_adicional = opcion.abono_adicional_mensual
   uvr_actual = valor_uvr_actual
   inflacion_anual_estimada = config
   subsidio_frech = datos_visible.beneficio_frech
   seguro_mensual = datos_visible.seguros_mensual

2) comparacion = compare_uvr_scenarios(payload)

3) cuotas_nuevas = comparacion.escenario_con_abono.meses_totales
4) nueva_cuota = cuota_actual + abono_adicional
5) total_simple = nueva_cuota * cuotas_nuevas

6) costo_total_proyectado = comparacion.escenario_con_abono.total_pagado_cliente

7) subsidio_frech_total = calcular_flujo_frech(..., cuotas_nuevas, ...)
8) costo_total_proyectado_banco = costo_total_proyectado + subsidio_frech_total

9) ahorro_intereses = comparacion.ahorro_intereses_real

10) veces_pagado = costo_total_proyectado / saldo_capital (si saldo > 0)
11) honorarios_con_iva e ingreso_minimo igual que en ruta estandar.
```

### 8.5 `simulate_uvr_scenario(...)` en `uvr_projection_engine.py`

```text
Inicializacion:
 - tasa_mensual = tasa_ea_a_mensual(tasa_efectiva_anual)
 - inflacion_mensual = inflacion_anual_a_mensual_lineal(inflacion_anual_estimada)
 - saldo_uvr = saldo_inicial / uvr_actual

Cada mes:
 1) uvr_mes = uvr_mes * (1 + inflacion_mensual)
 2) saldo_inicial_pesos = saldo_uvr * uvr_mes
 3) interes_mes = saldo_inicial_pesos * tasa_mensual
 4) pago_cliente_mes = cuota_actual + abono + seguro
 5) pago_para_deuda = cuota_actual + abono + subsidio_frech
 6) capital_mes = max(pago_para_deuda - interes_mes, 0)
 7) saldo_final_pesos = max(saldo_inicial_pesos - capital_mes, 0)
 8) capital_uvr = capital_mes / uvr_mes
 9) saldo_uvr = max(saldo_uvr - capital_uvr, 0)

Acumula por escenario:
 - total_intereses
 - total_pagado_cliente
 - total_pagado_banco
 - capital_total_amortizado
```

### 8.6 `compare_uvr_scenarios(...)` en `uvr_projection_engine.py`

```text
1) escenario_original = simulate_uvr_scenario(abono=0)
2) escenario_con_abono = simulate_uvr_scenario(abono=abono_adicional)

3) ahorro_intereses_real =
      escenario_original.intereses_totales - escenario_con_abono.intereses_totales

4) meses_reducidos =
      max(0, escenario_original.meses_totales - escenario_con_abono.meses_totales)
```

### 8.7 Normalizacion en API (cuando faltan campos)

`admin.py::derive_total_por_pagar_simple()` y `analyses.py::normalize_totals_semantics()` aplican:

```text
si total_por_pagar_simple es null y hay nuevo_valor_cuota y cuotas_nuevas:
    total_por_pagar_simple = nuevo_valor_cuota * cuotas_nuevas

si costo_total_proyectado es null:
    costo_total_proyectado = total_por_pagar_aprox

si total_por_pagar_aprox es null:
    total_por_pagar_aprox = total_por_pagar_simple

si costo_total_proyectado_banco es null:
    costo_total_proyectado_banco = costo_total_proyectado
```

### 8.8 Operaciones de compatibilidad legacy en frontend

En `AnalysisProjectionDetail.tsx::buildLegacyProposal(...)` se hacen estas operaciones para reconstruir datos antiguos:

```text
1) cuotaActual:
   - usar valor_cuota_con_subsidio si existe
   - si no, intentar valor_cuota_con_seguros - frech (si es valido)
   - si no, usar valor_cuota_con_seguros o valor_cuota_sin_seguros

2) totalPagarSimple:
   - usar total_por_pagar_simple si viene
   - si no: cuotaActual * cuotasPendientes

3) costoTotalProyectadoBanco:
   - usar costo_total_proyectado_banco
   - fallback: costo_total_proyectado

4) vecesPagado:
   - usar valor existente
   - fallback: costoTotalProyectado / saldoCredito (si saldo > 0)
```

Con esta capa, la tabla mantiene el mismo significado financiero incluso cuando llegan respuestas historicas.

