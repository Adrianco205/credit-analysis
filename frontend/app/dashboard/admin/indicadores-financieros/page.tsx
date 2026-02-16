'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BanknoteArrowUp, BarChart3, RefreshCw } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import type {
  ConversionUVRResponse,
  DTFResponse,
  HistoricoUVRResponse,
  IPCResponse,
  IndicadoresConsolidadosResponse,
  ProyeccionUVRResponse,
  UVRResponse,
  UserProfile,
} from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

const pesosFormatter = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
});

const decimalFormatter = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

function formatCurrency(value?: number | null) {
  if (value === undefined || value === null) return 'N/A';
  return pesosFormatter.format(value);
}

function formatPercent(value?: number | null) {
  if (value === undefined || value === null) return 'N/A';
  return `${decimalFormatter.format(value)}%`;
}

function formatDecimal(value?: number | null) {
  if (value === undefined || value === null) return 'N/A';
  return decimalFormatter.format(value);
}

function toIsoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

const INDICADORES_CACHE_TTL_MS = 60_000;

type IndicadoresMemoryCache = {
  timestamp: number;
  uvr: UVRResponse | null;
  ipc: IPCResponse | null;
  dtf: DTFResponse | null;
  consolidados: IndicadoresConsolidadosResponse | null;
  historico: HistoricoUVRResponse | null;
};

let indicadoresMemoryCache: IndicadoresMemoryCache | null = null;

export default function AdminIndicadoresFinancierosPage() {
  const router = useRouter();

  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isRoleLoading, setIsRoleLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [uvr, setUvr] = useState<UVRResponse | null>(null);
  const [ipc, setIpc] = useState<IPCResponse | null>(null);
  const [dtf, setDtf] = useState<DTFResponse | null>(null);
  const [consolidados, setConsolidados] = useState<IndicadoresConsolidadosResponse | null>(null);
  const [historico, setHistorico] = useState<HistoricoUVRResponse | null>(null);

  const [error, setError] = useState('');

  const [uvrMonto, setUvrMonto] = useState('1000');
  const [conversion, setConversion] = useState<ConversionUVRResponse | null>(null);
  const [conversionError, setConversionError] = useState('');
  const [converting, setConverting] = useState(false);

  const [projectionMonths, setProjectionMonths] = useState('12');
  const [projectionInflation, setProjectionInflation] = useState('0.06');
  const [projection, setProjection] = useState<ProyeccionUVRResponse | null>(null);
  const [projectionError, setProjectionError] = useState('');
  const [projecting, setProjecting] = useState(false);

  const hasLoadedIndicadoresRef = useRef(false);
  const isLoadingIndicadoresRef = useRef(false);

  const withTimeout = useCallback(<T,>(promise: Promise<T>, timeoutMs = 12000): Promise<T> => {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        setTimeout(() => reject(new Error('timeout')), timeoutMs);
      }),
    ]);
  }, []);

  const loadIndicadores = useCallback(async (forceRefresh = false) => {
    if (isLoadingIndicadoresRef.current) {
      return;
    }

    if (!forceRefresh && indicadoresMemoryCache) {
      const cacheAge = Date.now() - indicadoresMemoryCache.timestamp;
      if (cacheAge <= INDICADORES_CACHE_TTL_MS) {
        setUvr(indicadoresMemoryCache.uvr);
        setIpc(indicadoresMemoryCache.ipc);
        setDtf(indicadoresMemoryCache.dtf);
        setConsolidados(indicadoresMemoryCache.consolidados);
        setHistorico(indicadoresMemoryCache.historico);
        setLoading(false);
        setRefreshing(false);
        setError('');
        return;
      }
    }

    isLoadingIndicadoresRef.current = true;
    const hasAnyData = Boolean(
      uvr || ipc || dtf || consolidados || (historico && historico.datos && historico.datos.length > 0)
    );
    if (!hasAnyData) {
      setLoading(true);
    }
    setRefreshing(true);
    setError('');

    try {
      const today = new Date();
      const from = new Date();
      from.setDate(today.getDate() - 29);

      const [uvrResult, ipcResult, consolidadoResult, historicoResult] = await Promise.allSettled([
        withTimeout(apiClient.getIndicadorUVR()),
        withTimeout(apiClient.getIndicadorIPC()),
        withTimeout(apiClient.getIndicadoresConsolidados()),
        withTimeout(apiClient.getHistoricoUVR(toIsoDate(from), toIsoDate(today))),
      ]);

      if (uvrResult.status === 'fulfilled') {
        setUvr(uvrResult.value);
      }

      if (ipcResult.status === 'fulfilled') {
        setIpc(ipcResult.value);
      }

      let nextDtf: DTFResponse | null = dtf;

      if (consolidadoResult.status === 'fulfilled') {
        const consolidadoData = consolidadoResult.value;
        setConsolidados(consolidadoData);

        if (consolidadoData.dtf !== undefined && consolidadoData.dtf !== null) {
          nextDtf = {
            fecha: consolidadoData.fecha,
            valor: consolidadoData.dtf,
            fuente: consolidadoData.fuente || 'OFICIAL',
          };
          setDtf(nextDtf);
        }
      }

      if (historicoResult.status === 'fulfilled') {
        setHistorico(historicoResult.value);
      }

      const hasAtLeastOneSuccess =
        uvrResult.status === 'fulfilled' ||
        ipcResult.status === 'fulfilled' ||
        consolidadoResult.status === 'fulfilled' ||
        historicoResult.status === 'fulfilled';

      if (!hasAtLeastOneSuccess) {
        setError('No se pudo obtener el indicador en este momento');
      } else {
        const hasFailures =
          uvrResult.status === 'rejected' ||
          ipcResult.status === 'rejected' ||
          consolidadoResult.status === 'rejected' ||
          historicoResult.status === 'rejected';

        if (hasFailures) {
          setError('Algunos indicadores tardaron más de lo esperado; se muestran los datos disponibles.');
        }

        indicadoresMemoryCache = {
          timestamp: Date.now(),
          uvr: uvrResult.status === 'fulfilled' ? uvrResult.value : uvr,
          ipc: ipcResult.status === 'fulfilled' ? ipcResult.value : ipc,
          dtf: nextDtf,
          consolidados: consolidadoResult.status === 'fulfilled' ? consolidadoResult.value : consolidados,
          historico: historicoResult.status === 'fulfilled' ? historicoResult.value : historico,
        };
      }
    } finally {
      isLoadingIndicadoresRef.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, [consolidados, dtf, historico, ipc, uvr, withTimeout]);

  useEffect(() => {
    const validateRole = async () => {
      try {
        const user = await apiClient.getProfile();
        setCurrentUser(user);
        if (user.rol !== 'ADMIN') {
          router.replace('/dashboard');
          return;
        }

        if (!hasLoadedIndicadoresRef.current) {
          hasLoadedIndicadoresRef.current = true;
          await loadIndicadores();
        }
      } catch {
        router.replace('/auth/login');
        return;
      } finally {
        setIsRoleLoading(false);
      }
    };

    validateRole();
  }, [router, loadIndicadores]);

  const chartData = useMemo(() => {
    const raw = historico?.datos || [];
    const series = raw.slice(-12);
    const max = Math.max(...series.map((item) => Number(item.valor || 0)), 1);
    return series.map((item) => ({
      fecha: item.fecha,
      valor: Number(item.valor || 0),
      height: Math.max(8, Math.round((Number(item.valor || 0) / max) * 100)),
    }));
  }, [historico]);

  const handleConvert = async (event: React.FormEvent) => {
    event.preventDefault();
    setConversionError('');
    setConverting(true);
    setConversion(null);

    try {
      const monto = Number(uvrMonto);
      if (!monto || monto <= 0) {
        setConversionError('Ingresa una cantidad UVR válida.');
        return;
      }

      const result = await apiClient.convertirUVR({
        monto,
        direccion: 'uvr_a_pesos',
      });
      setConversion(result);
    } catch {
      setConversionError('No se pudo obtener el indicador en este momento');
    } finally {
      setConverting(false);
    }
  };

  const handleProject = async (event: React.FormEvent) => {
    event.preventDefault();
    setProjectionError('');
    setProjecting(true);
    setProjection(null);

    try {
      const meses = Number(projectionMonths);
      const inflacion = Number(projectionInflation);

      if (!meses || meses < 1 || meses > 360) {
        setProjectionError('Meses debe estar entre 1 y 360.');
        return;
      }
      if (!inflacion || inflacion <= 0) {
        setProjectionError('La inflación anual debe ser mayor que 0.');
        return;
      }

      const result = await apiClient.proyectarUVR({
        meses,
        inflacion_anual: inflacion,
      });
      setProjection(result);
    } catch {
      setProjectionError('No se pudo obtener el indicador en este momento');
    } finally {
      setProjecting(false);
    }
  };

  if (isRoleLoading || loading) {
    return (
      <div className="flex items-center justify-center h-[55vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]" />
      </div>
    );
  }

  if (currentUser?.rol !== 'ADMIN') {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Indicadores Financieros</h1>
          <p className="text-sm text-gray-600">Módulo de consulta en tiempo real para UVR, IPC, DTF e indicadores consolidados.</p>
        </div>
        <Button variant="outline" leftIcon={<RefreshCw size={16} />} onClick={() => loadIndicadores(true)} isLoading={refreshing}>
          Actualizar datos
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard title="UVR actual" value={uvr ? formatDecimal(uvr.valor) : 'N/A'} subtitle={uvr ? `Fecha: ${uvr.fecha}` : undefined} />
        <MetricCard title="IPC anual" value={ipc ? formatPercent(ipc.variacion_anual) : 'N/A'} subtitle={ipc ? `Mensual: ${formatPercent(ipc.variacion_mensual)}` : undefined} />
        <MetricCard title="DTF" value={dtf ? formatPercent(dtf.valor) : 'N/A'} subtitle={dtf ? `Fecha: ${dtf.fecha}` : undefined} />
        <MetricCard title="Consolidados" value={consolidados ? `IBR: ${formatPercent(consolidados.ibr_overnight)}` : 'N/A'} subtitle={consolidados ? `UVR: ${formatDecimal(consolidados.uvr || null)}` : undefined} />
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <BarChart3 size={18} className="text-[var(--verde-hoja)]" />
            Evolución UVR (últimos 12 puntos)
          </h2>
        </CardHeader>
        {chartData.length === 0 ? (
          <p className="text-sm text-gray-500 px-4 pb-4">No se pudo obtener el indicador en este momento</p>
        ) : (
          <div className="px-4 pb-4">
            <div className="h-44 rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="h-full flex items-end gap-2">
                {chartData.map((item) => (
                  <div key={item.fecha} className="flex-1 flex flex-col items-center justify-end gap-2">
                    <div className="w-full rounded-t-md bg-[var(--verde-hoja)]" style={{ height: `${item.height}%` }} />
                    <span className="text-[10px] text-gray-500">{item.fecha.slice(5)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <BanknoteArrowUp size={18} className="text-[var(--verde-hoja)]" />
              Convertir UVR → Pesos
            </h2>
          </CardHeader>

          <form onSubmit={handleConvert} className="space-y-4">
            <Input
              label="Cantidad UVR"
              type="number"
              value={uvrMonto}
              onChange={(event) => setUvrMonto(event.target.value)}
              min={0.0001}
              step={0.0001}
            />
            <Button type="submit" isLoading={converting}>Convertir</Button>

            {conversionError && (
              <p className="text-sm text-red-600">{conversionError}</p>
            )}

            {conversion && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-900">
                <p><strong className="text-gray-700">UVR usado:</strong> <span className="font-semibold text-gray-900">{formatDecimal(conversion.valor_uvr_usado)}</span></p>
                <p><strong className="text-gray-700">Resultado:</strong> <span className="font-semibold text-gray-900">{formatCurrency(conversion.monto_convertido)}</span></p>
              </div>
            )}
          </form>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800">Proyectar UVR</h2>
          </CardHeader>

          <form onSubmit={handleProject} className="space-y-4">
            <Input
              label="Meses a proyectar"
              type="number"
              value={projectionMonths}
              onChange={(event) => setProjectionMonths(event.target.value)}
              min={1}
              max={360}
            />
            <Input
              label="Inflación anual esperada (decimal)"
              type="number"
              value={projectionInflation}
              onChange={(event) => setProjectionInflation(event.target.value)}
              min={0.0001}
              step={0.0001}
            />
            <Button type="submit" isLoading={projecting}>Proyectar</Button>

            {projectionError && (
              <p className="text-sm text-red-600">{projectionError}</p>
            )}

            {projection && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-900 space-y-1">
                <p><strong className="text-gray-700">UVR inicial:</strong> <span className="font-semibold text-gray-900">{formatDecimal(projection.uvr_inicial)}</span></p>
                <p><strong className="text-gray-700">UVR proyectado:</strong> <span className="font-semibold text-gray-900">{formatDecimal(projection.uvr_proyectado)}</span></p>
                <p><strong className="text-gray-700">Incremento absoluto:</strong> <span className="font-semibold text-gray-900">{formatDecimal(projection.incremento_absoluto)}</span></p>
                <p><strong className="text-gray-700">Incremento porcentual:</strong> <span className="font-semibold text-gray-900">{formatPercent(projection.incremento_porcentual)}</span></p>
              </div>
            )}
          </form>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <Card className="border border-gray-200">
      <div className="p-4">
        <p className="text-sm text-gray-500">{title}</p>
        <p className="mt-1 text-lg font-semibold text-gray-900">{value}</p>
        {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
      </div>
    </Card>
  );
}
