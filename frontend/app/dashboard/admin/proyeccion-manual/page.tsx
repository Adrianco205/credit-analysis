'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, BriefcaseBusiness, FileText, PlusCircle } from 'lucide-react';
import { toast } from 'sonner';

import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cleanDigitsInput, formatDigitsInput, formatMonetaryInput, parseMonetaryInput } from '@/lib/utils';
import type { UserProfile } from '@/types/api';

interface FormState {
  customer_full_name: string;
  customer_id_number: string;
  customer_email: string;
  customer_phone: string;
  ingresos_mensuales: string;
  capacidad_pago_max: string;
  tipo_contrato_laboral: string;
  banco_id: string;
  opcion_abono_1: string;
  opcion_abono_2: string;
  opcion_abono_3: string;
  numero_credito: string;
  sistema_amortizacion: string;
  plan_credito: string;
  valor_prestado_inicial: string;
  fecha_desembolso: string;
  fecha_extracto: string;
  plazo_total_meses: string;
  cuotas_pactadas: string;
  cuotas_pagadas: string;
  cuotas_pendientes: string;
  tasa_interes_pactada_ea: string;
  tasa_interes_cobrada_ea: string;
  tasa_interes_subsidiada_ea: string;
  tasa_mora_pactada_ea: string;
  valor_cuota_sin_seguros: string;
  valor_cuota_con_seguros: string;
  beneficio_frech_mensual: string;
  valor_cuota_con_subsidio: string;
  saldo_capital_pesos: string;
  total_por_pagar: string;
  saldo_capital_uvr: string;
  valor_uvr_fecha_extracto: string;
  valor_cuota_uvr: string;
  seguro_vida: string;
  seguro_incendio: string;
  seguro_terremoto: string;
  capital_pagado_periodo: string;
  intereses_corrientes_periodo: string;
  intereses_mora: string;
  otros_cargos: string;
  password: string;
}

const INITIAL_FORM: FormState = {
  customer_full_name: '',
  customer_id_number: '',
  customer_email: '',
  customer_phone: '',
  ingresos_mensuales: '',
  capacidad_pago_max: '',
  tipo_contrato_laboral: 'Indefinido',
  banco_id: '',
  opcion_abono_1: '200000',
  opcion_abono_2: '300000',
  opcion_abono_3: '400000',
  numero_credito: '',
  sistema_amortizacion: 'PESOS',
  plan_credito: '',
  valor_prestado_inicial: '',
  fecha_desembolso: '',
  fecha_extracto: '',
  plazo_total_meses: '',
  cuotas_pactadas: '',
  cuotas_pagadas: '',
  cuotas_pendientes: '',
  tasa_interes_pactada_ea: '',
  tasa_interes_cobrada_ea: '',
  tasa_interes_subsidiada_ea: '',
  tasa_mora_pactada_ea: '',
  valor_cuota_sin_seguros: '',
  valor_cuota_con_seguros: '',
  beneficio_frech_mensual: '',
  valor_cuota_con_subsidio: '',
  saldo_capital_pesos: '',
  total_por_pagar: '',
  saldo_capital_uvr: '',
  valor_uvr_fecha_extracto: '',
  valor_cuota_uvr: '',
  seguro_vida: '',
  seguro_incendio: '',
  seguro_terremoto: '',
  capital_pagado_periodo: '',
  intereses_corrientes_periodo: '',
  intereses_mora: '',
  otros_cargos: '',
  password: '',
};

const MONEY_FIELDS = new Set<keyof FormState>([
  'ingresos_mensuales', 'capacidad_pago_max', 'opcion_abono_1', 'opcion_abono_2', 'opcion_abono_3',
  'valor_prestado_inicial', 'tasa_interes_pactada_ea', 'tasa_interes_cobrada_ea', 'tasa_interes_subsidiada_ea',
  'tasa_mora_pactada_ea', 'valor_cuota_sin_seguros', 'valor_cuota_con_seguros', 'beneficio_frech_mensual',
  'valor_cuota_con_subsidio', 'saldo_capital_pesos', 'total_por_pagar', 'saldo_capital_uvr',
  'valor_uvr_fecha_extracto', 'valor_cuota_uvr', 'seguro_vida', 'seguro_incendio', 'seguro_terremoto',
  'capital_pagado_periodo', 'intereses_corrientes_periodo', 'intereses_mora', 'otros_cargos',
]);

const INTEGER_FIELDS = new Set<keyof FormState>([
  'plazo_total_meses', 'cuotas_pactadas', 'cuotas_pagadas', 'cuotas_pendientes',
]);

const DIGIT_ONLY_MONEY_FIELDS = new Set<keyof FormState>([
  'ingresos_mensuales',
  'capacidad_pago_max',
]);

export default function AdminManualProjectionPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isRoleLoading, setIsRoleLoading] = useState(true);
  const [banks, setBanks] = useState<Array<{ id: number; nombre: string }>>([]);
  const [file, setFile] = useState<File | null>(null);
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
        const banksList = await apiClient.getBanks();
        setBanks(banksList);
      } catch {
        router.replace('/auth/login');
      } finally {
        setIsRoleLoading(false);
      }
    };

    bootstrap();
  }, [router]);

  const canSubmit = useMemo(() => {
    return !!(
      file &&
      form.customer_full_name.trim() &&
      form.customer_id_number.trim() &&
      form.customer_email.trim() &&
      form.customer_phone.trim() &&
      form.banco_id &&
      form.numero_credito.trim() &&
      form.valor_prestado_inicial.trim() &&
      form.valor_cuota_con_seguros.trim() &&
      form.saldo_capital_pesos.trim() &&
      form.tasa_interes_cobrada_ea.trim() &&
      form.cuotas_pendientes.trim() &&
      form.fecha_extracto.trim() &&
      form.plazo_total_meses.trim() &&
      form.cuotas_pactadas.trim()
    );
  }, [file, form]);

  const updateField = (field: keyof FormState, value: string) => {
    if (INTEGER_FIELDS.has(field)) {
      setForm((prev) => ({ ...prev, [field]: cleanDigitsInput(value) }));
      return;
    }
    if (DIGIT_ONLY_MONEY_FIELDS.has(field)) {
      setForm((prev) => ({ ...prev, [field]: cleanDigitsInput(value) }));
      return;
    }
    if (MONEY_FIELDS.has(field)) {
      setForm((prev) => ({ ...prev, [field]: formatMonetaryInput(value) }));
      return;
    }
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const monetary = (value: string) => parseMonetaryInput(value);
  const integer = (value: string) => {
    const digits = cleanDigitsInput(value);
    return digits ? Number(digits) : undefined;
  };

  const toOptionalNumber = (value: string) => {
    const parsed = monetary(value);
    return parsed === null ? undefined : parsed;
  };

  const toOptionalDigitsNumber = (value: string) => {
    const digits = cleanDigitsInput(value);
    return digits ? Number(digits) : undefined;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      toast.error('Debes seleccionar un PDF');
      return;
    }

    const ingresos = toOptionalDigitsNumber(form.ingresos_mensuales);
    const prestado = monetary(form.valor_prestado_inicial);
    const cuota = monetary(form.valor_cuota_con_seguros);
    const saldo = monetary(form.saldo_capital_pesos);
    const tasa = monetary(form.tasa_interes_cobrada_ea);

    if (!ingresos || !prestado || !cuota || !saldo || !tasa) {
      toast.error('Completa los campos financieros obligatorios');
      return;
    }

    const plazo = integer(form.plazo_total_meses);
    const cuotasPactadas = integer(form.cuotas_pactadas);
    const cuotasPagadas = integer(form.cuotas_pagadas) || 0;
    const cuotasPendientes = integer(form.cuotas_pendientes);

    if (!plazo || !cuotasPactadas || cuotasPendientes === undefined) {
      toast.error('Completa los campos de cuotas y plazo');
      return;
    }

    try {
      setSubmitting(true);
      const result = await apiClient.createAdminManualProjection({
        customer_full_name: form.customer_full_name.trim(),
        customer_id_number: form.customer_id_number.trim(),
        customer_email: form.customer_email.trim(),
        customer_phone: form.customer_phone.trim(),
        ingresos_mensuales: ingresos,
        capacidad_pago_max: toOptionalDigitsNumber(form.capacidad_pago_max),
        tipo_contrato_laboral: form.tipo_contrato_laboral,
        banco_id: Number(form.banco_id),
        opcion_abono_1: toOptionalNumber(form.opcion_abono_1),
        opcion_abono_2: toOptionalNumber(form.opcion_abono_2),
        opcion_abono_3: toOptionalNumber(form.opcion_abono_3),
        numero_credito: form.numero_credito.trim(),
        sistema_amortizacion: form.sistema_amortizacion,
        plan_credito: form.plan_credito.trim() || undefined,
        valor_prestado_inicial: prestado,
        fecha_desembolso: form.fecha_desembolso || undefined,
        fecha_extracto: form.fecha_extracto,
        plazo_total_meses: plazo,
        cuotas_pactadas: cuotasPactadas,
        cuotas_pagadas: cuotasPagadas,
        cuotas_pendientes: cuotasPendientes,
        tasa_interes_pactada_ea: toOptionalNumber(form.tasa_interes_pactada_ea),
        tasa_interes_cobrada_ea: tasa,
        tasa_interes_subsidiada_ea: toOptionalNumber(form.tasa_interes_subsidiada_ea),
        tasa_mora_pactada_ea: toOptionalNumber(form.tasa_mora_pactada_ea),
        valor_cuota_sin_seguros: toOptionalNumber(form.valor_cuota_sin_seguros),
        valor_cuota_con_seguros: cuota,
        beneficio_frech_mensual: toOptionalNumber(form.beneficio_frech_mensual),
        valor_cuota_con_subsidio: toOptionalNumber(form.valor_cuota_con_subsidio),
        saldo_capital_pesos: saldo,
        total_por_pagar: toOptionalNumber(form.total_por_pagar),
        saldo_capital_uvr: toOptionalNumber(form.saldo_capital_uvr),
        valor_uvr_fecha_extracto: toOptionalNumber(form.valor_uvr_fecha_extracto),
        valor_cuota_uvr: toOptionalNumber(form.valor_cuota_uvr),
        seguro_vida: toOptionalNumber(form.seguro_vida),
        seguro_incendio: toOptionalNumber(form.seguro_incendio),
        seguro_terremoto: toOptionalNumber(form.seguro_terremoto),
        capital_pagado_periodo: toOptionalNumber(form.capital_pagado_periodo),
        intereses_corrientes_periodo: toOptionalNumber(form.intereses_corrientes_periodo),
        intereses_mora: toOptionalNumber(form.intereses_mora),
        otros_cargos: toOptionalNumber(form.otros_cargos),
        file,
        password: form.password.trim() || undefined,
      });

      if (!result.success || !result.analisis_id) {
        toast.error(result.message || 'No se pudo crear el análisis manual');
        return;
      }

      toast.success('Proyección manual creada correctamente');
      router.push(`/dashboard/admin/proyecciones/${result.analisis_id}`);
    } catch (error: unknown) {
      const parsed = error as { message?: string; detail?: { requires_password?: boolean; message?: string } | string };
      const detail = parsed?.detail;
      if (detail && typeof detail === 'object' && detail.requires_password) {
        toast.error(detail.message || 'El PDF tiene contraseña. Ingresa la contraseña para continuar.');
      } else if (typeof detail === 'string' && detail.trim().length > 0) {
        toast.error(detail);
      } else {
        toast.error(parsed?.message || 'No se pudo crear la proyección manual');
      }
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
        <p className="text-sm text-gray-600">Carga el PDF y completa manualmente toda la información del crédito para generar proyecciones.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800">Datos del cliente</h2>
          </CardHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Nombre completo *" value={form.customer_full_name} onChange={(e) => updateField('customer_full_name', e.target.value)} required />
            <Input label="Cédula *" value={form.customer_id_number} onChange={(e) => updateField('customer_id_number', cleanDigitsInput(e.target.value))} required />
            <Input label="Email *" type="email" value={form.customer_email} onChange={(e) => updateField('customer_email', e.target.value)} required />
            <Input label="Teléfono *" value={form.customer_phone} onChange={(e) => updateField('customer_phone', cleanDigitsInput(e.target.value))} required />
          </div>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800">Archivo y configuración</h2>
          </CardHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold ml-1 text-verde-bosque">Banco *</label>
              <select className="w-full px-4 py-2.5 border border-gray-300 rounded-xl" value={form.banco_id} onChange={(e) => updateField('banco_id', e.target.value)} required>
                <option value="">Selecciona</option>
                {banks.map((bank) => <option key={bank.id} value={bank.id}>{bank.nombre}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold ml-1 text-verde-bosque">Tipo de Contrato *</label>
              <div className="relative">
                <BriefcaseBusiness size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <select
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl bg-white"
                  value={form.tipo_contrato_laboral}
                  onChange={(e) => updateField('tipo_contrato_laboral', e.target.value)}
                >
                  <option value="Indefinido">Indefinido</option>
                  <option value="Término fijo">Término fijo</option>
                  <option value="Independiente">Independiente</option>
                  <option value="Prestación de servicios">Prestación de servicios</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>
            </div>
            <Input label="Ingresos mensuales *" inputMode="numeric" value={formatDigitsInput(form.ingresos_mensuales)} onChange={(e) => updateField('ingresos_mensuales', e.target.value)} required />
            <Input label="Capacidad de pago" inputMode="numeric" value={formatDigitsInput(form.capacidad_pago_max)} onChange={(e) => updateField('capacidad_pago_max', e.target.value)} />
            <Input label="Abono opción 1" inputMode="decimal" value={form.opcion_abono_1} onChange={(e) => updateField('opcion_abono_1', e.target.value)} />
            <Input label="Abono opción 2" inputMode="decimal" value={form.opcion_abono_2} onChange={(e) => updateField('opcion_abono_2', e.target.value)} />
            <Input label="Abono opción 3" inputMode="decimal" value={form.opcion_abono_3} onChange={(e) => updateField('opcion_abono_3', e.target.value)} />
            <Input label="Contraseña PDF (si aplica)" type="password" value={form.password} onChange={(e) => updateField('password', e.target.value)} />
          </div>
          <div className="mt-4 rounded-xl border border-dashed border-gray-300 p-4 bg-gray-50">
            <label className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-2"><FileText size={16} /> PDF del crédito *</label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm"
              required
            />
            {file && <p className="text-xs text-gray-500 mt-2">Archivo: {file.name}</p>}
          </div>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-800">Datos del crédito (manual completo)</h2>
          </CardHeader>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input label="Número crédito *" value={form.numero_credito} onChange={(e) => updateField('numero_credito', e.target.value)} required />
            <div className="space-y-1.5">
              <label className="text-sm font-semibold ml-1 text-verde-bosque">Sistema amortización *</label>
              <select className="w-full px-4 py-2.5 border border-gray-300 rounded-xl" value={form.sistema_amortizacion} onChange={(e) => updateField('sistema_amortizacion', e.target.value)}>
                <option value="PESOS">PESOS</option>
                <option value="UVR">UVR</option>
              </select>
            </div>
            <Input label="Plan crédito" value={form.plan_credito} onChange={(e) => updateField('plan_credito', e.target.value)} />
            <Input label="Valor prestado inicial *" inputMode="decimal" value={form.valor_prestado_inicial} onChange={(e) => updateField('valor_prestado_inicial', e.target.value)} required />
            <Input label="Fecha desembolso" type="date" value={form.fecha_desembolso} onChange={(e) => updateField('fecha_desembolso', e.target.value)} />
            <Input label="Fecha extracto *" type="date" value={form.fecha_extracto} onChange={(e) => updateField('fecha_extracto', e.target.value)} required />
            <Input label="Plazo total meses *" inputMode="numeric" value={formatDigitsInput(form.plazo_total_meses)} onChange={(e) => updateField('plazo_total_meses', e.target.value)} required />
            <Input label="Cuotas pactadas *" inputMode="numeric" value={formatDigitsInput(form.cuotas_pactadas)} onChange={(e) => updateField('cuotas_pactadas', e.target.value)} required />
            <Input label="Cuotas pagadas" inputMode="numeric" value={formatDigitsInput(form.cuotas_pagadas)} onChange={(e) => updateField('cuotas_pagadas', e.target.value)} />
            <Input label="Cuotas pendientes *" inputMode="numeric" value={formatDigitsInput(form.cuotas_pendientes)} onChange={(e) => updateField('cuotas_pendientes', e.target.value)} required />
            <Input label="Tasa pactada EA" inputMode="decimal" value={form.tasa_interes_pactada_ea} onChange={(e) => updateField('tasa_interes_pactada_ea', e.target.value)} />
            <Input label="Tasa cobrada EA *" inputMode="decimal" value={form.tasa_interes_cobrada_ea} onChange={(e) => updateField('tasa_interes_cobrada_ea', e.target.value)} required />
            <Input label="Tasa subsidiada EA" inputMode="decimal" value={form.tasa_interes_subsidiada_ea} onChange={(e) => updateField('tasa_interes_subsidiada_ea', e.target.value)} />
            <Input label="Tasa mora EA" inputMode="decimal" value={form.tasa_mora_pactada_ea} onChange={(e) => updateField('tasa_mora_pactada_ea', e.target.value)} />
            <Input label="Cuota sin seguros" inputMode="decimal" value={form.valor_cuota_sin_seguros} onChange={(e) => updateField('valor_cuota_sin_seguros', e.target.value)} />
            <Input label="Cuota con seguros *" inputMode="decimal" value={form.valor_cuota_con_seguros} onChange={(e) => updateField('valor_cuota_con_seguros', e.target.value)} required />
            <Input label="Beneficio FRECH" inputMode="decimal" value={form.beneficio_frech_mensual} onChange={(e) => updateField('beneficio_frech_mensual', e.target.value)} />
            <Input label="Cuota con subsidio" inputMode="decimal" value={form.valor_cuota_con_subsidio} onChange={(e) => updateField('valor_cuota_con_subsidio', e.target.value)} />
            <Input label="Saldo capital pesos *" inputMode="decimal" value={form.saldo_capital_pesos} onChange={(e) => updateField('saldo_capital_pesos', e.target.value)} required />
            <Input label="Total por pagar" inputMode="decimal" value={form.total_por_pagar} onChange={(e) => updateField('total_por_pagar', e.target.value)} />
            <Input label="Saldo capital UVR" inputMode="decimal" value={form.saldo_capital_uvr} onChange={(e) => updateField('saldo_capital_uvr', e.target.value)} />
            <Input label="Valor UVR fecha" inputMode="decimal" value={form.valor_uvr_fecha_extracto} onChange={(e) => updateField('valor_uvr_fecha_extracto', e.target.value)} />
            <Input label="Valor cuota UVR" inputMode="decimal" value={form.valor_cuota_uvr} onChange={(e) => updateField('valor_cuota_uvr', e.target.value)} />
            <Input label="Seguro vida" inputMode="decimal" value={form.seguro_vida} onChange={(e) => updateField('seguro_vida', e.target.value)} />
            <Input label="Seguro incendio" inputMode="decimal" value={form.seguro_incendio} onChange={(e) => updateField('seguro_incendio', e.target.value)} />
            <Input label="Seguro terremoto" inputMode="decimal" value={form.seguro_terremoto} onChange={(e) => updateField('seguro_terremoto', e.target.value)} />
            <Input label="Capital pagado periodo" inputMode="decimal" value={form.capital_pagado_periodo} onChange={(e) => updateField('capital_pagado_periodo', e.target.value)} />
            <Input label="Intereses corrientes" inputMode="decimal" value={form.intereses_corrientes_periodo} onChange={(e) => updateField('intereses_corrientes_periodo', e.target.value)} />
            <Input label="Intereses mora" inputMode="decimal" value={form.intereses_mora} onChange={(e) => updateField('intereses_mora', e.target.value)} />
            <Input label="Otros cargos" inputMode="decimal" value={form.otros_cargos} onChange={(e) => updateField('otros_cargos', e.target.value)} />
          </div>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" leftIcon={<PlusCircle size={16} />} isLoading={submitting} disabled={!canSubmit || submitting}>
            Guardar y abrir proyecciones
          </Button>
        </div>
      </form>

      <Card className="border-amber-200 bg-amber-50">
        <div className="p-3 text-sm text-amber-800 flex items-center gap-2">
          <AlertTriangle size={16} />
          Esta opción es exclusiva para administradores y marcará el análisis como <strong>D.E. manualmente</strong> en el historial.
        </div>
      </Card>
    </div>
  );
}
