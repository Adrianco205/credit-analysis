'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { AlertTriangle, ArrowLeft, Calculator } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cleanDigitsInput, formatDigitsInput, formatMonetaryInput, parseMonetaryInput } from '@/lib/utils';
import type { AnalysisDetailResponse, UpdateManualFieldsRequest } from '@/types/api';

type RequiredFieldKey =
  | 'valor_prestado_inicial'
  | 'saldo_capital_pesos'
  | 'valor_cuota_con_seguros'
  | 'cuotas_pendientes'
  | 'tasa_interes_cobrada_ea';

const REQUIRED_FIELD_LABELS: Record<RequiredFieldKey, string> = {
  valor_prestado_inicial: 'Valor prestado inicial',
  saldo_capital_pesos: 'Saldo capital actual',
  valor_cuota_con_seguros: 'Cuota mensual actual',
  cuotas_pendientes: 'Cuotas pendientes',
  tasa_interes_cobrada_ea: 'Tasa de interés cobrada EA',
};

interface ManualFormState {
  valor_prestado_inicial: string;
  saldo_capital_pesos: string;
  valor_cuota_con_seguros: string;
  cuotas_pendientes: string;
  tasa_interes_cobrada_ea: string;
}

export default function AnalysisManualCalculatorPage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisDetailResponse | null>(null);
  const [form, setForm] = useState<ManualFormState>({
    valor_prestado_inicial: '',
    saldo_capital_pesos: '',
    valor_cuota_con_seguros: '',
    cuotas_pendientes: '',
    tasa_interes_cobrada_ea: '',
  });

  const missingFields = useMemo(() => {
    if (!analysis) return [] as RequiredFieldKey[];

    const fields: RequiredFieldKey[] = [];

    if (analysis.valor_prestado_inicial === null || analysis.valor_prestado_inicial === undefined) {
      fields.push('valor_prestado_inicial');
    }
    if (analysis.saldo_capital_pesos === null || analysis.saldo_capital_pesos === undefined) {
      fields.push('saldo_capital_pesos');
    }

    const hasAvailableQuota = [
      analysis.valor_cuota_con_subsidio,
      analysis.valor_cuota_con_seguros,
      analysis.valor_cuota_sin_seguros,
    ].some((value) => value !== null && value !== undefined);

    if (!hasAvailableQuota) {
      fields.push('valor_cuota_con_seguros');
    }

    if (analysis.cuotas_pendientes === null || analysis.cuotas_pendientes === undefined) {
      fields.push('cuotas_pendientes');
    }

    if (analysis.tasa_interes_cobrada_ea === null || analysis.tasa_interes_cobrada_ea === undefined) {
      fields.push('tasa_interes_cobrada_ea');
    }

    return fields;
  }, [analysis]);

  const loadAnalysisDetail = useCallback(async () => {
    try {
      setLoading(true);
      const detail = await apiClient.getAnalysisDetail(analysisId);
      setAnalysis(detail);
      setForm({
        valor_prestado_inicial: intToInput(detail.valor_prestado_inicial),
        saldo_capital_pesos: numberToInput(detail.saldo_capital_pesos),
        valor_cuota_con_seguros: numberToInput(
          detail.valor_cuota_con_seguros ?? detail.valor_cuota_con_subsidio ?? detail.valor_cuota_sin_seguros,
        ),
        cuotas_pendientes: intToInput(detail.cuotas_pendientes),
        tasa_interes_cobrada_ea: rateToInput(detail.tasa_interes_cobrada_ea),
      });
    } catch (err: unknown) {
      const parsed = err && typeof err === 'object' ? (err as { message?: string }) : null;
      setError(parsed?.message || 'No se pudo cargar el análisis para completar datos manuales.');
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    if (analysisId) {
      loadAnalysisDetail();
    }
  }, [analysisId, loadAnalysisDetail]);

  const updateField = (field: keyof ManualFormState, value: string) => {
    if (field === 'valor_prestado_inicial') {
      setForm((prev) => ({ ...prev, [field]: formatDigitsInput(value) }));
      return;
    }

    const moneyFields: Array<keyof ManualFormState> = [
      'saldo_capital_pesos',
      'valor_cuota_con_seguros',
    ];

    if (field === 'cuotas_pendientes') {
      setForm((prev) => ({ ...prev, [field]: formatDigitsInput(value) }));
      return;
    }

    if (moneyFields.includes(field)) {
      setForm((prev) => ({ ...prev, [field]: formatMonetaryInput(value) }));
      return;
    }

    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!analysis) return;

    const required = new Set(missingFields);
    const payload: UpdateManualFieldsRequest = {};

    const valorPrestado = parseInteger(form.valor_prestado_inicial);
    const saldoCapital = parseMonetaryInput(form.saldo_capital_pesos);
    const valorCuota = parseMonetaryInput(form.valor_cuota_con_seguros);
    const cuotasPendientes = parseInteger(form.cuotas_pendientes);
    const tasaEA = parseDecimal(form.tasa_interes_cobrada_ea);

    if (required.has('valor_prestado_inicial')) {
      if (valorPrestado === null || valorPrestado <= 0) {
        toast.error('Ingresa un valor prestado inicial válido');
        return;
      }
      payload.valor_prestado_inicial = valorPrestado;
    }

    if (required.has('saldo_capital_pesos')) {
      if (saldoCapital === null || saldoCapital <= 0) {
        toast.error('Ingresa un saldo capital válido');
        return;
      }
      payload.saldo_capital_pesos = saldoCapital;
    }

    if (required.has('valor_cuota_con_seguros')) {
      if (valorCuota === null || valorCuota <= 0) {
        toast.error('Ingresa una cuota mensual válida');
        return;
      }
      payload.valor_cuota_con_seguros = valorCuota;
    }

    if (required.has('cuotas_pendientes')) {
      if (cuotasPendientes === null || cuotasPendientes <= 0) {
        toast.error('Ingresa un número de cuotas pendientes válido');
        return;
      }
      payload.cuotas_pendientes = cuotasPendientes;
    }

    if (required.has('tasa_interes_cobrada_ea')) {
      if (tasaEA === null || tasaEA < 0) {
        toast.error('Ingresa una tasa EA válida');
        return;
      }
      payload.tasa_interes_cobrada_ea = tasaEA;
    }

    if (Object.keys(payload).length === 0) {
      toast.success('El análisis ya cuenta con los datos mínimos para proyectar.');
      router.push(`/dashboard/analysis/${analysisId}/summary`);
      return;
    }

    try {
      setSaving(true);
      const result = await apiClient.updateAnalysisManual(analysisId, payload);

      if (!result.success) {
        toast.error(result.message || 'No se pudieron guardar los datos manuales.');
        return;
      }

      if (result.requires_manual_input && result.campos_faltantes && result.campos_faltantes.length > 0) {
        const pendingLabels = result.campos_faltantes
          .map((field) => REQUIRED_FIELD_LABELS[field as RequiredFieldKey] || field)
          .join(', ');
        toast.error(`Aún faltan datos: ${pendingLabels}`);
        await loadAnalysisDetail();
        return;
      }

      toast.success('Datos manuales guardados. Ya puedes continuar con proyecciones.');
      router.push(`/dashboard/analysis/${analysisId}/summary`);
    } catch (err: unknown) {
      const parsed = err && typeof err === 'object' ? (err as { message?: string }) : null;
      toast.error(parsed?.message || 'Error al guardar los datos manuales.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto py-8">
        <Card className="border-red-200 bg-red-50">
          <div className="flex items-center gap-4 p-6">
            <AlertTriangle className="text-red-500" size={32} />
            <div>
              <h2 className="text-lg font-semibold text-red-700">Error al cargar datos manuales</h2>
              <p className="text-red-600">{error}</p>
            </div>
          </div>
          <div className="px-6 pb-6">
            <Link href="/dashboard/historial">
              <Button variant="secondary" leftIcon={<ArrowLeft size={16} />}>
                Volver al historial
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/dashboard/historial">
          <Button variant="ghost" leftIcon={<ArrowLeft size={16} />}>
            Volver al historial
          </Button>
        </Link>
      </div>

      <Card className="border-t-4 border-blue-500">
        <div className="p-6 space-y-2">
          <h1 className="text-2xl font-bold text-[var(--verde-bosque)] flex items-center gap-2">
            <Calculator size={26} className="text-[var(--verde-hoja)]" />
            Calculadora manual para EcoFinanzas
          </h1>
          <p className="text-sm text-gray-600">
            Tu PDF se guardó correctamente. Para generar proyecciones, completa los datos mínimos que no se pudieron extraer automáticamente.
          </p>
        </div>
      </Card>

      {missingFields.length > 0 ? (
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800">Datos requeridos para proyecciones</h2>
            <p className="text-sm text-gray-500">
              Campos pendientes: {missingFields.map((field) => REQUIRED_FIELD_LABELS[field]).join(', ')}
            </p>
          </CardHeader>

          <div className="p-6 pt-0 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Valor prestado inicial (COP)"
              inputMode="numeric"
              placeholder="Ej: 120.000.000"
              value={form.valor_prestado_inicial}
              onChange={(event) => updateField('valor_prestado_inicial', event.target.value)}
              disabled={!missingFields.includes('valor_prestado_inicial')}
            />
            <Input
              label="Saldo capital actual (COP)"
              inputMode="decimal"
              placeholder="Ej: 98000000"
              value={form.saldo_capital_pesos}
              onChange={(event) => updateField('saldo_capital_pesos', event.target.value)}
              disabled={!missingFields.includes('saldo_capital_pesos')}
            />
            <Input
              label="Cuota mensual actual (COP)"
              inputMode="decimal"
              placeholder="Ej: 850000"
              value={form.valor_cuota_con_seguros}
              onChange={(event) => updateField('valor_cuota_con_seguros', event.target.value)}
              disabled={!missingFields.includes('valor_cuota_con_seguros')}
            />
            <Input
              label="Cuotas pendientes"
              inputMode="numeric"
              placeholder="Ej: 237"
              value={form.cuotas_pendientes}
              onChange={(event) => updateField('cuotas_pendientes', event.target.value)}
              disabled={!missingFields.includes('cuotas_pendientes')}
            />
            <Input
              label="Tasa de interés cobrada EA"
              inputMode="decimal"
              placeholder="Ej: 11.8"
              helperText="Puedes escribirla en porcentaje (11.8) o decimal (0.118)."
              value={form.tasa_interes_cobrada_ea}
              onChange={(event) => updateField('tasa_interes_cobrada_ea', event.target.value)}
              disabled={!missingFields.includes('tasa_interes_cobrada_ea')}
            />
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <Link href={`/dashboard/analysis/${analysisId}/summary`}>
              <Button variant="secondary">Ver resumen</Button>
            </Link>
            <Button variant="primary" onClick={handleSubmit} isLoading={saving} disabled={saving}>
              Guardar datos manuales
            </Button>
          </div>
        </Card>
      ) : (
        <Card className="border-green-200 bg-green-50">
          <div className="p-6 space-y-3">
            <h2 className="text-lg font-semibold text-green-700">No faltan datos críticos</h2>
            <p className="text-sm text-green-700/90">
              Este análisis ya cuenta con los datos mínimos para generar proyecciones.
            </p>
            <div className="pt-1">
              <Link href={`/dashboard/analysis/${analysisId}/summary`}>
                <Button variant="primary">Ir al resumen</Button>
              </Link>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

function parseDecimal(raw: string): number | null {
  if (!raw) return null;
  const trimmed = raw.replace(/\s/g, '').trim();
  const hasComma = trimmed.includes(',');
  const hasDot = trimmed.includes('.');

  let normalized = trimmed;
  if (hasComma && hasDot) {
    normalized = trimmed.replace(/\./g, '').replace(',', '.');
  } else if (hasComma) {
    normalized = trimmed.replace(',', '.');
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseInteger(raw: string): number | null {
  const digits = cleanDigitsInput(raw);
  if (!digits) return null;
  const parsed = Number(digits);
  if (!Number.isFinite(parsed)) return null;
  return Math.trunc(parsed);
}

function numberToInput(value?: number | null): string {
  if (value === null || value === undefined) return '';
  return formatMonetaryInput(String(value));
}

function intToInput(value?: number | null): string {
  if (value === null || value === undefined) return '';
  return formatDigitsInput(String(Math.trunc(value)));
}

function rateToInput(value?: number | null): string {
  if (value === null || value === undefined) return '';
  if (value > 0 && value <= 1) {
    return String(Number((value * 100).toFixed(4)));
  }
  return String(value);
}
