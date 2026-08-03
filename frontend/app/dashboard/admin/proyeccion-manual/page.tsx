'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertTriangle,
  BriefcaseBusiness,
  Calculator,
  FileText,
  PlusCircle,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import { toast } from 'sonner';

import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  cleanDigitsInput,
  formatCopCurrency,
  formatNumericInput,
  parseNumericInput,
} from '@/lib/utils';
import type { AdminManualProjectionRequest, UserProfile } from '@/types/api';

// ─────────────────────────────────────────────────────────────────────────────
// Definición de campos
// ─────────────────────────────────────────────────────────────────────────────

type FieldKind = 'text' | 'money' | 'rate' | 'uvr' | 'integer' | 'date' | 'select' | 'boolean';

/** Un campo del formulario declarado una sola vez: tipo, etiqueta y ayuda. */
interface FieldSpec {
  name: keyof FormState;
  label: string;
  kind: FieldKind;
  required?: boolean;
  helperText?: string;
  options?: Array<{ value: string; label: string }>;
  /** Solo aplica a créditos UVR. */
  uvrOnly?: boolean;
  /** Solo aplica cuando el crédito tiene beneficio FRECH. */
  frechOnly?: boolean;
}

interface SectionSpec {
  title: string;
  description?: string;
  columns?: 2 | 3;
  fields: FieldSpec[];
}

const SECTIONS: SectionSpec[] = [
  {
    title: 'Datos del cliente',
    description: 'Con la cédula o el correo se reutiliza el cliente si ya existe en la plataforma.',
    columns: 2,
    fields: [
      { name: 'customer_full_name', label: 'Nombre completo', kind: 'text', required: true },
      { name: 'customer_id_number', label: 'Cédula', kind: 'integer', required: true },
      { name: 'customer_email', label: 'Email', kind: 'text', required: true },
      { name: 'customer_phone', label: 'Teléfono', kind: 'integer', required: true },
      {
        name: 'ingresos_mensuales',
        label: 'Ingresos mensuales',
        kind: 'money',
        required: true,
        helperText: 'Ingreso declarado por el cliente',
      },
      {
        name: 'capacidad_pago_max',
        label: 'Capacidad de pago máxima',
        kind: 'money',
        helperText: 'Tope mensual que el cliente puede destinar al crédito',
      },
      {
        name: 'tipo_contrato_laboral',
        label: 'Tipo de contrato',
        kind: 'select',
        options: [
          { value: 'Indefinido', label: 'Indefinido' },
          { value: 'Término fijo', label: 'Término fijo' },
          { value: 'Independiente', label: 'Independiente' },
          { value: 'Prestación de servicios', label: 'Prestación de servicios' },
          { value: 'Otro', label: 'Otro' },
        ],
      },
    ],
  },
  {
    title: 'Identificación del crédito',
    columns: 3,
    fields: [
      { name: 'numero_credito', label: 'Número del crédito', kind: 'text', required: true },
      {
        name: 'sistema_amortizacion',
        label: 'Sistema de amortización',
        kind: 'select',
        required: true,
        options: [
          { value: 'PESOS', label: 'PESOS' },
          { value: 'UVR', label: 'UVR' },
        ],
      },
      {
        name: 'plan_credito',
        label: 'Plan del crédito',
        kind: 'text',
        helperText: 'Ej: Cuota constante en UVR - VIS',
      },
      { name: 'fecha_extracto', label: 'Fecha del extracto', kind: 'date', required: true },
      {
        name: 'fecha_desembolso',
        label: 'Fecha de desembolso',
        kind: 'date',
        helperText: 'Necesaria para estimar la vigencia FRECH',
      },
      {
        name: 'plazo_total_meses',
        label: 'Plazo total (meses)',
        kind: 'integer',
        helperText: 'Si se deja vacío se toma el número de cuotas pactadas',
      },
    ],
  },
  {
    title: 'Saldos y cuotas',
    columns: 3,
    fields: [
      { name: 'valor_prestado_inicial', label: 'Valor prestado', kind: 'money', required: true },
      {
        name: 'saldo_capital_pesos',
        label: 'Saldo capital',
        kind: 'money',
        required: true,
        helperText: 'Saldo a la fecha del extracto',
      },
      {
        name: 'total_por_pagar',
        label: 'Total por pagar del período',
        kind: 'money',
        helperText: 'Lo que el cliente debe pagar este mes',
      },
      { name: 'cuotas_pactadas', label: 'Cuotas pactadas', kind: 'integer', required: true },
      { name: 'cuotas_pagadas', label: 'Cuotas pagadas', kind: 'integer', required: true },
      { name: 'cuotas_pendientes', label: 'Cuotas por pagar', kind: 'integer', required: true },
      {
        name: 'nro_cuota_a_cancelar',
        label: 'Nro. cuota a cancelar',
        kind: 'integer',
        helperText: 'Número de la cuota que se está cobrando en el extracto',
      },
      {
        name: 'cuotas_vencidas',
        label: 'Cuotas vencidas',
        kind: 'integer',
        helperText: 'Cuotas en mora. Si es mayor a 0 se bloquea la proyección',
      },
    ],
  },
  {
    title: 'Tasas de interés (efectiva anual)',
    description: 'Puedes escribir 7,47 o 0,0747; ambas se interpretan como 7,47% E.A.',
    columns: 2,
    fields: [
      { name: 'tasa_interes_cobrada_ea', label: 'Tasa cobrada E.A.', kind: 'rate', required: true },
      { name: 'tasa_interes_pactada_ea', label: 'Tasa pactada E.A.', kind: 'rate' },
      { name: 'tasa_interes_subsidiada_ea', label: 'Tasa subsidiada E.A.', kind: 'rate' },
      { name: 'tasa_mora_pactada_ea', label: 'Tasa de mora E.A.', kind: 'rate' },
    ],
  },
  {
    title: 'Cuota mensual y seguros',
    columns: 3,
    fields: [
      {
        name: 'valor_cuota_con_seguros',
        label: 'Cuota completa aproximada',
        kind: 'money',
        required: true,
        helperText: 'Cuota total facturada, con seguros',
      },
      { name: 'valor_cuota_sin_seguros', label: 'Cuota sin seguros', kind: 'money' },
      {
        name: 'valor_cuota_con_subsidio',
        label: 'Cuota que paga el cliente',
        kind: 'money',
        helperText: 'Cuota neta después del subsidio FRECH',
      },
      { name: 'seguro_vida', label: 'Seguro de vida', kind: 'money' },
      { name: 'seguro_incendio', label: 'Seguro de incendio', kind: 'money' },
      { name: 'seguro_terremoto', label: 'Seguro de terremoto', kind: 'money' },
    ],
  },
  {
    title: 'Beneficio FRECH',
    description: 'Marca si el crédito cuenta con subsidio y cuánto ha recibido hasta hoy.',
    columns: 2,
    fields: [
      { name: 'tiene_beneficio_frech', label: '¿Cuenta con beneficio FRECH?', kind: 'boolean' },
      {
        name: 'beneficio_frech_mensual',
        label: 'Beneficio FRECH mensual',
        kind: 'money',
        frechOnly: true,
        required: true,
      },
      {
        name: 'total_frech_recibido',
        label: 'FRECH recibido hasta hoy',
        kind: 'money',
        frechOnly: true,
        helperText: 'Si se deja vacío se calcula: beneficio × cuotas pagadas',
      },
      { name: 'frech_fecha_inicio', label: 'Inicio de vigencia FRECH', kind: 'date', frechOnly: true },
      { name: 'frech_fecha_fin', label: 'Fin de vigencia FRECH', kind: 'date', frechOnly: true },
    ],
  },
  {
    title: 'Pagos acumulados',
    columns: 2,
    fields: [
      {
        name: 'total_pagado_cliente',
        label: 'Pagado por el cliente hasta hoy',
        kind: 'money',
        helperText: 'Si se deja vacío se calcula: cuota del cliente × cuotas pagadas',
      },
    ],
  },
  {
    title: 'Datos UVR',
    description: 'Obligatorios cuando el sistema de amortización es UVR.',
    columns: 3,
    fields: [
      { name: 'saldo_capital_uvr', label: 'Saldo capital en UVR', kind: 'uvr', uvrOnly: true, required: true },
      { name: 'valor_uvr_fecha_extracto', label: 'Valor UVR a la fecha', kind: 'uvr', uvrOnly: true, required: true },
      { name: 'valor_cuota_uvr', label: 'Valor de la cuota en UVR', kind: 'uvr', uvrOnly: true },
    ],
  },
  {
    title: 'Componentes del período',
    description: 'Desglose del último pago reportado en el extracto.',
    columns: 2,
    fields: [
      { name: 'capital_pagado_periodo', label: 'Capital abonado en el período', kind: 'money' },
      { name: 'intereses_corrientes_periodo', label: 'Intereses corrientes del período', kind: 'money' },
      { name: 'intereses_mora', label: 'Intereses de mora', kind: 'money' },
      { name: 'otros_cargos', label: 'Otros cargos', kind: 'money' },
    ],
  },
  {
    title: 'Opciones de abono a proyectar',
    columns: 3,
    fields: [
      { name: 'opcion_abono_1', label: 'Abono opción 1', kind: 'money' },
      { name: 'opcion_abono_2', label: 'Abono opción 2', kind: 'money' },
      { name: 'opcion_abono_3', label: 'Abono opción 3', kind: 'money' },
    ],
  },
];

const ALL_FIELDS = SECTIONS.flatMap((section) => section.fields);

// ─────────────────────────────────────────────────────────────────────────────
// Estado del formulario
// ─────────────────────────────────────────────────────────────────────────────

interface FormState {
  customer_full_name: string;
  customer_id_number: string;
  customer_email: string;
  customer_phone: string;
  ingresos_mensuales: string;
  capacidad_pago_max: string;
  tipo_contrato_laboral: string;
  numero_credito: string;
  sistema_amortizacion: string;
  plan_credito: string;
  fecha_extracto: string;
  fecha_desembolso: string;
  plazo_total_meses: string;
  valor_prestado_inicial: string;
  saldo_capital_pesos: string;
  total_por_pagar: string;
  cuotas_pactadas: string;
  cuotas_pagadas: string;
  cuotas_pendientes: string;
  cuotas_vencidas: string;
  nro_cuota_a_cancelar: string;
  tasa_interes_cobrada_ea: string;
  tasa_interes_pactada_ea: string;
  tasa_interes_subsidiada_ea: string;
  tasa_mora_pactada_ea: string;
  valor_cuota_con_seguros: string;
  valor_cuota_sin_seguros: string;
  valor_cuota_con_subsidio: string;
  seguro_vida: string;
  seguro_incendio: string;
  seguro_terremoto: string;
  tiene_beneficio_frech: string;
  beneficio_frech_mensual: string;
  total_frech_recibido: string;
  frech_fecha_inicio: string;
  frech_fecha_fin: string;
  total_pagado_cliente: string;
  saldo_capital_uvr: string;
  valor_uvr_fecha_extracto: string;
  valor_cuota_uvr: string;
  capital_pagado_periodo: string;
  intereses_corrientes_periodo: string;
  intereses_mora: string;
  otros_cargos: string;
  opcion_abono_1: string;
  opcion_abono_2: string;
  opcion_abono_3: string;
}

const INITIAL_FORM: FormState = {
  customer_full_name: '',
  customer_id_number: '',
  customer_email: '',
  customer_phone: '',
  ingresos_mensuales: '',
  capacidad_pago_max: '',
  tipo_contrato_laboral: 'Indefinido',
  numero_credito: '',
  sistema_amortizacion: 'PESOS',
  plan_credito: '',
  fecha_extracto: '',
  fecha_desembolso: '',
  plazo_total_meses: '',
  valor_prestado_inicial: '',
  saldo_capital_pesos: '',
  total_por_pagar: '',
  cuotas_pactadas: '',
  cuotas_pagadas: '',
  cuotas_pendientes: '',
  cuotas_vencidas: '0',
  nro_cuota_a_cancelar: '',
  tasa_interes_cobrada_ea: '',
  tasa_interes_pactada_ea: '',
  tasa_interes_subsidiada_ea: '',
  tasa_mora_pactada_ea: '',
  valor_cuota_con_seguros: '',
  valor_cuota_sin_seguros: '',
  valor_cuota_con_subsidio: '',
  seguro_vida: '',
  seguro_incendio: '',
  seguro_terremoto: '',
  tiene_beneficio_frech: 'false',
  beneficio_frech_mensual: '',
  total_frech_recibido: '',
  frech_fecha_inicio: '',
  frech_fecha_fin: '',
  total_pagado_cliente: '',
  saldo_capital_uvr: '',
  valor_uvr_fecha_extracto: '',
  valor_cuota_uvr: '',
  capital_pagado_periodo: '',
  intereses_corrientes_periodo: '',
  intereses_mora: '',
  otros_cargos: '',
  opcion_abono_1: '200.000',
  opcion_abono_2: '300.000',
  opcion_abono_3: '400.000',
};

/** Decimales admitidos por tipo de campo, alineados con las columnas del modelo. */
const DECIMALS_BY_KIND: Record<string, number> = { money: 2, rate: 4, uvr: 4 };

function normalizeByKind(kind: FieldKind, value: string): string {
  switch (kind) {
    case 'money':
      return formatNumericInput(value, { maxDecimals: 2, thousands: true });
    case 'rate':
      return formatNumericInput(value, { maxDecimals: 4, thousands: false });
    case 'uvr':
      return formatNumericInput(value, { maxDecimals: 4, thousands: true });
    case 'integer':
      return cleanDigitsInput(value);
    default:
      return value;
  }
}

function toNumber(kind: FieldKind, value: string): number | undefined {
  if (!value.trim()) return undefined;
  if (kind === 'integer') {
    const digits = cleanDigitsInput(value);
    return digits ? Number(digits) : undefined;
  }
  const parsed = parseNumericInput(value, DECIMALS_BY_KIND[kind] ?? 2);
  return parsed === null ? undefined : parsed;
}

// ─────────────────────────────────────────────────────────────────────────────
// Página
// ─────────────────────────────────────────────────────────────────────────────

export default function AdminManualProjectionPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isRoleLoading, setIsRoleLoading] = useState(true);
  const [banks, setBanks] = useState<Array<{ id: number; nombre: string }>>([]);
  const [bankId, setBankId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [pdfPassword, setPdfPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const user = await apiClient.getProfile();
        setCurrentUser(user);
        if (user.rol !== 'ADMIN') {
          router.replace('/dashboard');
          return;
        }
        setBanks(await apiClient.getBanks());
      } catch {
        router.replace('/auth/login');
      } finally {
        setIsRoleLoading(false);
      }
    };

    bootstrap();
  }, [router]);

  const isUvr = form.sistema_amortizacion === 'UVR';
  const hasFrech = form.tiene_beneficio_frech === 'true';

  const isFieldVisible = (field: FieldSpec) => {
    if (field.uvrOnly && !isUvr) return false;
    if (field.frechOnly && !hasFrech) return false;
    return true;
  };

  const updateField = (field: FieldSpec, rawValue: string) => {
    setForm((prev) => ({ ...prev, [field.name]: normalizeByKind(field.kind, rawValue) }));
  };

  // Vista previa de los acumulados con las mismas reglas del backend.
  const preview = useMemo(() => {
    const cuotasPagadas = toNumber('integer', form.cuotas_pagadas) ?? 0;
    const cuotaCompleta = toNumber('money', form.valor_cuota_con_seguros) ?? 0;
    const frechMensual = hasFrech ? toNumber('money', form.beneficio_frech_mensual) ?? 0 : 0;
    const cuotaCliente =
      toNumber('money', form.valor_cuota_con_subsidio) ?? Math.max(cuotaCompleta - frechMensual, 0);

    const pagadoCliente = toNumber('money', form.total_pagado_cliente) ?? cuotaCliente * cuotasPagadas;
    const frechAcumulado = hasFrech
      ? toNumber('money', form.total_frech_recibido) ?? frechMensual * cuotasPagadas
      : 0;

    return {
      cuotaCliente,
      pagadoCliente,
      frechAcumulado,
      totalAbonado: pagadoCliente + frechAcumulado,
    };
  }, [form, hasFrech]);

  const missingRequired = useMemo(() => {
    const missing = ALL_FIELDS.filter(
      (field) => field.required && isFieldVisible(field) && !form[field.name].trim()
    ).map((field) => field.label);

    if (!bankId) missing.push('Banco');
    if (!file) missing.push('PDF del extracto');
    return missing;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, bankId, file, isUvr, hasFrech]);

  const canSubmit = missingRequired.length === 0 && !submitting;

  const buildPayload = (): AdminManualProjectionRequest | null => {
    if (!file) return null;

    const cuotasPactadas = toNumber('integer', form.cuotas_pactadas) ?? 0;
    const cuotasPagadas = toNumber('integer', form.cuotas_pagadas) ?? 0;
    const cuotasPendientes = toNumber('integer', form.cuotas_pendientes) ?? 0;

    if (cuotasPagadas + cuotasPendientes > cuotasPactadas) {
      toast.error('La suma de cuotas pagadas y cuotas por pagar no puede superar las cuotas pactadas');
      return null;
    }

    if (form.fecha_desembolso && form.fecha_extracto && form.fecha_extracto < form.fecha_desembolso) {
      toast.error('La fecha del extracto no puede ser anterior a la fecha de desembolso');
      return null;
    }

    return {
      customer_full_name: form.customer_full_name.trim(),
      customer_id_number: form.customer_id_number.trim(),
      customer_email: form.customer_email.trim(),
      customer_phone: form.customer_phone.trim(),
      ingresos_mensuales: toNumber('money', form.ingresos_mensuales)!,
      capacidad_pago_max: toNumber('money', form.capacidad_pago_max),
      tipo_contrato_laboral: form.tipo_contrato_laboral,

      banco_id: Number(bankId),
      numero_credito: form.numero_credito.trim(),
      sistema_amortizacion: form.sistema_amortizacion,
      plan_credito: form.plan_credito.trim() || undefined,
      fecha_extracto: form.fecha_extracto,
      fecha_desembolso: form.fecha_desembolso || undefined,
      plazo_total_meses: toNumber('integer', form.plazo_total_meses),

      valor_prestado_inicial: toNumber('money', form.valor_prestado_inicial)!,
      saldo_capital_pesos: toNumber('money', form.saldo_capital_pesos)!,
      total_por_pagar: toNumber('money', form.total_por_pagar),

      cuotas_pactadas: cuotasPactadas,
      cuotas_pagadas: cuotasPagadas,
      cuotas_pendientes: cuotasPendientes,
      cuotas_vencidas: toNumber('integer', form.cuotas_vencidas) ?? 0,
      nro_cuota_a_cancelar: toNumber('integer', form.nro_cuota_a_cancelar),

      tasa_interes_cobrada_ea: toNumber('rate', form.tasa_interes_cobrada_ea)!,
      tasa_interes_pactada_ea: toNumber('rate', form.tasa_interes_pactada_ea),
      tasa_interes_subsidiada_ea: toNumber('rate', form.tasa_interes_subsidiada_ea),
      tasa_mora_pactada_ea: toNumber('rate', form.tasa_mora_pactada_ea),

      valor_cuota_con_seguros: toNumber('money', form.valor_cuota_con_seguros)!,
      valor_cuota_sin_seguros: toNumber('money', form.valor_cuota_sin_seguros),
      valor_cuota_con_subsidio: toNumber('money', form.valor_cuota_con_subsidio),

      tiene_beneficio_frech: hasFrech,
      beneficio_frech_mensual: hasFrech ? toNumber('money', form.beneficio_frech_mensual) : undefined,
      total_frech_recibido: hasFrech ? toNumber('money', form.total_frech_recibido) : undefined,
      frech_fecha_inicio: hasFrech ? form.frech_fecha_inicio || undefined : undefined,
      frech_fecha_fin: hasFrech ? form.frech_fecha_fin || undefined : undefined,

      total_pagado_cliente: toNumber('money', form.total_pagado_cliente),

      saldo_capital_uvr: isUvr ? toNumber('uvr', form.saldo_capital_uvr) : undefined,
      valor_uvr_fecha_extracto: isUvr ? toNumber('uvr', form.valor_uvr_fecha_extracto) : undefined,
      valor_cuota_uvr: isUvr ? toNumber('uvr', form.valor_cuota_uvr) : undefined,

      seguro_vida: toNumber('money', form.seguro_vida),
      seguro_incendio: toNumber('money', form.seguro_incendio),
      seguro_terremoto: toNumber('money', form.seguro_terremoto),

      capital_pagado_periodo: toNumber('money', form.capital_pagado_periodo),
      intereses_corrientes_periodo: toNumber('money', form.intereses_corrientes_periodo),
      intereses_mora: toNumber('money', form.intereses_mora),
      otros_cargos: toNumber('money', form.otros_cargos),

      opcion_abono_1: toNumber('money', form.opcion_abono_1),
      opcion_abono_2: toNumber('money', form.opcion_abono_2),
      opcion_abono_3: toNumber('money', form.opcion_abono_3),

      file,
      password: pdfPassword.trim() || undefined,
    };
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (missingRequired.length > 0) {
      toast.error(`Faltan campos obligatorios: ${missingRequired.join(', ')}`);
      return;
    }

    const payload = buildPayload();
    if (!payload) return;

    try {
      setSubmitting(true);
      const result = await apiClient.createAdminManualProjection(payload);

      if (!result.success || !result.analisis_id) {
        toast.error(result.message || 'No se pudo crear el análisis manual');
        return;
      }

      toast.success('Proyección manual creada y validada correctamente');
      router.push(`/dashboard/admin/proyecciones/${result.analisis_id}`);
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  if (isRoleLoading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]" />
      </div>
    );
  }

  if (currentUser?.rol !== 'ADMIN') {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Proyección manual</h1>
        <p className="text-sm text-gray-600">
          Digita todos los datos del extracto. El análisis queda marcado como{' '}
          <strong>Validado manualmente</strong> y usa los mismos cálculos que una proyección automática.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Upload size={18} /> Extracto y banco
            </h2>
          </CardHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold ml-1 text-verde-bosque">Banco *</label>
              <select
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl bg-white"
                value={bankId}
                onChange={(event) => setBankId(event.target.value)}
                required
              >
                <option value="">Selecciona</option>
                {banks.map((bank) => (
                  <option key={bank.id} value={bank.id}>
                    {bank.nombre}
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="Contraseña del PDF (si aplica)"
              type="password"
              value={pdfPassword}
              onChange={(event) => setPdfPassword(event.target.value)}
            />
          </div>
          <div className="mt-2 rounded-xl border border-dashed border-gray-300 p-4 bg-gray-50">
            <label className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-2">
              <FileText size={16} /> PDF del extracto *
            </label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="block w-full text-sm"
              required
            />
            {file && <p className="text-xs text-gray-500 mt-2">Archivo: {file.name}</p>}
          </div>
        </Card>

        {SECTIONS.map((section) => {
          const visibleFields = section.fields.filter(isFieldVisible);
          if (visibleFields.length === 0) return null;

          return (
            <Card key={section.title}>
              <CardHeader>
                <h2 className="text-lg font-semibold text-gray-800">{section.title}</h2>
                {section.description && (
                  <p className="text-xs text-gray-500 mt-1">{section.description}</p>
                )}
              </CardHeader>
              <div
                className={`grid grid-cols-1 gap-4 ${
                  section.columns === 3 ? 'md:grid-cols-3' : 'md:grid-cols-2'
                }`}
              >
                {visibleFields.map((field) => (
                  <FieldControl
                    key={field.name}
                    field={field}
                    value={form[field.name]}
                    onChange={(value) => updateField(field, value)}
                  />
                ))}
              </div>
            </Card>
          );
        })}

        <Card className="border-l-4 border-[var(--verde-hoja)]">
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Calculator size={18} /> Totales calculados
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              Vista previa de lo que quedará registrado en el resumen del crédito.
            </p>
          </CardHeader>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <SummaryTile label="Cuota que paga el cliente" value={preview.cuotaCliente} />
            <SummaryTile label="Pagado por el cliente" value={preview.pagadoCliente} />
            <SummaryTile label="FRECH acumulado" value={preview.frechAcumulado} accent="text-green-700" />
            <SummaryTile
              label="Total abonado al crédito"
              value={preview.totalAbonado}
              accent="text-[var(--verde-bosque)] font-bold"
            />
          </div>
        </Card>

        {missingRequired.length > 0 && (
          <Card className="border-amber-200 bg-amber-50">
            <div className="p-3 text-sm text-amber-800 flex items-start gap-2">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <span>Faltan campos obligatorios: {missingRequired.join(', ')}</span>
            </div>
          </Card>
        )}

        <div className="flex justify-end">
          <Button
            type="submit"
            leftIcon={<PlusCircle size={16} />}
            isLoading={submitting}
            disabled={!canSubmit}
          >
            Guardar y abrir proyecciones
          </Button>
        </div>
      </form>

      <Card className="border-emerald-200 bg-emerald-50">
        <div className="p-3 text-sm text-emerald-800 flex items-center gap-2">
          <ShieldCheck size={16} />
          Esta opción es exclusiva para administradores y marcará el análisis como{' '}
          <strong>Validado manualmente</strong> en el historial.
        </div>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Componentes auxiliares
// ─────────────────────────────────────────────────────────────────────────────

function FieldControl({
  field,
  value,
  onChange,
}: {
  field: FieldSpec;
  value: string;
  onChange: (value: string) => void;
}) {
  const label = field.required ? `${field.label} *` : field.label;

  if (field.kind === 'select') {
    return (
      <div className="space-y-1.5">
        <label className="text-sm font-semibold ml-1 text-verde-bosque">{label}</label>
        <div className="relative">
          <BriefcaseBusiness
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <select
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl bg-white"
            value={value}
            onChange={(event) => onChange(event.target.value)}
          >
            {field.options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="min-h-[20px] ml-1">
          {field.helperText && <p className="text-xs text-gray-600">{field.helperText}</p>}
        </div>
      </div>
    );
  }

  if (field.kind === 'boolean') {
    return (
      <div className="space-y-1.5">
        <label className="text-sm font-semibold ml-1 text-verde-bosque">{label}</label>
        <label className="flex items-center gap-3 px-4 py-2.5 border border-gray-300 rounded-xl bg-white cursor-pointer">
          <input
            type="checkbox"
            className="h-4 w-4 accent-[var(--verde-hoja)]"
            checked={value === 'true'}
            onChange={(event) => onChange(event.target.checked ? 'true' : 'false')}
          />
          <span className="text-sm text-gray-700">{value === 'true' ? 'Sí' : 'No'}</span>
        </label>
        <div className="min-h-[20px] ml-1">
          {field.helperText && <p className="text-xs text-gray-600">{field.helperText}</p>}
        </div>
      </div>
    );
  }

  return (
    <Input
      label={label}
      type={field.kind === 'date' ? 'date' : 'text'}
      inputMode={field.kind === 'integer' ? 'numeric' : field.kind === 'text' ? undefined : 'decimal'}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      helperText={field.helperText}
      required={field.required}
    />
  );
}

function SummaryTile({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: string;
}) {
  return (
    <div className="rounded-xl bg-gray-50 border border-gray-200 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-base mt-1 ${accent ?? 'text-gray-900 font-semibold'}`}>
        {formatCopCurrency(value)}
      </p>
    </div>
  );
}

/**
 * El backend responde `detail` como string, como objeto `{message}` o —para
 * errores de validación— como lista de `{field, message}`.
 */
function extractErrorMessage(error: unknown): string {
  const parsed = error as {
    message?: string;
    detail?: unknown;
    response?: { data?: { detail?: unknown; message?: string } };
  };
  const data = parsed?.response?.data;
  const detail = data?.detail ?? parsed?.detail;

  if (typeof detail === 'string' && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        const entry = item as { field?: string; message?: string; msg?: string };
        const text = (entry.message ?? entry.msg ?? '').replace(/^Value error,\s*/, '');
        if (!text) return '';
        return entry.field ? `${entry.field}: ${text}` : text;
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join(' · ');
  }

  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: string }).message;
    if (message) return message;
  }

  return data?.message || parsed?.message || 'No se pudo crear la proyección manual';
}
