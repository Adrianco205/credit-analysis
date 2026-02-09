export interface RegisterRequest {
  nombres: string;
  primer_apellido: string;
  segundo_apellido?: string;
  tipo_identificacion: string;
  identificacion: string;
  email: string;
  telefono?: string;
  genero?: string;
  password: string;
  ciudad_departamento?: string;
}

export interface RegisterResponse {
  user_id: string;
  status: string;
  message: string;
}

export interface VerifyOtpRequest {
  user_id: string;
  code: string;
}

export interface VerifyOtpResponse {
  message: string;
  status: string;
}

export interface LoginRequest {
  identificacion: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  identificacion: string;
  tipo_identificacion?: string;
  nombres: string;
  primer_apellido: string;
  segundo_apellido?: string;
  apellidos: string;  // Computed field from backend
  genero?: string;
  email: string;
  telefono?: string;
  status: string;
  email_verificado: boolean;
  ciudad_departamento?: string;
  rol?: string;
}

export interface UpdatePasswordRequest {
  current_password: string;
  new_password: string;
}

// Analysis & Documents Types

export interface DocumentUploadResponse {
  success: boolean;
  message: string;
  document_id?: string;
  validation?: {
    is_valid: boolean;
    requires_password: boolean;
    message: string;
  };
}

export interface ExtractDataResponse {
  success: boolean;
  data: any; // Flexible for now as structure is complex
  banco_detected?: string;
  confidence?: number;
  es_extracto_hipotecario?: boolean;
}

export interface BancoItem {
  id: number;
  nombre: string;
}

export interface CreateAnalysisRequest {
  documento_id: string;
  datos_usuario: {
    ingresos_mensuales: number;
    capacidad_pago_max?: number;
    tipo_contrato_laboral?: string;
    opciones_abono_preferidas?: number[];
  };
  banco_id?: number;
}

export interface CreateAnalysisResponse {
  success: boolean;
  analisis_id?: string;
  status?: string;
  message?: string;
  requires_manual_input?: boolean;
  campos_faltantes?: string[];
  campos_extraidos?: string[];
  name_mismatch?: boolean;
  id_mismatch?: boolean;
  invalid_document_type?: boolean;
  tipo_documento_detectado?: string;
}

export interface DatosBasicosResumen {
  valor_prestado: number;
  cuotas_pactadas: number;
  cuotas_pagadas: number;
  cuotas_por_pagar: number;
  cuota_actual_aprox: number;
  beneficio_frech: number;
  cuota_completa_aprox: number;
  total_pagado_fecha: number;
  total_frech_recibido: number;
  monto_real_pagado_banco: number;
}

export interface LimitesBancoResumen {
  valor_prestado: number;
  saldo_actual_credito: number;
  abono_adicional_cuota?: number | null;
}

export interface AjusteInflacionResumen {
    ajuste_pesos: number;
    porcentaje_ajuste: number;
    metodo?: string | null;  // "uvr_calculation", "direct_difference", "manual"
}

export interface DesgloseInteresesSeguros {
    interes_corriente: number;
    interes_mora: number;
    seguro_vida: number;
    seguro_incendio: number;
    seguro_terremoto: number;
    otros_cargos: number;
}

export interface CostosExtraResumen {
    total_intereses_seguros: number;
    desglose?: DesgloseInteresesSeguros | null;
    capital_pagado_periodo?: number | null;
    intereses_corrientes_periodo?: number | null;
    intereses_mora_periodo?: number | null;
    seguros_total_periodo?: number | null;
    otros_cargos_periodo?: number | null;
    formula?: string | null;
}

export interface AnalysisSummary {
  analisis_id: string;
  numero_credito?: string;
  nombre_titular?: string;
  banco_nombre?: string;
  sistema_amortizacion?: string;
  fecha_extracto?: string;
  
  datos_basicos: DatosBasicosResumen;
  limites_banco: LimitesBancoResumen;
  ajuste_inflacion?: AjusteInflacionResumen | null;
  costos_extra?: CostosExtraResumen;
  
  // Flags de auditoría
  is_total_paid_estimated?: boolean;
  
  // Legacy fields if used elsewhere
  id?: string;
  documento_id?: string;
  status?: string;
  datos_faltantes?: string[]; 
}

export interface ApiError {
  error: string;
  message: string;
  status_code: number;
  detail?: string | object;
}

// ==========================================
// HISTORIAL DE ESTUDIOS
// ==========================================

export interface EstudioHistorialItem {
  analisis_id: string;
  documento_id: string | null;
  banco_nombre: string | null;
  fecha_subida: string | null;
  status: string;
  saldo_actual: number | null;
  numero_credito: string | null;
}

export interface EstudiosHistorialResponse {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  estudios: EstudioHistorialItem[];
}
