'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { UserProfile, DocumentUploadResponse, AnalysisSummary } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader } from '@/components/ui/card';
import { toast } from 'sonner';
import { 
    FileText, 
    Upload, 
    CheckCircle2, 
    AlertTriangle, 
    CreditCard, 
    User, 
    DollarSign,
    Calendar,
    ArrowRight,
    Loader2,
    Lock
} from 'lucide-react';

export default function CreditAnalysisUploadPage() {
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
    const [documentId, setDocumentId] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [analysisId, setAnalysisId] = useState<string | null>(null);
    const [summaryData, setSummaryData] = useState<AnalysisSummary | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        loadProfile();
        loadBanks();
    }, []);

    const loadBanks = async () => {
        try {
            const banksList = await apiClient.getBanks();
            setBanks(banksList);
        } catch (err) {
            console.error('Error loading banks:', err);
        }
    };

    const loadProfile = async () => {
        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                router.push('/auth/login');
                return;
            }
            const u = await apiClient.getProfile();
            setUser(u);
        } catch (err: any) {
            console.error('Error loading profile:', err?.message || err?.error || JSON.stringify(err));
            if (err?.status_code === 401) {
                router.push('/auth/login');
                return;
            }
        } finally {
            setLoading(false);
        }
    };

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

        setUploading(true);
        try {
            // 1. Upload Document
            const uploadRes = await apiClient.uploadDocument(file, pdfPassword || undefined);
            
            if (!uploadRes.success) {
                // If requires password
                if (uploadRes.validation?.requires_password) {
                     toast.error("El PDF está protegido. Por favor ingresa la contraseña.");
                     setUploading(false);
                     return;
                }
                 throw new Error(uploadRes.message || "Error al subir documento");
            }
            
            const docId = uploadRes.document_id;
            if(!docId) throw new Error("No se recibió ID del documento");
            setDocumentId(docId);

            // 2. Extract Data
            setProcessing(true); // Switch to processing state UI
            setUploading(false); // Upload done
            
            const extractRes = await apiClient.extractDocumentData(docId);
            
            if (!extractRes.success) {
                // Check if it failed because it's not a mortgage credit
                if (extractRes.es_extracto_hipotecario === false) {
                     throw new Error("El documento subido no parece ser un extracto de crédito hipotecario válido.");
                }
                throw new Error("No se pudo extraer información del documento. ¿Es un extracto válido?");
            }

            // Verify explicitly it is a mortgage credit
            if (extractRes.es_extracto_hipotecario === false) {
                 throw new Error("El documento subido no parece ser un extracto de crédito hipotecario válido.");
            }

            // 3. Compare Name (Client Side)
            // Implementation of D) Validar nombre documento vs usuario
            const extractedName = (extractRes.data?.nombre_titular_extracto || '').toLowerCase();
            const userName = (`${user?.nombres || ''} ${user?.primer_apellido || ''}`).toLowerCase();
            
            // Simple check: basic includes or normalized check could be better
            // If the extraction is confident but names don't overlap significantly, warn.
            // Split into parts to be more lenient
            const userParts = userName.split(' ').filter((p: string) => p.length > 2);
            const extractedParts = extractedName.split(' ').filter((p: string) => p.length > 2);
            
            const match = userParts.some((part: string) => extractedName.includes(part)) || 
                          extractedParts.some((part: string) => userName.includes(part));

            if (!match && extractedName) {
                toast.warning(
                    "El nombre en el extracto parece diferente al tuyo. Verificaremos manualmente.", 
                    { duration: 6000 }
                );
            }
            
            // 4. Create Analysis
            const analysisRes = await apiClient.createAnalysis({
                documento_id: docId,
                datos_usuario: {
                    ingresos_mensuales: Number(income),
                    capacidad_pago_max: Number(paymentCapacity),
                    tipo_contrato_laboral: contractType,
                    opciones_abono_preferidas: [Number(option1), Number(option2), Number(option3)]
                },
                banco_id: bankId || undefined
            });

            if (!analysisRes.success || !analysisRes.analisis_id) {
                if (analysisRes.invalid_document_type) {
                    throw new Error("El documento subido no es un crédito hipotecario válido.");
                }
                throw new Error(analysisRes.message || "No se pudo crear el análisis.");
            }

            // 5. Fetch Detail Summary
            try {
                const summary = await apiClient.getAnalysisSummary(analysisRes.analisis_id);
                setSummaryData(summary);
            } catch (sumErr) {
                console.warn("Could not fetch summary immediately:", sumErr);
                // We proceed anyway, maybe show a "Generated" state without full summary or retry
            }

            setAnalysisId(analysisRes.analisis_id);
            setStep(3);
            toast.success("¡Análisis creado exitosamente!");

        } catch (err: any) {
            console.error("Create Analysis Error:", err);
            const msg = err.response?.data?.detail || err.message || 'Ocurrió un error en el proceso';
            toast.error(msg);
        } finally {
            setUploading(false);
            setProcessing(false);
        }
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
                        <p className="text-gray-500 text-sm mt-1">Ingresa tus datos para personalizar las proyecciones.</p>
                    </CardHeader>
                    
                    <form onSubmit={handleStep1Submit} className="space-y-6 mt-4">
                        <div className="w-full flex flex-col gap-1.5 ">
                            <label className="block text-sm font-semibold text-gray-700 ml-1">Tipo de Crédito *</label>
                            <select 
                                className="w-full px-4 py-3 text-sm md:text-base border border-gray-300 rounded-xl transition-all duration-200 outline-none bg-white focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja"
                                value={creditType}
                                onChange={(e) => setCreditType(e.target.value)}
                            >
                                <option value="Hipotecario">Crédito Hipotecario / Leasing Habitacional</option>
                            </select>
                            <p className="text-xs text-gray-500 ml-1">Por el momento solo soportamos análisis de créditos hipotecarios.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <Input 
                                label="Ingresos Mensuales Total (COP) *"
                                type="number"
                                placeholder="Ej: 5000000"
                                value={income}
                                onChange={(e) => setIncome(e.target.value)}
                                min="0"
                                required
                            />
                            <Input 
                                label="Capacidad de Pago Máxima (COP) *"
                                type="number"
                                placeholder="Ej: 1500000"
                                helperText="Lo máximo que puedes pagar mensual por la cuota"
                                value={paymentCapacity}
                                onChange={(e) => setPaymentCapacity(e.target.value)}
                                min="0"
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
                                Opciones de Abono Extra (Simulación)
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <Input label="Opción 1" type="number" value={option1} onChange={e => setOption1(e.target.value)} min="0" />
                                <Input label="Opción 2" type="number" value={option2} onChange={e => setOption2(e.target.value)} min="0" />
                                <Input label="Opción 3" type="number" value={option3} onChange={e => setOption3(e.target.value)} min="0" />
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
                            <strong>Ingresos:</strong> ${Number(income).toLocaleString()} | <strong>Contrato:</strong> {contractType}
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
                            <Input 
                                label="Contraseña del PDF (Opcional)"
                                type="password"
                                placeholder="Solo si el archivo pide clave"
                                value={pdfPassword}
                                onChange={(e) => setPdfPassword(e.target.value)}
                                leftIcon={<Lock size={18} />}
                                showPasswordToggle
                            />
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
                                        onClick={handleUploadAndAnalyze} 
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
                 <div className="space-y-6">
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
                                <Row label="Valor Prestado" value={formatMoney(summaryData.datos_basicos?.valor_prestado)} />
                                <Row label="Cuotas Pactadas" value={summaryData.datos_basicos?.cuotas_pactadas} />
                                <Row label="Cuotas Pagadas" value={summaryData.datos_basicos?.cuotas_pagadas} />
                                <Row label="Cuotas por Pagar" value={summaryData.datos_basicos?.cuotas_por_pagar} />
                                <Row label="Cuota Actual a Cancelar Aprox." value={formatMoney(summaryData.datos_basicos?.cuota_actual_aprox)} />
                                <Row label="Beneficio FRECH (cuota)" value={formatMoney(summaryData.datos_basicos?.beneficio_frech)} valueClass="text-green-600" />
                                <Row label="Cuota Completa Aprox. (sin FRECH)" value={formatMoney(summaryData.datos_basicos?.cuota_completa_aprox)} />
                                <div className="col-span-full border-t my-2" />
                                <Row label="Total Pagado al Día" value={formatMoney(summaryData.datos_basicos?.total_pagado_fecha)} valueClass="font-semibold" />
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
                                <Row label="Valor Prestado" value={formatMoney(summaryData.limites_banco?.valor_prestado)} />
                                <Row label="Saldo Actual del Crédito" value={formatMoney(summaryData.limites_banco?.saldo_actual_credito)} valueClass="font-bold text-lg" />
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

                 <div className="flex justify-end gap-4 pt-2">
                    <Button 
                        onClick={() => router.push(`/dashboard/analysis/${analysisId}/projections`)}
                        variant="primary"
                        size="lg"
                        rightIcon={<ArrowRight size={18} />}
                    >
                        Generar Proyecciones de Ahorro
                    </Button>
                 </div>
                 </div>
            )}
        </div>
    );
}

function Row({ label, value, valueClass = "text-gray-900" }: { label: string, value: any, valueClass?: string }) {
    if (value === undefined || value === null) return null;
    return (
        <div className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
            <span className="text-gray-500">{label}</span>
            <span className={`font-medium ${valueClass}`}>{value}</span>
        </div>
    );
}

function formatMoney(amount?: number) {
    if (amount === undefined || amount === null) return '-';
    return new Intl.NumberFormat('es-CO', { 
        style: 'currency', 
        currency: 'COP', 
        maximumFractionDigits: 0 
    }).format(amount);
}
