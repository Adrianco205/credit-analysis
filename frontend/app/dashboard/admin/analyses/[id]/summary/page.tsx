'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AlertTriangle, ArrowLeft, CheckCircle2 } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import { AnalysisSummary, SummaryRow } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { formatCopCurrency, formatNumberWithThousands } from '@/lib/utils';

const WARNING_MESSAGES: Record<string, string> = {
  wrong_mapping_saldo_as_cuota: 'Se detectó un posible mapeo incorrecto: el saldo fue interpretado como cuota.',
  blocked_quota_equals_saldo: 'La cuota se bloqueó porque coincide con el saldo actual del crédito.',
  possible_wrong_quota_mapping: 'La cuota extraída parece anormalmente alta frente al valor prestado.',
  value_total_inconsistency: 'Los valores de cuota total, beneficio y total a pagar no son consistentes entre sí.',
  cuotas_por_pagar_mismatch: 'La cantidad de cuotas por pagar presenta discrepancias entre fuentes.',
  cuotas_pagadas_source_discrepancy: 'Las cuotas pagadas extraídas no coinciden con la derivación por cuotas pendientes.',
  cuotas_consistency_mismatch: 'No hay coherencia entre cuotas pactadas, pagadas y por pagar.',
  low_confidence_extraction: 'Algunos campos fueron extraídos con baja confianza.',
  no_subsidy_detected: 'No se detectó subsidio/beneficio FRECH para este extracto.',
  intereses_seguros_period_value: 'El valor de intereses y seguros corresponde al periodo, no al acumulado histórico.',
  saldo_mayor_que_desembolso: 'El saldo actual es mayor que el valor desembolsado inicial.',
};

export default function AdminAnalysisSummaryPage() {
  const params = useParams();
  const analysisId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [summaryData, setSummaryData] = useState<AnalysisSummary | null>(null);

  useEffect(() => {
    if (analysisId) {
      loadSummary();
    }
  }, [analysisId]);

  const loadSummary = async () => {
    try {
      const summary = await apiClient.getAdminAnalysisSummary(analysisId);
      setSummaryData(summary);
    } catch (err: any) {
      if (err?.status_code === 404) {
        try {
          const detail = await apiClient.getAdminAnalysisDetail(analysisId);
          if (detail?.id && detail.id !== analysisId) {
            const summary = await apiClient.getAdminAnalysisSummary(detail.id);
            setSummaryData(summary);
            return;
          }
        } catch {
          // Se mantiene el error original
        }
      }
      setError(err?.message || 'No se pudo cargar el resumen del análisis');
    } finally {
      setLoading(false);
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
              <h2 className="text-lg font-semibold text-red-700">Error al cargar el análisis</h2>
              <p className="text-red-600">{error}</p>
            </div>
          </div>
          <div className="px-6 pb-6">
            <Link href="/dashboard/admin/analyses">
              <Button variant="secondary" leftIcon={<ArrowLeft size={16} />}>
                Volver al Historial
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
        <Link href="/dashboard/admin/analyses">
          <Button variant="ghost" leftIcon={<ArrowLeft size={16} />}>
            Volver al Historial
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Resumen del Análisis</h1>
      </div>

      <Card className="border-t-4 border-green-500">
        <div className="text-center py-6 space-y-3">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 size={32} className="text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Análisis Completado</h2>
          <p className="text-gray-600 max-w-md mx-auto">Vista administrativa del resumen hipotecario.</p>
        </div>
      </Card>

      {summaryData && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2 border-b">
              <h3 className="font-semibold text-gray-700">PERFIL FINANCIERO DEL CLIENTE</h3>
            </CardHeader>
            <div className="p-4 pt-3 text-sm space-y-1">
              <Row label="Ingresos mensuales" value={formatMoney(summaryData.ingresos_mensuales)} valueClass="font-semibold text-gray-900" />
              <Row label="Capacidad de pago máxima" value={formatMoney(summaryData.capacidad_pago_max)} valueClass="font-semibold text-gray-900" />
            </div>
          </Card>

          {summaryData.mortgage_summary?.sections?.map((section) => (
            <Card key={section.key}>
              <CardHeader className="pb-2 border-b">
                <h3 className="font-semibold text-gray-700">{section.title}</h3>
              </CardHeader>
              <div className="p-4 pt-3 text-sm space-y-1">
                {section.rows.map((row) => (
                  <Row
                    key={row.key}
                    label={row.label}
                    value={formatSummaryRowValue(row)}
                    valueClass={getSummaryRowClass(row)}
                    missing={row.source === 'missing'}
                    missingReason={getMissingReason(row, summaryData.warnings || [])}
                  />
                ))}
              </div>
            </Card>
          ))}

          {summaryData.warnings && summaryData.warnings.length > 0 && (
            <Card className="border-yellow-200 bg-yellow-50">
              <div className="p-3 text-xs text-yellow-800">
                <p className="font-semibold mb-1">Advertencias de validación</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  {summaryData.warnings.map((warning) => (
                    <li key={warning}>{formatWarningMessage(warning)}</li>
                  ))}
                </ul>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  valueClass = 'text-gray-900',
  missing = false,
  missingReason,
}: {
  label: string;
  value: any;
  valueClass?: string;
  missing?: boolean;
  missingReason?: string;
}) {
  const displayValue = value === undefined || value === null ? '—' : value;
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
      <span className="text-gray-700">{label}</span>
      <span
        className={`font-medium ${missing ? 'text-gray-400 italic' : valueClass}`}
        title={missing ? (missingReason || 'No encontrado en el PDF') : undefined}
      >
        {displayValue}
      </span>
    </div>
  );
}

function getMissingReason(row: SummaryRow, warnings: string[]) {
  const blockedByWrongMapping = warnings.includes('wrong_mapping_saldo_as_cuota') || warnings.includes('blocked_quota_equals_saldo');
  if (
    blockedByWrongMapping
    && ['cuota_actual_aprox', 'cuota_completa_aprox', 'total_pagado_fecha', 'total_frech_recibido', 'monto_real_pagado_banco'].includes(row.key)
  ) {
    return 'Bloqueado por validación: la cuota coincidía con el saldo del crédito (mapeo incorrecto).';
  }

  return 'No encontrado en el PDF';
}

function formatWarningMessage(warning: string) {
  if (WARNING_MESSAGES[warning]) {
    return WARNING_MESSAGES[warning];
  }

  if (warning.startsWith('negative_value:')) {
    const field = warning.replace('negative_value:', '');
    return `Se detectó un valor negativo inusual en el campo: ${field}.`;
  }

  return warning;
}

function formatSummaryRowValue(row: SummaryRow) {
  if (row.value === null || row.value === undefined) {
    return '—';
  }

  if (row.key === 'beneficio_frech' && Number(row.value) <= 0) {
    return 'No aplica';
  }

  if (row.currency) {
    return formatMoney(Number(row.value));
  }

  if (row.key.includes('porcentaje')) {
    return `${Number(row.value).toFixed(2)}%`;
  }

  return formatNumberWithThousands(Number(row.value));
}

function getSummaryRowClass(row: SummaryRow) {
  if (row.key.includes('beneficio')) return 'text-green-600 font-semibold';
  if (row.key.includes('intereses')) return 'text-red-600 font-bold';
  if (row.key.includes('monto_real')) return 'font-bold text-[var(--verde-bosque)]';
  return 'text-gray-900';
}

function formatMoney(amount?: number | null) {
  return formatCopCurrency(amount);
}
