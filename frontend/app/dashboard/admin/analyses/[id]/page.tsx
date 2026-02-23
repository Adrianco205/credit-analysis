'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AlertTriangle, ArrowLeft } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import { AdminAnalysisDetailResponse } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';

export default function AdminAnalysisDetailPage() {
  const params = useParams();
  const analysisId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState<AdminAnalysisDetailResponse | null>(null);

  useEffect(() => {
    if (analysisId) {
      loadDetail();
    }
  }, [analysisId]);

  const loadDetail = async () => {
    try {
      const data = await apiClient.getAdminAnalysisDetail(analysisId);
      setDetail(data);
    } catch (err: any) {
      setError(err?.message || 'No se pudo cargar el detalle del análisis');
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

  if (error || !detail) {
    return (
      <Card className="border-red-200 bg-red-50">
        <div className="flex items-center gap-3 p-6">
          <AlertTriangle className="text-red-600" size={20} />
          <span className="text-red-700">{error || 'No se encontró el análisis'}</span>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/dashboard/admin/analyses">
          <Button variant="ghost" leftIcon={<ArrowLeft size={16} />}>Volver al historial</Button>
        </Link>
        <Link href={`/dashboard/admin/analyses/${analysisId}/summary`}>
          <Button variant="secondary">Ver resumen</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <h1 className="text-xl font-semibold text-[var(--verde-bosque)]">Detalle del análisis</h1>
        </CardHeader>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <Info label="Cliente" value={detail.usuario_nombre} />
          <Info label="Cédula" value={detail.usuario_cedula} />
          <Info label="Email" value={detail.usuario_email} />
          <Info label="Teléfono" value={detail.usuario_telefono} />
          <Info label="Estado" value={detail.status} />
          <Info label="Número de crédito" value={detail.numero_credito} />
          <Info label="Sistema" value={detail.sistema_amortizacion} />
          <Info label="Plan" value={detail.plan_credito} />
          <Info label="Fecha extracto" value={detail.fecha_extracto} />
          <Info label="Saldo capital" value={formatMoney(detail.saldo_capital_pesos)} />
          <Info label="Ingresos mensuales" value={formatMoney(detail.ingresos_mensuales)} />
          <Info label="Capacidad de pago máxima" value={formatMoney(detail.capacidad_pago_max)} />
        </div>
      </Card>
    </div>
  );
}

function Info({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="border border-gray-100 rounded-lg p-3">
      <p className="text-gray-500">{label}</p>
      <p className="font-medium text-gray-800">{value ?? 'N/A'}</p>
    </div>
  );
}

function formatMoney(amount?: number | null) {
  if (amount === undefined || amount === null) return 'N/A';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(amount);
}
