'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AlertTriangle, ArrowLeft, CheckCircle2 } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import { AnalysisSummary } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';

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

          <Card>
            <CardHeader className="pb-2 border-b">
              <h3 className="font-semibold text-gray-700">DATOS BÁSICOS</h3>
            </CardHeader>
            <div className="p-4 pt-3 text-sm grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1">
              <Row label="Valor Prestado" value={formatMoney(summaryData.datos_basicos?.valor_prestado)} />
              <Row label="Cuotas Pactadas" value={summaryData.datos_basicos?.cuotas_pactadas} />
              <Row label="Cuotas Pagadas" value={summaryData.datos_basicos?.cuotas_pagadas} />
              <Row label="Cuotas por Pagar" value={summaryData.datos_basicos?.cuotas_por_pagar} />
              <Row label="Cuota Actual a Cancelar Aprox." value={formatMoney(summaryData.datos_basicos?.cuota_actual_aprox)} />
              <Row label="Beneficio FRECH (cuota)" value={formatMoney(summaryData.datos_basicos?.beneficio_frech)} valueClass="text-green-600" />
              <Row label="Cuota Completa Aprox. (sin FRECH)" value={formatMoney(summaryData.datos_basicos?.cuota_completa_aprox)} />
              <div className="col-span-full border-t my-2" />
              <Row label="Total Pagado al Día" value={formatMoney(summaryData.datos_basicos?.total_pagado_fecha)} valueClass="font-semibold text-gray-900" />
              <Row label="Total Beneficio FRECH Recibido" value={formatMoney(summaryData.datos_basicos?.total_frech_recibido)} valueClass="text-green-600 font-semibold" />
              <Row label="Monto Real Pagado al Banco" value={formatMoney(summaryData.datos_basicos?.monto_real_pagado_banco)} valueClass="font-bold text-lg text-[var(--verde-bosque)] bg-yellow-100 px-2 py-1 rounded" />
            </div>
          </Card>

          <Card>
            <CardHeader className="pb-2 border-b">
              <h3 className="font-semibold text-gray-700">LÍMITES CON EL BANCO HOY</h3>
            </CardHeader>
            <div className="p-4 pt-3 text-sm space-y-1">
              <Row label="Valor Prestado" value={formatMoney(summaryData.limites_banco?.valor_prestado)} />
              <Row label="Saldo Actual del Crédito" value={formatMoney(summaryData.limites_banco?.saldo_actual_credito)} valueClass="font-bold text-lg text-gray-900" />
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2 border-b">
                <h3 className="font-semibold text-gray-700">AJUSTE POR INFLACIÓN</h3>
              </CardHeader>
              <div className="p-4 pt-3 text-sm space-y-1">
                <Row
                  label="Ajuste en Pesos"
                  value={summaryData.ajuste_inflacion ? formatMoney(summaryData.ajuste_inflacion.ajuste_pesos) : 'N/A'}
                  valueClass={summaryData.ajuste_inflacion && Number(summaryData.ajuste_inflacion.ajuste_pesos) > 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}
                />
                <Row
                  label="% Ajustado (Incremento por Inflación)"
                  value={summaryData.ajuste_inflacion ? `${Number(summaryData.ajuste_inflacion.porcentaje_ajuste).toFixed(2)}%` : 'N/A'}
                  valueClass={summaryData.ajuste_inflacion && Number(summaryData.ajuste_inflacion.porcentaje_ajuste) > 0 ? 'text-red-600' : 'text-green-600'}
                />
              </div>
            </Card>

            <Card>
              <CardHeader className="pb-2 border-b">
                <h3 className="font-semibold text-gray-700">INTERESES Y SEGUROS</h3>
              </CardHeader>
              <div className="p-4 pt-3 text-sm space-y-1">
                <Row
                  label="Total Intereses y Seguros"
                  value={formatMoney(summaryData.costos_extra?.total_intereses_seguros)}
                  valueClass="text-red-600 font-bold text-lg"
                />
                <p className="text-xs text-gray-500 mt-2">Lo que NO abona a capital</p>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, valueClass = 'text-gray-900' }: { label: string; value: any; valueClass?: string }) {
  if (value === undefined || value === null) return null;
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
      <span className="text-gray-700">{label}</span>
      <span className={`font-medium ${valueClass}`}>{value}</span>
    </div>
  );
}

function formatMoney(amount?: number | null) {
  if (amount === undefined || amount === null) return '-';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}
