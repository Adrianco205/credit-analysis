'use client';

import { useEffect, useState, useRef, useCallback, type ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { apiClient } from '@/lib/api-client';
import { UserProfile, AnalysisSummary } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader } from '@/components/ui/card';
import { toast } from 'sonner';
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/build/pdf.mjs';
import { 
    FileText, 
    Upload, 
    CheckCircle2, 
    CreditCard, 
    User, 
    DollarSign,
    Calendar,
    ArrowRight,
    Loader2,
    Lock,
    X
} from 'lucide-react';

GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
).toString();

export default function CreditAnalysisUploadPage() {
        const isPdfPasswordException = (error: unknown) => {
            if (!error || typeof error !== 'object') return false;
            const errObj = error as { name?: string; code?: number };
            return errObj.name === 'PasswordException' || errObj.code === 1 || errObj.code === 2;
        };

        const parseApiError = (error: unknown) => {
            if (!error || typeof error !== 'object') return null;
            return error as { message?: string; error?: string; status_code?: number };
        };

    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [step, setStep] = useState(1); // 1: Info Financiera, 2: Upload, 3: Success

    // Section 1: Financial Info
    const [creditType, setCreditType] = useState('Hipotecario');
    const [income, setIncome] = useState('');
    const [paymentCapacity, setPaymentCapacity] = useState('');
    const [contractType, setContractType] = useState('Indefinido');
    const [option1, setOption1] = useState('200000');
    const [option2, setOption2] = useState('300000');
    const [option3, setOption3] = useState('400000');

    // Section 2: Upload
    const [file, setFile] = useState<File | null>(null);
    const [banks, setBanks] = useState<Array<{ id: number; nombre: string }>>([]);
    const [bankId, setBankId] = useState<number | null>(null);
    const [pdfPassword, setPdfPassword] = useState('');
    const [pdfRequiresPassword, setPdfRequiresPassword] = useState(false);
    const [pdfPasswordError, setPdfPasswordError] = useState('');
    const [checkingPdf, setCheckingPdf] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [analysisId, setAnalysisId] = useState<string | null>(null);
    const [summaryData, setSummaryData] = useState<AnalysisSummary | null>(null);
    const [monthlyDuplicateWarning, setMonthlyDuplicateWarning] = useState(false);
    const [showContactModal, setShowContactModal] = useState(false);
    const [showIdentityMismatchModal, setShowIdentityMismatchModal] = useState(false);
    const [identityMismatchMessage, setIdentityMismatchMessage] = useState('');
    const [contactPhone, setContactPhone] = useState('');
    const [savingContact, setSavingContact] = useState(false);
    const [showLoadingOverlay, setShowLoadingOverlay] = useState(false);
    const [loadingProgress, setLoadingProgress] = useState(0);
    const [allowLoadingFinish, setAllowLoadingFinish] = useState(false);

    const COLOMBIA_MOBILE_REGEX = /^3\d{9}$/;

    const nextUploadAvailability = getNextUploadAvailability();

    const fileInputRef = useRef<HTMLInputElement>(null);
    const loadingCompletionResolverRef = useRef<(() => void) | null>(null);
    const analysisCompletedSectionRef = useRef<HTMLDivElement>(null);

    const getErrorMessage = (error: unknown) => {
        if (error && typeof error === 'object') {
            const raw = error as Record<string, unknown>;
            const statusCode = Number(raw.status_code || 0);
            if (statusCode === 503) {
                return 'El servicio de extracción está temporalmente ocupado. Intenta nuevamente en unos segundos.';
            }

            const detail = raw.detail;

            if (typeof detail === 'string' && detail.trim().length > 0 && detail !== '{}') {
                return detail;
            }

            if (detail && typeof detail === 'object') {
                const detailObj = detail as Record<string, unknown>;
                if (typeof detailObj.message === 'string' && detailObj.message.trim().length > 0) {
                    return detailObj.message;
                }
            }

            if (typeof raw.message === 'string' && raw.message.trim().length > 0 && raw.message !== '{}') {
                return raw.message;
            }
        }

        if (error instanceof Error && error.message && error.message.trim().length > 0) {
            return error.message;
        }

        return 'Ocurrió un error en el proceso. Intenta nuevamente en unos segundos.';
    };

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

    useEffect(() => {
        if (step !== 3) {
            return;
        }

        const timeoutId = window.setTimeout(() => {
            analysisCompletedSectionRef.current?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
            });
        }, 120);

        return () => window.clearTimeout(timeoutId);
    }, [step, analysisId]);

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

    const loadBanks = useCallback(async () => {
        try {
            const banksList = await apiClient.getBanks();
            setBanks(banksList);
        } catch (err) {
            console.error('Error loading banks:', err);
        }
    }, []);

    const loadProfile = useCallback(async () => {
        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                router.push('/auth/login');
                return;
            }
            const u = await apiClient.getProfile();
            setUser(u);
            setContactPhone((u.telefono || '').replace(/\D/g, '').slice(0, 10));
        } catch (err: unknown) {
            const parsedError = parseApiError(err);
            console.error('Error loading profile:', parsedError?.message || parsedError?.error || JSON.stringify(err));
            if (parsedError?.status_code === 401) {
                router.push('/auth/login');
                return;
            }
        } finally {
            setLoading(false);
        }
    }, [router]);

    useEffect(() => {
        loadProfile();
        loadBanks();
    }, [loadBanks, loadProfile]);

    // --- Steps Logic ---

    const handleStep1Submit = (e: React.FormEvent) => {
        e.preventDefault();
        
        // Basic validation
        if (!income || Number(income) <= 0) {
            toast.error("Por favor ingresa unos ingresos válidos");
            return;
        }
        if (!paymentCapacity || Number(paymentCapacity) <= 0) {
            toast.error("Por favor ingresa una capacidad de pago válida");
            return;
        }
        
        // Move to step 2
        setStep(2);
        toast.success("Información financiera guardada temporalmente");
    };

    // --- File Handling ---
    
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            if (selectedFile.type !== 'application/pdf') {
                toast.error("Solo se permiten archivos PDF");
                return;
            }
            setFile(selectedFile);
            setMonthlyDuplicateWarning(false);
            setPdfPassword('');
            setPdfPasswordError('');
            checkPdfEncryption(selectedFile);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
             const selectedFile = e.dataTransfer.files[0];
             if (selectedFile.type !== 'application/pdf') {
                toast.error("Solo se permiten archivos PDF");
                return;
            }
            setFile(selectedFile);
            setMonthlyDuplicateWarning(false);
            setPdfPassword('');
            setPdfPasswordError('');
            checkPdfEncryption(selectedFile);
        }
    };

    const checkPdfEncryption = async (selectedFile: File) => {
        setCheckingPdf(true);
        setPdfRequiresPassword(false);
        try {
            const buffer = await selectedFile.arrayBuffer();
            await getDocument({ data: buffer, password: '' }).promise;
            setPdfRequiresPassword(false);
        } catch (err: unknown) {
            const isPasswordError = isPdfPasswordException(err);
            if (isPasswordError) {
                setPdfRequiresPassword(true);
                return;
            }
            setFile(null);
            toast.error('No se pudo leer el PDF. Verifica que sea valido.');
        } finally {
            setCheckingPdf(false);
        }
    };

    const verifyPdfPassword = async (selectedFile: File, password: string) => {
        const buffer = await selectedFile.arrayBuffer();
        try {
            await getDocument({ data: buffer, password }).promise;
            return true;
        } catch (err: unknown) {
            const isPasswordError = isPdfPasswordException(err);
            if (isPasswordError) {
                return false;
            }
            throw err;
        }
    };

    const handleUploadAndAnalyze = async () => {
        if (!file) {
            toast.error("Debes seleccionar un archivo PDF");
            return;
        }
        if (!bankId) {
            toast.error("Debes seleccionar el banco del crédito");
            return;
        }
        if (checkingPdf) {
            toast.error("Estamos validando el PDF, espera un momento");
            return;
        }
        if (pdfRequiresPassword) {
            if (!pdfPassword) {
                setPdfPasswordError('Debes ingresar la contraseña del PDF');
                toast.error('El PDF requiere contraseña');
                return;
            }
            const isValid = await verifyPdfPassword(file, pdfPassword);
            if (!isValid) {
                setPdfPasswordError('Contraseña incorrecta');
                toast.error('Contraseña incorrecta');
                return;
            }
            setPdfPasswordError('');
        }

        setUploading(true);
        try {
            // 1. Upload Document
            const uploadRes = await apiClient.uploadDocument(
                file,
                pdfRequiresPassword ? pdfPassword : undefined
            );
            
            if (!uploadRes.success) {
                const duplicateMessage = "Este documento ya lo ha subido anteriormente. Puede ver el resumen de su análisis en la sección de 'Historial de análisis'.";
                if (uploadRes.message === duplicateMessage) {
                    setMonthlyDuplicateWarning(true);
                    setUploading(false);
                    return;
                }

                if (uploadRes.validation?.requires_password) {
                    setPdfRequiresPassword(true);
                    toast.error("El PDF está protegido. Por favor ingresa la contraseña.");
                    setUploading(false);
                    return;
                }
                throw new Error(uploadRes.message || "Error al subir documento");
            }
            
            const docId = uploadRes.document_id;
            if(!docId) throw new Error("No se recibió ID del documento");
            // 2. Create analysis (la extracción IA ocurre en backend una sola vez)
            startLoadingOverlay();
            setProcessing(true); // Switch to processing state UI
            setUploading(false); // Upload done

            // 3. Create Analysis
            const analysisRes = await apiClient.createAnalysis({
                documento_id: docId,
                datos_usuario: {
                    ingresos_mensuales: Number(income),
                    capacidad_pago_max: Number(paymentCapacity),
                    tipo_contrato_laboral: contractType,
                    opciones_abono_preferidas: [
                        Number(option1 || 0),
                        Number(option2 || 0),
                        Number(option3 || 0)
                    ].filter((value) => value > 0)
                },
                banco_id: bankId || undefined
            });

            if (!analysisRes.success || !analysisRes.analisis_id) {
                if (analysisRes.invalid_document_type) {
                    throw new Error("El documento subido no es un crédito hipotecario válido.");
                }
                throw new Error(analysisRes.message || "No se pudo crear el análisis.");
            }

            if (analysisRes.name_mismatch) {
                toast.warning(
                    "El nombre en el extracto parece diferente al tuyo. Verificaremos manualmente.",
                    { duration: 6000 }
                );
            }

            const createdAnalysisId = analysisRes.analisis_id;

            // 4. Fetch Detail Summary
            let fetchedSummary: AnalysisSummary | null = null;
            try {
                fetchedSummary = await apiClient.getAnalysisSummary(createdAnalysisId);
            } catch (sumErr) {
                console.warn("Could not fetch summary immediately:", sumErr);
                // We proceed anyway, maybe show a "Generated" state without full summary or retry
            }

            await completeLoadingOverlay();

            if (fetchedSummary) {
                setSummaryData(fetchedSummary);
            }
            setAnalysisId(createdAnalysisId);
            setStep(3);
            toast.success("¡Análisis creado exitosamente!");

        } catch (err: unknown) {
            resetLoadingOverlay();
            console.warn("Create Analysis failed:", getErrorMessage(err));
            const parsedError = parseApiError(err);
            const errorMessage = getErrorMessage(err);
            const isIdentityValidationError =
                parsedError?.status_code === 403 ||
                parsedError?.status_code === 422 ||
                errorMessage.toLowerCase().includes('no coinciden con tu cuenta') ||
                errorMessage.toLowerCase().includes('nombre o la cédula') ||
                errorMessage.toLowerCase().includes('cedula') ||
                errorMessage.toLowerCase().includes('mejor calidad');
            const detail = (err && typeof err === 'object')
                ? (err as { detail?: { requires_password?: boolean; message?: string } }).detail
                : undefined;
            if (detail?.requires_password) {
                setPdfRequiresPassword(true);
                toast.error(detail.message || 'El PDF requiere contraseña');
            } else if (isIdentityValidationError) {
                setIdentityMismatchMessage(errorMessage);
                setShowIdentityMismatchModal(true);
            } else {
                toast.error(errorMessage);
            }
        } finally {
            setUploading(false);
            setProcessing(false);
        }
    };

    const openContactConfirmationModal = () => {
        if (!file) {
            toast.error("Debes seleccionar un archivo PDF");
            return;
        }

        setShowContactModal(true);
    };

    const handleConfirmAndStartAnalysis = async () => {
        const normalizedPhone = contactPhone.replace(/\D/g, '').trim();
        if (!normalizedPhone) {
            toast.error('Por favor verifica tu número de celular');
            return;
        }

        if (!COLOMBIA_MOBILE_REGEX.test(normalizedPhone)) {
            toast.error('Ingresa un celular válido de Colombia (10 dígitos iniciando en 3)');
            return;
        }

        if (!user) {
            toast.error('No se encontró el perfil del usuario');
            return;
        }

        const currentPhone = (user.telefono || '').replace(/\D/g, '').trim();

        if (normalizedPhone !== currentPhone) {
            setSavingContact(true);
            try {
                const updatedProfile = await apiClient.updateProfile({ telefono: normalizedPhone });
                setUser(updatedProfile);
                setContactPhone((updatedProfile.telefono || normalizedPhone).replace(/\D/g, '').slice(0, 10));
            } catch (err: unknown) {
                toast.error(getErrorMessage(err));
                return;
            } finally {
                setSavingContact(false);
            }
        }

        setUser((prev) => (prev ? { ...prev, telefono: normalizedPhone } : prev));
        setShowContactModal(false);
        await handleUploadAndAnalyze();
    };


    if (loading) return <div className="p-8 text-center text-gray-500">Cargando perfil...</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Header: User Info (Readonly) */}
            <Card className="bg-white border-none shadow-sm">
                <div className="flex items-center gap-4 p-4 text-sm text-gray-600">
                    <div className="bg-[var(--verde-suave)] p-2 rounded-full text-[var(--verde-bosque)]">
                        <User size={20} />
                    </div>
                    <div className="hidden md:block border-r pr-4 border-gray-200">
                        <p className="font-bold text-gray-900">Mi Información</p>
                    </div>
                    <div className="flex flex-wrap gap-x-6 gap-y-1">
                         <span><span className="font-medium text-gray-900">Usuario:</span> {user?.nombres} {user?.primer_apellido}</span>
                         <span><span className="font-medium text-gray-900">ID:</span> {user?.identificacion}</span>
                         <span><span className="font-medium text-gray-900">Email:</span> {user?.email}</span>
                    </div>
                </div>
            </Card>

            <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Nuevo Análisis de Crédito</h1>

            {/* Step 1: Financial Info */}
            <div className={step === 1 ? 'block' : 'hidden'}>
                <Card variant="default" className="border-t-4 border-[var(--verde-hoja)]">
                    <CardHeader>
                        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
                            <DollarSign className="text-[var(--verde-hoja)]" />
                            1. Información Financiera
                        </h2>
                        <p className="text-gray-500 text-sm mt-1">Ingresa tus datos para personalizar el análisis.</p>
                    </CardHeader>
                    
                    <form onSubmit={handleStep1Submit} className="space-y-6 mt-4">
                        <div className="w-full flex flex-col gap-1.5 ">
                            <label className="block text-sm font-semibold text-gray-700 ml-1">Tipo de Crédito *</label>
                            <select 
                                className="w-full px-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl transition-all duration-200 outline-none bg-white focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja"
                                value={creditType}
                                onChange={(e) => setCreditType(e.target.value)}
                            >
                                <option value="Hipotecario">Crédito Hipotecario</option>
                            </select>
                            <p className="text-xs text-gray-500 ml-1">Por el momento solo soportamos análisis de créditos hipotecarios.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <Input 
                                label="Ingresos Mensuales Total (COP) *"
                                type="text"
                                inputMode="numeric"
                                placeholder="Ej: 5.000.000"
                                value={formatNumberInput(income)}
                                onChange={(e) => setIncome(cleanNumberInput(e.target.value))}
                                required
                            />
                            <Input 
                                label="Capacidad de Pago Máxima (COP) *"
                                type="text"
                                inputMode="numeric"
                                placeholder="Ej: 1.500.000"
                                helperText="Lo máximo que puedes pagar mensual por la cuota"
                                value={formatNumberInput(paymentCapacity)}
                                onChange={(e) => setPaymentCapacity(cleanNumberInput(e.target.value))}
                                required
                            />
                        </div>

                        <div className="w-full flex flex-col gap-1.5">
                            <label className="block text-sm font-semibold text-gray-700 ml-1">Tipo de Contrato *</label>
                            <select 
                                className="w-full px-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl transition-all duration-200 outline-none bg-white focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja"
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

                        <div className="bg-[var(--gray-50)] p-4 rounded-xl border border-gray-200">
                            <h3 className="font-semibold text-gray-700 mb-3 text-sm flex items-center gap-2">
                                <CheckCircle2 size={16} className="text-[var(--verde-hoja)]"/>
                                Opciones de Abono Extra (Simulacion)
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <Input
                                    label="Opcion 1"
                                    type="text"
                                    inputMode="numeric"
                                    value={formatNumberInput(option1)}
                                    onChange={(e) => setOption1(cleanNumberInput(e.target.value))}
                                />
                                <Input
                                    label="Opcion 2"
                                    type="text"
                                    inputMode="numeric"
                                    value={formatNumberInput(option2)}
                                    onChange={(e) => setOption2(cleanNumberInput(e.target.value))}
                                />
                                <Input
                                    label="Opcion 3"
                                    type="text"
                                    inputMode="numeric"
                                    value={formatNumberInput(option3)}
                                    onChange={(e) => setOption3(cleanNumberInput(e.target.value))}
                                />
                            </div>
                        </div>

                        <div className="flex justify-end">
                            <Button type="submit" variant="primary" size="lg" rightIcon={<ArrowRight size={18} />}>
                                Continuar
                            </Button>
                        </div>
                    </form>
                </Card>
            </div>


            {/* Step 2: Upload PDF */}
            <div className={step === 2 || step === 3 ? 'block' : 'hidden'}>
               {/* Readonly Summary of Step 1 if in Step 2 */}
               {step === 2 && (
                   <div className="flex justify-between items-center bg-gray-50 border border-gray-200 p-4 rounded-lg mb-6">
                       <div className="text-sm text-gray-600">
                           <strong>Ingresos:</strong> ${formatNumberInput(income)} | <strong>Contrato:</strong> {contractType}
                       </div>
                       <Button variant="ghost" size="sm" onClick={() => setStep(1)} disabled={uploading || processing}>
                           Editar
                       </Button>
                   </div>
               )}

               <Card variant="default" className={`transition-opacity ${step === 3 ? 'opacity-50 pointer-events-none' : 'opacity-100'} border-t-4 border-blue-500`}>
                    <CardHeader>
                        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
                            <Upload className="text-blue-500" />
                            2. Subir Extracto Bancario
                        </h2>
                         <p className="text-gray-500 text-sm mt-1">Sube el PDF de tu extracto para procesarlo con IA.</p>
                    </CardHeader>
                    
                    <div className="space-y-6 mt-4">
                        {monthlyDuplicateWarning && (
                            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-900 space-y-2">
                                <p className="text-sm font-medium">
                                    Este documento ya lo ha subido anteriormente. Puede ver el resumen de su análisis en la sección de{' '}
                                    <Link href="/dashboard/historial" className="underline font-semibold hover:text-amber-700">
                                        Historial de análisis
                                    </Link>
                                    .
                                </p>
                                <p className="text-sm">
                                    Podrá volver a subir este documento el próximo mes, una vez que se reflejen nuevos movimientos en su extracto.
                                </p>
                                <div className="inline-flex items-center gap-2 rounded-lg border border-amber-400/60 bg-white px-3 py-2 text-xs font-semibold text-amber-800">
                                    <Calendar size={14} />
                                    <span>
                                        Habilitado nuevamente el {nextUploadAvailability.dateLabel} · faltan {nextUploadAvailability.daysRemaining} día{nextUploadAvailability.daysRemaining === 1 ? '' : 's'}
                                    </span>
                                </div>
                            </div>
                        )}

                        {/* Drag & Drop Area */}
                        <div 
                            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-colors cursor-pointer
                                ${file ? 'border-[var(--verde-hoja)] bg-[var(--verde-suave)]' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}
                            `}
                            onDragOver={handleDragOver}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input 
                                type="file" 
                                accept="application/pdf" 
                                className="hidden" 
                                ref={fileInputRef} 
                                onChange={handleFileChange}
                            />
                            
                            {file ? (
                                <div className="space-y-2">
                                    <FileText size={48} className="mx-auto text-[var(--verde-hoja)]" />
                                    <p className="font-semibold text-gray-900">{file.name}</p>
                                    <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                    <p className="text-xs text-[var(--verde-bosque)] font-medium mt-2">Click para cambiar</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <Upload size={48} className="mx-auto text-gray-400" />
                                    <p className="font-medium text-gray-700">Arrastra tu PDF aquí o haz click para buscar</p>
                                    <p className="text-xs text-gray-400">Solo archivos .pdf habilitados</p>
                                </div>
                            )}
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="w-full flex flex-col gap-1.5">
                                <label className="block text-sm font-semibold text-gray-700 ml-1">Banco del Extracto *</label>
                                <div className="relative">
                                    <CreditCard size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                    <select
                                        className="w-full pl-10 pr-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl transition-all duration-200 outline-none bg-white focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja"
                                        value={bankId || ''}
                                        onChange={(e) => setBankId(e.target.value ? Number(e.target.value) : null)}
                                        required
                                    >
                                        <option value="" disabled>Selecciona un banco</option>
                                        {banks.map((bank) => (
                                            <option key={bank.id} value={bank.id}>{bank.nombre}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            {pdfRequiresPassword ? (
                                <Input 
                                    label="Contraseña del PDF"
                                    type="password"
                                    placeholder="Ingresa la clave del PDF"
                                    value={pdfPassword}
                                    onChange={(e) => {
                                        setPdfPassword(e.target.value);
                                        if (pdfPasswordError) setPdfPasswordError('');
                                    }}
                                    leftIcon={<Lock size={18} />}
                                    showPasswordToggle
                                    error={pdfPasswordError || undefined}
                                    helperText={!pdfPasswordError ? "Este PDF esta protegido" : undefined}
                                />
                            ) : (
                                <div className="text-sm text-gray-500 flex items-center">
                                    {checkingPdf
                                        ? 'Validando PDF...'
                                        : file
                                            ? 'PDF sin contrasena detectado'
                                            : 'Selecciona un PDF para validar'
                                    }
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="pt-4">
                             {(uploading || processing) ? (
                                 <div className="w-full bg-gray-100 rounded-lg p-4 text-center space-y-3">
                                     <Loader2 size={32} className="mx-auto animate-spin text-[var(--verde-hoja)]" />
                                     <p className="font-medium text-gray-700">
                                         {uploading ? 'Subiendo documento...' : 'Analizando extracto...'}
                                     </p>
                                     <p className="text-xs text-gray-500">Esto puede tomar unos segundos. Por favor no cierres la página.</p>
                                 </div>
                             ) : (
                                step === 2 && (
                                    <Button 
                                        onClick={openContactConfirmationModal} 
                                        variant="primary" 
                                        className="w-full py-4 text-lg shadow-lg hover:shadow-xl"
                                        disabled={!file}
                                    >
                                        Subir y Analizar
                                    </Button>
                                )
                             )}
                        </div>
                    </div>
               </Card>
            </div>

            {/* Step 3: Success Result & Summary */}
            {step === 3 && analysisId && (
                  <div ref={analysisCompletedSectionRef} className="space-y-6">
                 <Card variant="soft" className="border border-green-200 bg-green-50 animate-in fade-in slide-in-from-bottom-4">
                    <div className="text-center py-6 space-y-3">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                            <CheckCircle2 size={32} className="text-green-600" />
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900">¡Análisis Completado!</h2>
                        <p className="text-gray-600 max-w-md mx-auto">
                            Hemos procesado tu extracto. Aquí tienes el resumen de tu crédito actual.
                        </p>
                    </div>
                 </Card>

                 {summaryData && (
                     <div className="space-y-4">
                         {/* Bloque 1: DATOS BÁSICOS */}
                         <Card>
                             <CardHeader className="pb-2 border-b">
                                 <h3 className="font-semibold text-gray-700">DATOS BÁSICOS</h3>
                             </CardHeader>
                             <div className="p-4 pt-3 text-sm grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1">
                                <Row label="Valor Prestado" value={formatMoneyOrND(summaryData.datos_basicos?.valor_prestado)} />
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

                         {/* Bloque 2: LÍMITES CON EL BANCO HOY */}
                         <Card>
                             <CardHeader className="pb-2 border-b">
                                 <h3 className="font-semibold text-gray-700">LÍMITES CON EL BANCO HOY</h3>
                             </CardHeader>
                             <div className="p-4 pt-3 text-sm space-y-1">
                                <Row label="Valor Prestado" value={formatMoneyOrND(summaryData.limites_banco?.valor_prestado)} />
                                <Row label="Saldo Actual del Crédito" value={formatMoney(summaryData.limites_banco?.saldo_actual_credito)} valueClass="font-bold text-lg text-gray-900" />
                             </div>
                         </Card>

                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                             {/* Bloque 3: AJUSTE POR INFLACIÓN */}
                             <Card>
                                 <CardHeader className="pb-2 border-b">
                                     <h3 className="font-semibold text-gray-700">AJUSTE POR INFLACIÓN</h3>
                                 </CardHeader>
                                 <div className="p-4 pt-3 text-sm space-y-1">
                                     <Row 
                                         label="Ajuste en Pesos" 
                                         value={summaryData.ajuste_inflacion ? formatMoney(summaryData.ajuste_inflacion.ajuste_pesos) : 'N/A'} 
                                         valueClass={summaryData.ajuste_inflacion && Number(summaryData.ajuste_inflacion.ajuste_pesos) > 0 ? "text-red-600 font-semibold" : "text-green-600 font-semibold"}
                                     />
                                     <Row 
                                         label="% Ajustado (Incremento por Inflación)" 
                                         value={summaryData.ajuste_inflacion ? `${Number(summaryData.ajuste_inflacion.porcentaje_ajuste).toFixed(2)}%` : 'N/A'} 
                                         valueClass={summaryData.ajuste_inflacion && Number(summaryData.ajuste_inflacion.porcentaje_ajuste) > 0 ? "text-red-600" : "text-green-600"}
                                     />
                                 </div>
                             </Card>

                             {/* Bloque 4: INTERESES Y SEGUROS */}
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

                         {/* Metadata */}
                         <div className="flex flex-wrap gap-4 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
                             <span><strong>Sistema:</strong> {summaryData.sistema_amortizacion || 'N/A'}</span>
                             <span><strong>Nº Crédito:</strong> {summaryData.numero_credito || 'N/A'}</span>
                             <span><strong>Fecha Extracto:</strong> {summaryData.fecha_extracto || 'N/A'}</span>
                         </div>
                     </div>
                 )}

                 </div>
            )}

            {showContactModal && (
                <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="w-full max-w-lg rounded-xl border border-gray-200 bg-white shadow-xl p-5 sm:p-6 space-y-5">
                        <div className="space-y-2">
                            <h3 className="text-xl font-semibold text-[var(--verde-bosque)]">Confirmar Datos de Contacto</h3>
                            <p className="text-sm text-gray-600">
                                Para enviarte los resultados del análisis, por favor verifica tu información.
                            </p>
                        </div>

                        <div className="space-y-1">
                            <Input
                                id="contact-email"
                                label="Email"
                                type="email"
                                value={user?.email || ''}
                                readOnly
                                className="bg-gray-100 text-gray-500 border-gray-200 cursor-not-allowed"
                            />
                            <div className="w-full flex flex-col gap-1.5">
                                <label htmlFor="contact-phone" className="text-sm font-semibold ml-1 text-verde-bosque">
                                    Celular
                                </label>
                                <div className="flex items-center w-full border border-gray-300 rounded-xl bg-white px-4 py-2.5 focus-within:ring-4 focus-within:ring-verde-hoja/15 focus-within:border-verde-hoja transition-all duration-200">
                                    <span className="text-gray-600 font-medium mr-3 select-none">+57</span>
                                    <input
                                        id="contact-phone"
                                        type="tel"
                                        inputMode="numeric"
                                        placeholder="300 123 4567"
                                        value={formatColombiaMobilePhone(contactPhone)}
                                        onChange={(e) => setContactPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                                        className="w-full text-sm md:text-base text-gray-900 bg-transparent outline-none placeholder:text-gray-400"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-2">
                            <Button
                                type="button"
                                variant="outline"
                                className="border-gray-300 text-gray-600 hover:bg-gray-50"
                                onClick={() => setShowContactModal(false)}
                                disabled={savingContact}
                            >
                                Cancelar
                            </Button>
                            <Button
                                type="button"
                                variant="primary"
                                className="sm:min-w-[240px]"
                                onClick={handleConfirmAndStartAnalysis}
                                isLoading={savingContact}
                                disabled={savingContact}
                            >
                                Confirmar e Iniciar Análisis
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {showIdentityMismatchModal && (
                <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="w-full max-w-2xl rounded-xl border border-red-200 bg-white shadow-xl p-6 sm:p-7 space-y-4">
                        <div className="flex items-start justify-between gap-4">
                            <h3 className="text-xl font-semibold text-red-700">No se pudo procesar el análisis</h3>
                            <button
                                type="button"
                                onClick={() => setShowIdentityMismatchModal(false)}
                                className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                                aria-label="Cerrar mensaje"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <p className="text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">
                            {identityMismatchMessage || 'Los datos del documento no coinciden con tu cuenta.'}
                        </p>

                        <div className="flex justify-end pt-2">
                            <Button
                                type="button"
                                variant="primary"
                                onClick={() => setShowIdentityMismatchModal(false)}
                            >
                                Entendido
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            <AnimatePresence>
                {showLoadingOverlay && (
                    <AnalysisLoadingOverlay
                        progress={loadingProgress}
                        statusText={getLoadingStatusText(loadingProgress, allowLoadingFinish)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

function getLoadingStatusText(progress: number, allowLoadingFinish: boolean) {
    if (allowLoadingFinish || progress >= 80) {
        return 'Finalizando análisis...';
    }

    if (progress < 30) {
        return 'Leyendo extracto...';
    }

    if (progress < 60) {
        return 'Analizando gastos...';
    }

    return 'Calculando capacidad de pago...';
}

function AnalysisLoadingOverlay({ progress, statusText }: { progress: number; statusText: string }) {
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
                            <h3 className="text-xl font-semibold text-[var(--verde-bosque)]">Procesando tu análisis financiero</h3>
                        </div>

                        <div className="h-3 w-full rounded-full bg-gray-200 overflow-hidden">
                            <motion.div
                                className="h-full rounded-full bg-[var(--verde-hoja)]"
                                animate={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
                                transition={{ duration: 0.22, ease: 'easeOut' }}
                            />
                        </div>

                        <div className="flex justify-between items-center text-xs text-gray-500">
                            <span>No cierres esta ventana. Estamos procesando tu extracto.</span>
                            <span className="font-semibold text-[var(--verde-bosque)]">{Math.round(progress)}%</span>
                        </div>
                    </div>
                </motion.div>
            </div>
        </motion.div>
    );
}

function cleanNumberInput(value: string) {
    return value.replace(/[^\d]/g, '');
}

function formatNumberInput(value: string) {
    if (!value) return '';
    const parsed = Number(value);
    if (Number.isNaN(parsed)) return '';
    return new Intl.NumberFormat('es-CO').format(parsed);
}

function getNextUploadAvailability() {
    const now = new Date();
    const nextMonthFirstDay = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const msPerDay = 1000 * 60 * 60 * 24;
    const daysRemaining = Math.max(1, Math.ceil((nextMonthFirstDay.getTime() - now.getTime()) / msPerDay));

    const dateLabel = new Intl.DateTimeFormat('es-CO', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    }).format(nextMonthFirstDay);

    return {
        dateLabel,
        daysRemaining,
    };
}

function Row({ label, value, valueClass = "text-gray-900" }: { label: string, value: ReactNode, valueClass?: string }) {
    if (value === undefined || value === null) return null;
    return (
        <div className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
            <span className="text-gray-700">{label}</span>
            <span className={`font-medium ${valueClass}`}>{value}</span>
        </div>
    );
}

function formatMoney(amount?: number) {
    if (amount === undefined || amount === null) return '-';
    return new Intl.NumberFormat('es-CO', { 
        style: 'currency', 
        currency: 'COP', 
        minimumFractionDigits: 0,
        maximumFractionDigits: 2 
    }).format(amount);
}

function formatMoneyOrND(amount?: number | null) {
    if (amount === undefined || amount === null || Number(amount) <= 0) return 'N/D';
    return formatMoney(amount);
}

function formatColombiaMobilePhone(value: string) {
    const digits = value.replace(/\D/g, '').slice(0, 10);
    if (!digits) return '';
    const first = digits.slice(0, 3);
    const second = digits.slice(3, 6);
    const third = digits.slice(6, 10);
    return [first, second, third].filter(Boolean).join(' ');
}
