# Indicadores Financieros - Flujo de Datos Oficiales

## Objetivo
Servicio robusto para UVR, IPC, DTF e IBR con fuentes oficiales, sin estimaciones manuales.

## Arquitectura (Strategy Pattern)
1. **BanRepFilesProvider (primario)**
   - `inddiarios_new.xls` / `inddiarios_3s_new.xls` (DTF, IPC y otras series)
   - `IBR.xlsx` (IBR overnight)
   - `datos_estadisticos_uvr.pdf` (UVR diario oficial)
2. **BanRepSeriesProvider (secundario)**
   - `https://suameca.banrep.gov.co/estadisticas-economicas/api/series/{serie}`
   - Reintentos con backoff (`0.5s`, `1s`, `2s`) y validación estricta de respuesta
3. **CacheProvider**
   - Cache fresh por indicador y fecha
   - Cache stale como fallback de continuidad

## Manejo de errores y estabilidad
- Validación obligatoria de proveedor:
  - `status_code == 200`
  - body no vacío
  - rechazo explícito de HTML en endpoints JSON
  - parseo JSON seguro
- Circuit breaker por `provider + indicador` para evitar tormenta de requests.
- Si no hay dato fresh:
  - se retorna `CACHE_STALE` si existe
  - si no existe, se retorna error controlado **503** con mensaje de proveedor oficial no disponible.

## TTL de cache
- UVR: 12h
- DTF: 12h
- IBR: 12h
- IPC: 24h
- Histórico UVR: 12h
- Consolidados: 12h

## Respuesta API
Cada endpoint de indicadores expone:
- `valor`
- `fecha`
- `fuente`
- `fecha_actualizacion`

## Endpoints impactados
- `/api/v1/indicadores/uvr`
- `/api/v1/indicadores/ipc`
- `/api/v1/indicadores/dtf`
- `/api/v1/indicadores/ibr`
- `/api/v1/indicadores/consolidados`
- `/api/v1/indicadores/uvr/historico`
