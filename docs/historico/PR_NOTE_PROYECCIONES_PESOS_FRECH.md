# PR Note — Ajuste de Proyecciones PESOS + FRECH

## Resumen
Se ajustó la lógica de proyecciones para alinear el comportamiento con el criterio de referencia del PDF en escenarios de crédito en PESOS con beneficio FRECH.

## Cambios principales
- Se usa como base de proyección la cuota pagada por el cliente (sin doble conteo de FRECH).
- Se evita sumar implícitamente el FRECH dos veces en métricas de resumen.
- Se ajusta el indicador `veces_pagado` para calcularse como:
  - `total_por_pagar / saldo_capital`
- Se fortalece la construcción de baseline para seleccionar fuente de cuota con trazabilidad (`cuota_base_source`), incluyendo heurística para derivar cuota cliente desde cuota total cuando aplica.

## Archivos impactados
- `app/services/analysis_service.py`
- `app/services/calc_service.py`
- `app/tests/test_calc_service.py`
- `app/tests/test_analysis_service.py`

## Validación
Se ejecutaron pruebas focalizadas:
- `pytest app/tests/test_calc_service.py app/tests/test_analysis_service.py -q`
- Resultado: **67 passed**

## Nota de evolución
Si en el futuro se requieren reglas específicas por banco sobre el tratamiento de FRECH, conviene externalizar la estrategia de composición de cuota (cliente vs total) a una política configurable por entidad financiera.
