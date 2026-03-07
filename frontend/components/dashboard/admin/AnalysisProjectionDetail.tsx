'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, ArrowLeft, Plus, Sparkles } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import type {
  AdminAnalysisDetailResponse,
  AdminProjectionOptionRequest,
  AdminProjectionResponse,
  ProposalOptionResponse,
  PropuestaCompletaResponse,
  ProjectionTimeResponse,
} from '@/types/api';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cleanDigitsInput, formatDigitsInput } from '@/lib/utils';

interface AnalysisProjectionDetailProps {
  analysisId: string;
}

const numberFormatter = new Intl.NumberFormat('es-CO', {
  maximumFractionDigits: 0,
});

const timesPaidFormatter = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const uvrFormatter = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

function formatCop(value?: number | null) {
  if (value === undefined || value === null) return '$ 0';
  return `$ ${numberFormatter.format(Math.round(Number(value)) || 0)}`;
}

function formatTimesPaid(value?: number | null) {
  if (value === undefined || value === null) return '0,00';
  return timesPaidFormatter.format(Number(value) || 0);
}

function formatUvr(value?: number | null) {
  if (value === undefined || value === null || Number(value) <= 0) return 'N/A';
  return uvrFormatter.format(Number(value));
}

function cleanDecimalInput(value: string) {
  const normalized = value.replace(',', '.').replace(/[^0-9.]/g, '');
  const firstDotIndex = normalized.indexOf('.');
  if (firstDotIndex === -1) return normalized;
  const integerPart = normalized.slice(0, firstDotIndex + 1);
  const decimalPart = normalized.slice(firstDotIndex + 1).replace(/\./g, '');
  return `${integerPart}${decimalPart}`;
}

function parsePositiveDecimal(value: string) {
  const parsed = Number(cleanDecimalInput(value));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function toTimeDescription(time?: ProjectionTimeResponse | null) {
  if (!time) return '0 años, 0 meses';
  return time.descripcion || `${time.anios || 0} años, ${time.meses || 0} meses`;
}

function monthsToTime(months?: number | null): ProjectionTimeResponse {
  const safeMonths = Math.max(0, Number(months || 0));
  const anios = Math.floor(safeMonths / 12);
  const meses = safeMonths % 12;
  return {
    anios,
    meses,
    total_meses: safeMonths,
    descripcion: `${anios} años, ${meses} meses`,
  };
}

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === 'object' && error && 'message' in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim().length > 0) {
      return message;
    }
  }
  return fallback;
}

function buildLegacyProposal(
  detail: AdminAnalysisDetailResponse,
  legacy: AdminProjectionResponse[]
): PropuestaCompletaResponse {
  const cuotasPendientes = Number(detail.cuotas_pendientes || 0);
  const saldoCredito = Number(detail.saldo_capital_pesos || 0);
  const frech = Number(detail.beneficio_frech_mensual || 0);
  const cuotaConSubsidio = Number(detail.valor_cuota_con_subsidio || 0);
  const cuotaConSeguros = Number(detail.valor_cuota_con_seguros || 0);
  const cuotaSinSeguros = Number(detail.valor_cuota_sin_seguros || 0);
  const sistema = String(detail.sistema_amortizacion || '').toUpperCase();
  const esUvr = sistema.includes('UVR');

  // Prioriza la cuota que realmente paga el cliente (sin FRECH).
  // Si no viene explícita, intenta derivarla desde cuota completa - FRECH.
  const cuotaActual =
    cuotaConSubsidio > 0
      ? cuotaConSubsidio
      : (cuotaConSeguros > frech && frech > 0
        ? cuotaConSeguros - frech
        : (cuotaConSeguros || cuotaSinSeguros));
  const costoTotalProyectado = Number(
    detail.costo_total_proyectado || detail.total_por_pagar_proyectado || detail.total_por_pagar || 0
  );
  const costoTotalProyectadoBanco = Number(detail.costo_total_proyectado_banco || costoTotalProyectado);
  const totalSubsidioFrechProyectado = Number(detail.total_subsidio_frech_proyectado || 0);
  const totalPagarSimple = Number(detail.total_por_pagar_simple || 0) > 0
    ? Number(detail.total_por_pagar_simple)
    : cuotaActual * cuotasPendientes;
  const vecesPagado =
    Number(detail.veces_pagado_actual || 0) > 0
      ? Number(detail.veces_pagado_actual || 0)
      : (saldoCredito > 0 ? costoTotalProyectadoBanco / saldoCredito : 0);

  const tasaCobradaConFrech = Number(
    detail.tasa_interes_subsidiada_ea ?? detail.tasa_interes_cobrada_ea ?? 0
  );
  const segurosActualesMensual = Number(detail.seguros_total_mensual || 0);

  const opciones: ProposalOptionResponse[] = legacy.map((item) => {
    const totalPorPagarAprox = Number(item.total_por_pagar_aprox || 0);
    const totalPorPagarSimple = Number(item.total_por_pagar_simple || 0) > 0
      ? Number(item.total_por_pagar_simple)
      : Number(item.nuevo_valor_cuota || 0) * Number(item.cuotas_nuevas || 0);
    const costoTotalProyectadoOpcion = Number(item.costo_total_proyectado || 0);
    const costoTotalProyectadoBancoOpcion = Number(item.costo_total_proyectado_banco || costoTotalProyectadoOpcion);
    const totalSubsidioFrechProyectadoOpcion = Number(item.total_subsidio_frech_proyectado || 0);
    const vecesPagadoOpcion = Number(item.veces_pagado || 0);

    // Compatibilidad con respuestas antiguas: total_por_pagar_aprox era costo proyectado.
    const totalSimpleFinal = totalPorPagarSimple > 0 ? totalPorPagarSimple : totalPorPagarAprox;
    const costoFinal = costoTotalProyectadoOpcion > 0
      ? costoTotalProyectadoOpcion
      : (totalPorPagarAprox > totalSimpleFinal ? totalPorPagarAprox : totalSimpleFinal);

    return {
      id: item.id,
      numero_opcion: item.numero_opcion,
      nombre_opcion: item.nombre_opcion,
      abono_adicional_mensual: Number(item.abono_adicional_mensual || 0),
      cuotas_nuevas: Number(item.cuotas_nuevas || 0),
      tiempo_restante: monthsToTime((item.tiempo_restante_anios || 0) * 12 + (item.tiempo_restante_meses || 0)),
      nuevo_valor_cuota: Number(item.nuevo_valor_cuota || 0),
      total_por_pagar_aprox: totalSimpleFinal,
      total_por_pagar_simple: totalSimpleFinal,
      costo_total_proyectado: costoFinal,
      costo_total_proyectado_banco: costoTotalProyectadoBancoOpcion,
      total_subsidio_frech_proyectado: totalSubsidioFrechProyectadoOpcion,
      cuotas_reducidas: Number(item.cuotas_reducidas || 0),
      tiempo_ahorrado: monthsToTime((item.tiempo_ahorrado_anios || 0) * 12 + (item.tiempo_ahorrado_meses || 0)),
      valor_ahorrado_intereses: Number(item.valor_ahorrado_intereses || 0),
      veces_pagado: vecesPagadoOpcion,
      honorarios_calculados: Number(item.honorarios_calculados || 0),
      honorarios_con_iva: Number(item.honorarios_con_iva || 0),
      ingreso_minimo_requerido: Number(item.ingreso_minimo_requerido || 0),
      origen: item.origen,
      es_opcion_seleccionada: item.es_opcion_seleccionada,
    };
  });

  return {
    analisis_id: detail.id,
    numero_credito: detail.numero_credito || null,
    nombre_cliente: detail.usuario_nombre || detail.nombre_titular_extracto || null,
    banco_nombre: detail.banco_nombre || null,
    fecha_generacion: new Date().toISOString().slice(0, 10),
    limites_actuales: {
      saldo_credito: Number(detail.saldo_capital_pesos || 0),
      cuotas_pendientes: cuotasPendientes,
      tiempo_pendiente: monthsToTime(cuotasPendientes),
      abono_adicional_cuota: 0,
      valor_cuota: cuotaActual,
      total_por_pagar_aprox: totalPagarSimple,
      total_por_pagar_simple: totalPagarSimple,
      costo_total_proyectado: costoTotalProyectado,
      costo_total_proyectado_banco: costoTotalProyectadoBanco,
      total_subsidio_frech_proyectado: totalSubsidioFrechProyectado,
      veces_pagado: vecesPagado,
    },
    opciones,
    tasa_cobrada_con_frech: esUvr && tasaCobradaConFrech > 0 ? tasaCobradaConFrech : null,
    seguros_actuales: segurosActualesMensual > 0 ? segurosActualesMensual : null,
    vigencia_dias: 20,
    fecha_vencimiento: null,
    agente_financiero: null,
  };
}

export function AnalysisProjectionDetail({ analysisId }: AnalysisProjectionDetailProps) {
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [previewingPdf, setPreviewingPdf] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [error, setError] = useState('');

  const [detail, setDetail] = useState<AdminAnalysisDetailResponse | null>(null);
  const [proposal, setProposal] = useState<PropuestaCompletaResponse | null>(null);

  const [adminOptionEnabled, setAdminOptionEnabled] = useState(false);
  const [adminOptionValue, setAdminOptionValue] = useState('');
  const [uvrMode, setUvrMode] = useState<'extracto' | 'manual'>('extracto');
  const [uvrManualValue, setUvrManualValue] = useState('');

  const clientOptions = useMemo(() => {
    const raw = detail?.opciones_abono_preferidas || [];
    return [
      Number(raw[0] || 0),
      Number(raw[1] || 0),
      Number(raw[2] || 0),
    ];
  }, [detail]);

  const canCalculate = useMemo(() => {
    const baseValid = clientOptions.every((value) => value > 0);
    if (!baseValid) return false;
    const isUvrCredit = (detail?.sistema_amortizacion || '').toLowerCase().includes('uvr');
    if (isUvrCredit && uvrMode === 'manual' && parsePositiveDecimal(uvrManualValue) <= 0) {
      return false;
    }
    if (!adminOptionEnabled) return true;
    return Number(cleanDigitsInput(adminOptionValue)) > 0;
  }, [
    clientOptions,
    adminOptionEnabled,
    adminOptionValue,
    detail?.sistema_amortizacion,
    uvrMode,
    uvrManualValue,
  ]);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiClient.getAdminAnalysisDetail(analysisId);
      setDetail(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'No se pudo cargar el detalle del crédito.'));
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleCalculate = async () => {
    if (!detail) return;
    if (!canCalculate) {
      setError('Las 3 opciones del cliente deben ser mayores a cero.');
      return;
    }

    setCalculating(true);
    setError('');

    const opciones: AdminProjectionOptionRequest[] = [
      { numero_opcion: 1, abono_adicional_mensual: clientOptions[0], nombre_opcion: '1a Elección' },
      { numero_opcion: 2, abono_adicional_mensual: clientOptions[1], nombre_opcion: '2a Elección' },
      { numero_opcion: 3, abono_adicional_mensual: clientOptions[2], nombre_opcion: '3a Elección' },
    ];

    if (adminOptionEnabled && Number(cleanDigitsInput(adminOptionValue)) > 0) {
      opciones.push({
        numero_opcion: 4,
        abono_adicional_mensual: Number(cleanDigitsInput(adminOptionValue)),
        nombre_opcion: 'Recomendada',
      });
    }

    try {
      const isUvrCredit = (detail.sistema_amortizacion || '').toLowerCase().includes('uvr');
      const response = await apiClient.calculateAdminProjections(analysisId, {
        opciones,
        uvr_mode: isUvrCredit ? uvrMode : undefined,
        uvr_manual_value:
          isUvrCredit && uvrMode === 'manual' ? parsePositiveDecimal(uvrManualValue) : undefined,
      });
      if (Array.isArray(response)) {
        setProposal(buildLegacyProposal(detail, response));
      } else {
        setProposal(response);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'No se pudieron calcular las proyecciones.'));
    } finally {
      setCalculating(false);
    }
  };

  const handleDownloadProposalPdf = async () => {
    setDownloadingPdf(true);
    setError('');

    try {
      const blob = await apiClient.downloadAdminProposalPdf(analysisId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `propuesta_admin_ecofinanzas_${analysisId}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'No se pudo descargar el PDF de proyecciones.'));
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handlePreviewProposalPdf = async () => {
    setPreviewingPdf(true);
    setError('');

    try {
      const blob = await apiClient.downloadAdminProposalPdf(analysisId);
      const url = window.URL.createObjectURL(blob);
      const previewWindow = window.open(url, '_blank', 'noopener,noreferrer');

      if (!previewWindow) {
        setError('No se pudo abrir la vista previa. Verifica si el navegador bloqueó la ventana emergente.');
      }

      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 60000);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'No se pudo abrir la vista previa del PDF.'));
    } finally {
      setPreviewingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[55vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]" />
      </div>
    );
  }

  if (error && !detail) {
    return (
      <Card className="border border-red-200 bg-red-50">
        <div className="p-6 flex items-center gap-3 text-red-700">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      </Card>
    );
  }

  if (!detail) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/dashboard/admin/proyecciones">
          <Button variant="ghost" leftIcon={<ArrowLeft size={16} />}>Volver</Button>
        </Link>
      </div>

      <Card variant="bordered">
        <CardHeader>
          <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Detalle y Proyección Financiera</h1>
          <p className="text-sm text-gray-600">Revisión del crédito y ejecución del motor financiero.</p>
        </CardHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <SummaryCard label="Saldo actual" value={formatCop(detail.saldo_capital_pesos)} />
          <SummaryCard
            label="Tasa"
            value={detail.tasa_interes_cobrada_ea !== undefined && detail.tasa_interes_cobrada_ea !== null
              ? `${(Number(detail.tasa_interes_cobrada_ea) * 100).toFixed(2)}% EA`
              : 'N/A'}
          />
          <SummaryCard label="Banco" value={detail.banco_nombre || 'N/A'} />
          <SummaryCard label="Cliente" value={detail.usuario_nombre || detail.nombre_titular_extracto || 'N/A'} />
        </div>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold text-[var(--verde-bosque)]">Motor de Proyecciones</h2>
          <p className="text-sm text-gray-600">Configuración de Escenarios</p>
        </CardHeader>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center gap-2">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input
              label="Opción 1 (Cliente)"
              inputMode="numeric"
              value={formatDigitsInput(String(clientOptions[0] || ''))}
              disabled
            />
            <Input
              label="Opción 2 (Cliente)"
              inputMode="numeric"
              value={formatDigitsInput(String(clientOptions[1] || ''))}
              disabled
            />
            <Input
              label="Opción 3 (Cliente)"
              inputMode="numeric"
              value={formatDigitsInput(String(clientOptions[2] || ''))}
              disabled
            />
          </div>

          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              leftIcon={<Plus size={16} />}
              onClick={() => setAdminOptionEnabled((prev) => !prev)}
            >
              {adminOptionEnabled ? 'Quitar Estrategia Personalizada' : 'Agregar Estrategia Personalizada'}
            </Button>
          </div>

          {adminOptionEnabled && (
            <div className="max-w-sm">
              <Input
                label="Opción Recomendada (Admin)"
                inputMode="numeric"
                value={formatDigitsInput(adminOptionValue)}
                onChange={(event) => setAdminOptionValue(cleanDigitsInput(event.target.value))}
                placeholder="Ej. 500000"
              />
            </div>
          )}

          {(detail.sistema_amortizacion || '').toLowerCase().includes('uvr') && (
            <div className="rounded-xl border border-[var(--gray-200)] bg-[var(--gray-50)] p-4 space-y-4">
              <div>
                <p className="text-sm font-semibold text-[var(--verde-bosque)]">Valor UVR para el cálculo</p>
                <p className="text-xs text-gray-600">
                  UVR del extracto: {formatUvr(detail.valor_uvr_fecha_extracto)}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="flex items-center gap-2 rounded-lg border border-[var(--gray-200)] bg-white p-3 text-sm text-gray-700">
                  <input
                    type="radio"
                    name="uvr-mode"
                    value="extracto"
                    checked={uvrMode === 'extracto'}
                    onChange={() => setUvrMode('extracto')}
                  />
                  Usar UVR del extracto
                </label>

                <label className="flex items-center gap-2 rounded-lg border border-[var(--gray-200)] bg-white p-3 text-sm text-gray-700">
                  <input
                    type="radio"
                    name="uvr-mode"
                    value="manual"
                    checked={uvrMode === 'manual'}
                    onChange={() => setUvrMode('manual')}
                  />
                  Ingresar UVR manual
                </label>
              </div>

              {uvrMode === 'manual' && (
                <div className="max-w-sm">
                  <Input
                    label="UVR manual"
                    inputMode="decimal"
                    value={uvrManualValue}
                    onChange={(event) => setUvrManualValue(cleanDecimalInput(event.target.value))}
                    placeholder="Ej. 382.1234"
                  />
                </div>
              )}
            </div>
          )}

          <Button
            size="lg"
            className="w-full md:w-auto"
            leftIcon={<Sparkles size={18} />}
            onClick={handleCalculate}
            isLoading={calculating}
            disabled={!canCalculate || calculating}
          >
            CALCULAR PROYECCIONES
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h3 className="text-lg font-semibold text-gray-800">Nuevas Oportunidades</h3>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                variant="secondary"
                onClick={handlePreviewProposalPdf}
                isLoading={previewingPdf}
                disabled={calculating || previewingPdf || downloadingPdf || !proposal || proposal.opciones.length === 0}
              >
                Vista previa PDF
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleDownloadProposalPdf}
                isLoading={downloadingPdf}
                disabled={calculating || previewingPdf || downloadingPdf || !proposal || proposal.opciones.length === 0}
              >
                Descargar PDF de Proyecciones
              </Button>
            </div>
          </div>
        </CardHeader>

        {calculating ? (
          <div className="py-12 flex flex-col items-center gap-3 text-gray-600">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--verde-hoja)]" />
            <p className="font-medium">Calculando proyecciones...</p>
          </div>
        ) : !proposal || proposal.opciones.length === 0 ? (
          <div className="py-8 text-center text-gray-500 text-sm">
            Aún no hay resultados. Configura escenarios y presiona calcular.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <InstitutionalOpportunitiesTable
              proposal={proposal}
              sistemaAmortizacion={detail.sistema_amortizacion}
              beneficioFrechMensual={detail.beneficio_frech_mensual}
              tasaInteresCobradaEa={detail.tasa_interes_cobrada_ea}
            />
          </div>
        )}
      </Card>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-200 p-4 bg-white">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function InstitutionalOpportunitiesTable({
  proposal,
  sistemaAmortizacion,
  beneficioFrechMensual,
  tasaInteresCobradaEa,
}: {
  proposal: PropuestaCompletaResponse;
  sistemaAmortizacion?: string | null;
  beneficioFrechMensual?: number | null;
  tasaInteresCobradaEa?: number | null;
}) {
  const opciones = proposal.opciones || [];
  const gridTemplateColumns = `minmax(290px, 290px) repeat(${opciones.length}, minmax(220px, 1fr))`;
  const esUvr = String(sistemaAmortizacion || '').toUpperCase().includes('UVR');
  const frechActivo = Number(beneficioFrechMensual || 0) > 0;
  const tasaRaw = proposal.tasa_cobrada_con_frech ?? tasaInteresCobradaEa ?? null;
  const tasaLabel = frechActivo ? 'Tasa cobrada UVR + FRECH' : 'Tasa cobrada UVR';
  const showTasa = esUvr && tasaRaw !== null && Number(tasaRaw) > 0;
  const segurosActuales = Number(proposal.seguros_actuales || 0);
  const showSeguros = segurosActuales > 0;

  return (
    <div className="min-w-[980px] rounded-xl border border-[var(--gray-200)] bg-white overflow-hidden">
      <div className="grid" style={{ gridTemplateColumns }}>
        <HeaderLeftCell title="LÍMITES CON EL BANCO HOY" />
        {opciones.map((opcion) => (
          <HeaderOptionCell
            key={`header-${opcion.numero_opcion}`}
            title={opcion.nombre_opcion || `${opcion.numero_opcion}a Elección`}
          />
        ))}
      </div>

      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Saldo Crédito"
        leftValue={formatCop(proposal.limites_actuales.saldo_credito)}
        options={opciones}
        getOptionValue={() => ''}
        leftVariant="base"
        isBlockStart
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Cuotas Pendientes"
        leftValue={String(proposal.limites_actuales.cuotas_pendientes || 0)}
        options={opciones}
        getOptionValue={(opcion) => String(opcion.cuotas_nuevas || 0)}
        leftVariant="base"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Tiempo Pendiente"
        leftValue={toTimeDescription(proposal.limites_actuales.tiempo_pendiente)}
        options={opciones}
        getOptionValue={(opcion) => toTimeDescription(opcion.tiempo_restante)}
        leftVariant="base"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Abono adicional a cuota"
        leftValue={formatCop(proposal.limites_actuales.abono_adicional_cuota)}
        options={opciones}
        getOptionValue={(opcion) => formatCop(opcion.abono_adicional_mensual)}
        leftVariant="base"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Cuota actual a cancelar aprox."
        leftValue={formatCop(proposal.limites_actuales.valor_cuota)}
        options={opciones}
        getOptionValue={(opcion) => formatCop(opcion.nuevo_valor_cuota)}
        leftVariant="base"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Total estimado a pagar al banco\n(incluye seguros proyectados)"
        leftValue={formatCop(proposal.limites_actuales.costo_total_proyectado_banco || proposal.limites_actuales.costo_total_proyectado)}
        options={opciones}
        getOptionValue={(opcion) => formatCop(opcion.costo_total_proyectado_banco || opcion.costo_total_proyectado)}
        leftVariant="base"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="No. Veces Pagado (sobre costo banco)"
        leftValue={formatTimesPaid(proposal.limites_actuales.veces_pagado)}
        options={opciones}
        getOptionValue={(opcion) => formatTimesPaid(opcion.veces_pagado)}
        leftVariant="base"
        isBlockEnd
      />

      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Valor Ahorrado en Intereses"
        options={opciones}
        getOptionValue={(opcion) => formatCop(opcion.valor_ahorrado_intereses)}
        valueTone="benefit"
        isBlockStart
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label=""
        options={opciones}
        getOptionValue={() => 'Calculado como: Total actual banco - Total proyectado banco opción'}
        valueTone="benefit"
        textSize="xs"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Cuotas Reducidas"
        options={opciones}
        getOptionValue={(opcion) => String(opcion.cuotas_reducidas || 0)}
        valueTone="benefit"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Tiempo Ahorrado"
        options={opciones}
        getOptionValue={(opcion) => toTimeDescription(opcion.tiempo_ahorrado)}
        valueTone="benefit"
        isBlockEnd
      />

      {showTasa && (
        <OpportunityRow
          gridTemplateColumns={gridTemplateColumns}
          label={tasaLabel}
          leftValue={formatPercentRate(tasaRaw)}
          options={opciones}
          getOptionValue={() => ''}
          leftVariant="base"
          isBlockStart={!showSeguros}
        />
      )}

      {showSeguros && (
        <OpportunityRow
          gridTemplateColumns={gridTemplateColumns}
          label="Seguros actuales"
          leftValue={formatCop(segurosActuales)}
          options={opciones}
          getOptionValue={() => ''}
          leftVariant="base"
          isBlockEnd
          isBlockStart={!showTasa}
        />
      )}

      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="HONORARIOS 6% o TARIFA MÍNIMA"
        options={opciones}
        getOptionValue={() => 'HONORARIOS 6% o TARIFA MÍNIMA'}
        valueTone="fees"
        labelTone="info"
        isBlockStart
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Valor Honorarios"
        options={opciones}
        getOptionValue={(opcion) => formatCop(opcion.honorarios_con_iva)}
        valueTone="fees"
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label=""
        options={opciones}
        getOptionValue={() => 'Estos costos incluyen IVA del 19%'}
        valueTone="fees"
        textSize="xs"
        isBlockEnd
      />

      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="INGRESOS MINIMOS A DEMOSTRAR"
        options={opciones}
        getOptionValue={() => ''}
        labelTone="danger"
        isBlockStart
      />
      <OpportunityRow
        gridTemplateColumns={gridTemplateColumns}
        label="Ingresos Mínimos"
        options={opciones}
        getOptionValue={(opcion) => formatCop(opcion.ingreso_minimo_requerido)}
        isBlockEnd
      />
    </div>
  );
}

function formatPercentRate(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'N/A';
  }
  const normalized = value > 1 ? value : value * 100;
  return `${normalized.toFixed(2)} %`;
}

function HeaderLeftCell({ title }: { title: string }) {
  return (
    <div className="sticky left-0 z-30 border-b border-[var(--gray-200)] border-r bg-[var(--info)] px-4 py-3 text-sm font-bold tracking-wide text-white">
      {title}
    </div>
  );
}

function HeaderOptionCell({ title }: { title: string }) {
  return (
    <div className="border-b border-[var(--gray-200)] px-3 py-3 text-center text-sm font-semibold text-[var(--verde-bosque)] bg-[var(--gray-50)]">
      {title}
    </div>
  );
}

function OpportunityRow({
  gridTemplateColumns,
  label,
  options,
  getOptionValue,
  leftValue,
  leftVariant = 'label',
  valueTone = 'default',
  labelTone = 'default',
  textSize = 'sm',
  isBlockStart,
  isBlockEnd,
}: {
  gridTemplateColumns: string;
  label: string;
  options: ProposalOptionResponse[];
  getOptionValue: (opcion: ProposalOptionResponse) => string;
  leftValue?: string;
  leftVariant?: 'base' | 'label';
  valueTone?: 'default' | 'benefit' | 'fees';
  labelTone?: 'default' | 'info' | 'danger';
  textSize?: 'sm' | 'xs';
  isBlockStart?: boolean;
  isBlockEnd?: boolean;
}) {
  const borderClass = isBlockStart
    ? 'border-t-2 border-t-[var(--gray-300)]'
    : isBlockEnd
      ? 'border-b-2 border-b-[var(--gray-300)]'
      : 'border-b border-[var(--gray-200)]';

  const leftLabelToneClass =
    labelTone === 'danger'
      ? 'text-red-600 font-bold'
      : labelTone === 'info'
        ? 'text-[var(--info)] font-bold'
        : 'text-[var(--gray-700)] font-semibold';

  const valueToneClass =
    valueTone === 'benefit'
      ? 'bg-verde-suave text-[var(--verde-bosque)] font-semibold'
      : valueTone === 'fees'
        ? 'bg-[var(--gray-50)] text-[var(--gray-700)] font-medium'
        : 'bg-white text-[var(--gray-900)]';

  const labelLines = label.split('\n');

  return (
    <div className="grid" style={{ gridTemplateColumns }}>
      <div
        className={`sticky left-0 z-20 border-r border-[var(--gray-200)] px-4 py-3 ${borderClass} ${
          leftVariant === 'base' ? 'bg-[var(--info)] text-white' : 'bg-white'
        }`}
      >
        <div className={`${leftVariant === 'base' ? 'text-blue-50' : leftLabelToneClass} ${textSize === 'xs' ? 'text-xs' : 'text-sm'}`}>
          {labelLines.map((line, index) => (
            <div key={`${line}-${index}`}>{line}</div>
          ))}
        </div>
        {leftVariant === 'base' && (
          <div className="mt-1 text-base font-semibold text-white">{leftValue || '$ 0'}</div>
        )}
      </div>

      {options.map((opcion) => (
        <div
          key={`${label}-${opcion.numero_opcion}`}
          className={`px-3 py-3 text-center ${textSize === 'xs' ? 'text-xs' : 'text-sm'} ${borderClass} ${valueToneClass}`}
        >
          {getOptionValue(opcion)}
        </div>
      ))}
    </div>
  );
}
