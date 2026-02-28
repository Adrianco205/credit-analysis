'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'sonner';
import { Upload, FileText, User, Mail, CreditCard, DollarSign, BriefcaseBusiness, Phone, Loader2 } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cleanDigitsInput, formatDigitsInput } from '@/lib/utils';

export default function AdminClientUploadAnalysisPage() {
  const router = useRouter();

  const [creditType] = useState('Hipotecario');
  const [customerFullName, setCustomerFullName] = useState('');
  const [customerIdNumber, setCustomerIdNumber] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');

  const [income, setIncome] = useState('');
  const [paymentCapacity, setPaymentCapacity] = useState('');
  const [contractType, setContractType] = useState('Indefinido');
  const [option1, setOption1] = useState('200000');
  const [option2, setOption2] = useState('300000');
  const [option3, setOption3] = useState('400000');

  const [banks, setBanks] = useState<Array<{ id: number; nombre: string }>>([]);
  const [bankId, setBankId] = useState<number | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [pdfPassword, setPdfPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showLoadingOverlay, setShowLoadingOverlay] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [allowLoadingFinish, setAllowLoadingFinish] = useState(false);

  const loadingCompletionResolverRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const loadBanks = async () => {
      try {
        const banksList = await apiClient.getBanks();
        setBanks(banksList);
      } catch {
        toast.error('No se pudo cargar la lista de bancos');
      }
    };

    loadBanks();
  }, []);

  useEffect(() => {
    if (!showLoadingOverlay) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setLoadingProgress((prev) => {
        const target = allowLoadingFinish ? 100 : 80;

        if (!allowLoadingFinish && prev >= 80) {
          return 80;
        }

        if (prev >= 100) {
          return 100;
        }

        const remaining = target - prev;
        const easeFactor = allowLoadingFinish ? 0.42 : 0.05;
        const minimumStep = allowLoadingFinish ? 4.2 : 0.18;
        const organicVariance = allowLoadingFinish ? 0 : Math.random() * 0.16;
        const next = prev + Math.max(minimumStep, remaining * easeFactor) + organicVariance;

        return Math.min(target, next);
      });
    }, 240);

    return () => window.clearInterval(intervalId);
  }, [showLoadingOverlay, allowLoadingFinish]);

  useEffect(() => {
    if (!showLoadingOverlay || !allowLoadingFinish || loadingProgress < 99.8) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setShowLoadingOverlay(false);
      setAllowLoadingFinish(false);
      setLoadingProgress(0);

      if (loadingCompletionResolverRef.current) {
        loadingCompletionResolverRef.current();
        loadingCompletionResolverRef.current = null;
      }
    }, 220);

    return () => window.clearTimeout(timeoutId);
  }, [showLoadingOverlay, allowLoadingFinish, loadingProgress]);

  const startLoadingOverlay = () => {
    setLoadingProgress(0);
    setAllowLoadingFinish(false);
    setShowLoadingOverlay(true);
  };

  const completeLoadingOverlay = () => {
    setAllowLoadingFinish(true);

    return new Promise<void>((resolve) => {
      loadingCompletionResolverRef.current = resolve;

      window.setTimeout(() => {
        if (loadingCompletionResolverRef.current) {
          setShowLoadingOverlay(false);
          setAllowLoadingFinish(false);
          setLoadingProgress(0);
          loadingCompletionResolverRef.current();
          loadingCompletionResolverRef.current = null;
        }
      }, 4000);
    });
  };

  const resetLoadingOverlay = () => {
    setShowLoadingOverlay(false);
    setAllowLoadingFinish(false);
    setLoadingProgress(0);

    if (loadingCompletionResolverRef.current) {
      loadingCompletionResolverRef.current();
      loadingCompletionResolverRef.current = null;
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] || null;
    if (!selected) return;

    if (selected.type !== 'application/pdf') {
      toast.error('Solo se permiten archivos PDF');
      return;
    }

    setFile(selected);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const selected = event.dataTransfer.files?.[0] || null;
    if (!selected) return;

    if (selected.type !== 'application/pdf') {
      toast.error('Solo se permiten archivos PDF');
      return;
    }

    setFile(selected);
  };

  const handleSubmit = async () => {
    if (!customerFullName.trim()) {
      toast.error('Debes ingresar el nombre completo del cliente');
      return;
    }
    if (!customerIdNumber.trim()) {
      toast.error('Debes ingresar la cédula del cliente');
      return;
    }
    if (!customerEmail.trim()) {
      toast.error('Debes ingresar el correo del cliente');
      return;
    }
    if (!customerPhone.trim()) {
      toast.error('Debes ingresar el teléfono del cliente');
      return;
    }
    if (!income || Number(income) <= 0) {
      toast.error('Debes ingresar ingresos mensuales válidos');
      return;
    }
    if (!paymentCapacity || Number(paymentCapacity) <= 0) {
      toast.error('Debes ingresar una capacidad de pago válida');
      return;
    }
    if (!bankId) {
      toast.error('Debes seleccionar el banco del crédito');
      return;
    }
    if (!file) {
      toast.error('Debes seleccionar un archivo PDF');
      return;
    }

    setSubmitting(true);
    startLoadingOverlay();
    try {
      const result = await apiClient.createAdminClientAnalysis({
        customer_full_name: customerFullName.trim(),
        customer_id_number: customerIdNumber.trim(),
        customer_email: customerEmail.trim(),
        customer_phone: customerPhone.trim(),
        ingresos_mensuales: Number(income),
        capacidad_pago_max: Number(paymentCapacity),
        tipo_contrato_laboral: contractType,
        banco_id: bankId,
        opcion_abono_1: Number(option1 || 0) || undefined,
        opcion_abono_2: Number(option2 || 0) || undefined,
        opcion_abono_3: Number(option3 || 0) || undefined,
        file,
        password: pdfPassword || undefined,
      });

      if (!result.success || !result.analisis_id) {
        throw new Error(result.message || 'No se pudo crear el análisis');
      }

      if (result.requires_manual_input) {
        await completeLoadingOverlay();
        toast.warning('Faltan datos para proyectar. Completa la calculadora manual del análisis.');
        router.push(`/dashboard/admin/analyses/${result.analisis_id}/manual`);
        return;
      }

      await completeLoadingOverlay();
      toast.success('Análisis del cliente creado y guardado exitosamente');
      router.push(`/dashboard/admin/analyses/${result.analisis_id}`);
    } catch (error: unknown) {
      resetLoadingOverlay();
      const parsed = error as { message?: string; detail?: { message?: string } | string };
      if (typeof parsed?.detail === 'string' && parsed.detail) {
        toast.error(parsed.detail);
      } else if (typeof parsed?.detail === 'object' && parsed.detail?.message) {
        toast.error(parsed.detail.message);
      } else {
        toast.error(parsed?.message || 'No se pudo subir y analizar el documento');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Subir análisis de clientes</h1>

        <Card className="border-t-4 border-[var(--verde-hoja)]">
          <CardHeader>
            <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
              <User className="text-[var(--verde-hoja)]" />
              Datos del cliente
            </h2>
          </CardHeader>

        <div className="space-y-5 p-6 pt-0">
          <div className="w-full flex flex-col gap-1.5">
            <label className="block text-sm font-semibold text-gray-700 ml-1">Tipo de Crédito *</label>
            <select
              className="w-full px-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl bg-white"
              value={creditType}
              disabled
            >
              <option value="Hipotecario">Crédito Hipotecario</option>
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Input
              label="Nombre completo del cliente *"
              value={customerFullName}
              onChange={(e) => setCustomerFullName(e.target.value)}
              leftIcon={<User size={18} />}
              placeholder="Ej: Juan David Pérez Gómez"
              required
            />
            <Input
              label="Cédula del cliente *"
              value={customerIdNumber}
              onChange={(e) => setCustomerIdNumber(e.target.value)}
              leftIcon={<CreditCard size={18} />}
              placeholder="Ej: 1020304050"
              required
            />
            <Input
              label="Correo del cliente *"
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              leftIcon={<Mail size={18} />}
              placeholder="cliente@correo.com"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Input
              label="Teléfono del cliente *"
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              leftIcon={<Phone size={18} />}
              placeholder="Ej: 3001234567"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Input
              label="Ingresos Mensuales (COP) *"
              inputMode="numeric"
              value={formatDigitsInput(income)}
              onChange={(e) => setIncome(cleanDigitsInput(e.target.value))}
              leftIcon={<DollarSign size={18} />}
              placeholder="Ej: 5.000.000"
              required
            />
            <Input
              label="Capacidad de Pago Máxima (COP) *"
              inputMode="numeric"
              value={formatDigitsInput(paymentCapacity)}
              onChange={(e) => setPaymentCapacity(cleanDigitsInput(e.target.value))}
              leftIcon={<DollarSign size={18} />}
              placeholder="Ej: 1.500.000"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="w-full flex flex-col gap-1.5">
              <label className="block text-sm font-semibold text-gray-700 ml-1">Tipo de Contrato *</label>
              <div className="relative">
                <BriefcaseBusiness size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <select
                  className="w-full pl-10 pr-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl bg-white"
                  value={contractType}
                  onChange={(e) => setContractType(e.target.value)}
                >
                  <option value="Indefinido">Indefinido</option>
                  <option value="Término fijo">Término fijo</option>
                  <option value="Independiente">Independiente</option>
                  <option value="Prestación de servicios">Prestación de servicios</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>
            </div>

            <div className="w-full flex flex-col gap-1.5">
              <label className="block text-sm font-semibold text-gray-700 ml-1">Banco del crédito *</label>
              <select
                className="w-full px-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl bg-white"
                value={bankId || ''}
                onChange={(e) => setBankId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Selecciona un banco</option>
                {banks.map((bank) => (
                  <option key={bank.id} value={bank.id}>
                    {bank.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="bg-[var(--gray-50)] p-4 rounded-xl border border-gray-200">
            <h3 className="font-semibold text-gray-700 mb-3 text-sm">Opciones de simulación</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Input
                label="Opción 1"
                inputMode="numeric"
                value={formatDigitsInput(option1)}
                onChange={(e) => setOption1(cleanDigitsInput(e.target.value))}
              />
              <Input
                label="Opción 2"
                inputMode="numeric"
                value={formatDigitsInput(option2)}
                onChange={(e) => setOption2(cleanDigitsInput(e.target.value))}
              />
              <Input
                label="Opción 3"
                inputMode="numeric"
                value={formatDigitsInput(option3)}
                onChange={(e) => setOption3(cleanDigitsInput(e.target.value))}
              />
            </div>
          </div>
        </div>
        </Card>

        <Card className="border-t-4 border-blue-500">
          <CardHeader>
            <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
              <Upload className="text-blue-500" />
              Documento del cliente
            </h2>
          </CardHeader>

        <div className="space-y-5 p-6 pt-0">
          <div
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-colors cursor-pointer ${
              file ? 'border-[var(--verde-hoja)] bg-[var(--verde-suave)]' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
            }`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => document.getElementById('admin-client-upload-pdf')?.click()}
          >
            <input
              id="admin-client-upload-pdf"
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={handleFileChange}
            />

            {file ? (
              <div className="space-y-2">
                <FileText size={48} className="mx-auto text-[var(--verde-hoja)]" />
                <p className="font-semibold text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload size={48} className="mx-auto text-gray-400" />
                <p className="font-medium text-gray-700">Arrastra el PDF aquí o haz click para buscar</p>
                <p className="text-xs text-gray-400">No se restringen documentos repetidos para clientes</p>
              </div>
            )}
          </div>

          <Input
            label="Contraseña del PDF (opcional)"
            type="password"
            value={pdfPassword}
            onChange={(e) => setPdfPassword(e.target.value)}
            placeholder="Ingresa la clave si el PDF está protegido"
            showPasswordToggle
          />

          <Button
            onClick={handleSubmit}
            variant="primary"
            className="w-full py-4 text-lg"
            isLoading={submitting}
            disabled={submitting || !file}
          >
            Subir y Guardar Análisis
          </Button>
        </div>
        </Card>
      </div>

      <AnimatePresence>
        {showLoadingOverlay && (
          <AdminAnalysisLoadingOverlay
            progress={loadingProgress}
            statusText={getLoadingStatusText(loadingProgress, allowLoadingFinish)}
          />
        )}
      </AnimatePresence>
    </>
  );
}

function getLoadingStatusText(progress: number, allowLoadingFinish: boolean) {
  if (allowLoadingFinish || progress >= 80) {
    return 'Finalizando análisis...';
  }

  if (progress < 30) {
    return 'Subiendo documento...';
  }

  if (progress < 60) {
    return 'Extrayendo datos financieros...';
  }

  return 'Guardando análisis...';
}

function AdminAnalysisLoadingOverlay({ progress, statusText }: { progress: number; statusText: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[60] bg-black/45 backdrop-blur-sm pointer-events-auto"
    >
      <div className="h-full w-full flex items-center justify-center px-4">
        <motion.div
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 6, opacity: 0 }}
          className="w-full max-w-xl rounded-xl bg-white shadow-xl border border-gray-200 p-6 sm:p-7"
        >
          <div className="space-y-4">
            <div className="space-y-1">
              <p className="text-sm font-medium text-gray-600">{statusText}</p>
              <h3 className="text-xl font-semibold text-[var(--verde-bosque)]">Procesando análisis del cliente</h3>
            </div>

            <div className="h-3 w-full rounded-full bg-gray-200 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-[var(--verde-hoja)]"
                animate={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
              />
            </div>

            <div className="flex justify-between items-center text-xs text-gray-500">
              <span>No cierres esta ventana. Estamos guardando el análisis.</span>
              <span className="font-semibold text-[var(--verde-bosque)]">{Math.round(progress)}%</span>
            </div>

            <div className="flex items-center justify-center gap-2 text-gray-500 text-sm pt-1">
              <Loader2 size={16} className="animate-spin" />
              <span>Un momento por favor...</span>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

