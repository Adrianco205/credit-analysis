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

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface ResetPasswordResponse {
  message: string;
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

export interface UpdateManualFieldsRequest {
  numero_credito?: string;
  sistema_amortizacion?: string;
  valor_prestado_inicial?: number;
  fecha_desembolso?: string;
  cuotas_pactadas?: number;
  cuotas_pagadas?: number;
  cuotas_pendientes?: number;
  tasa_interes_pactada_ea?: number;
  tasa_interes_cobrada_ea?: number;
  valor_cuota_con_seguros?: number;
  beneficio_frech_mensual?: number;
  saldo_capital_pesos?: number;
  saldo_capital_uvr?: number;
  valor_uvr_fecha_extracto?: number;
  seguro_vida?: number;
  seguro_incendio?: number;
  seguro_terremoto?: number;
  capital_pagado_periodo?: number;
  intereses_corrientes_periodo?: number;
  intereses_mora?: number;
  otros_cargos?: number;
}

export interface ProjectionRequestOption {
  numero_opcion: number;
  abono_adicional_mensual: number;
  nombre_opcion?: string;
}

export interface ProjectionResponse {
  id: string;
  numero_opcion: number;
  nombre_opcion?: string | null;
  abono_adicional_mensual: number;
  cuotas_nuevas?: number | null;
  tiempo_restante_anios?: number | null;
  tiempo_restante_meses?: number | null;
  cuotas_reducidas?: number | null;
  tiempo_ahorrado_anios?: number | null;
  tiempo_ahorrado_meses?: number | null;
  nuevo_valor_cuota?: number | null;
  total_por_pagar_aprox?: number | null;
  valor_ahorrado_intereses?: number | null;
  veces_pagado?: number | null;
  honorarios_calculados?: number | null;
  honorarios_con_iva?: number | null;
  ingreso_minimo_requerido?: number | null;
  origen: string;
  es_opcion_seleccionada: boolean;
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
  costos_extra: CostosExtraResumen;

  tasa_cobrada_con_frech?: number | null;
  seguros_actuales_mensual?: number | null;
  ingresos_mensuales?: number | null;
  capacidad_pago_max?: number | null;
  
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

// ==========================================
// ADMIN - HISTORIAL GLOBAL DE ANÁLISIS
// ==========================================

export interface AdminAnalysisActions {
  can_view_summary: boolean;
  can_view_detail: boolean;
  can_view_pdf: boolean;
}

export interface AdminAnalysisItem {
  analysis_id: string;
  uploaded_at: string | null;
  document_id: string | null;
  credit_number: string | null;
  status: string;
  customer: {
    user_id: string;
    full_name: string;
    id_number: string | null;
  };
  bank: {
    id: number | null;
    name: string | null;
  };
  actions: AdminAnalysisActions;
}

export interface AdminAnalysesResponse {
  data: AdminAnalysisItem[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
  filters: {
    bank_options: Array<{ id: number; name: string }>;
  };
}

export interface AdminAnalysisDetailResponse {
  id: string;
  documento_id: string;
  usuario_id: string;
  status: string;
  usuario_nombre?: string | null;
  usuario_cedula?: string | null;
  usuario_email?: string | null;
  usuario_telefono?: string | null;
  nombre_titular_extracto?: string | null;
  numero_credito?: string | null;
  banco_nombre?: string | null;
  sistema_amortizacion?: string | null;
  plan_credito?: string | null;
  tasa_interes_cobrada_ea?: number | null;
  valor_cuota_con_seguros?: number | null;
  cuotas_pendientes?: number | null;
  cuotas_pagadas?: number | null;
  fecha_extracto?: string | null;
  saldo_capital_pesos?: number | null;
  ingresos_mensuales?: number | null;
  capacidad_pago_max?: number | null;
  opciones_abono_preferidas?: number[] | null;
  created_at?: string | null;
}

export interface ProjectionTimeResponse {
  anios: number;
  meses: number;
  total_meses?: number;
  descripcion: string;
}

export interface ProposalCurrentLimitsResponse {
  saldo_credito: number;
  cuotas_pendientes: number;
  tiempo_pendiente: ProjectionTimeResponse;
  abono_adicional_cuota: number;
  valor_cuota: number;
  total_por_pagar_aprox: number;
  veces_pagado: number;
}

export interface ProposalOptionResponse {
  id?: string | null;
  numero_opcion: number;
  nombre_opcion?: string | null;
  abono_adicional_mensual: number;
  cuotas_nuevas: number;
  tiempo_restante: ProjectionTimeResponse;
  nuevo_valor_cuota: number;
  total_por_pagar_aprox: number;
  cuotas_reducidas: number;
  tiempo_ahorrado: ProjectionTimeResponse;
  valor_ahorrado_intereses: number;
  veces_pagado: number;
  honorarios_calculados: number;
  honorarios_con_iva: number;
  ingreso_minimo_requerido: number;
  origen: string;
  es_opcion_seleccionada: boolean;
}

export interface PropuestaCompletaResponse {
  analisis_id: string;
  numero_credito?: string | null;
  nombre_cliente?: string | null;
  banco_nombre?: string | null;
  fecha_generacion: string;
  limites_actuales: ProposalCurrentLimitsResponse;
  opciones: ProposalOptionResponse[];
  tasa_cobrada_con_frech?: number | null;
  seguros_actuales?: number | null;
  vigencia_dias: number;
  fecha_vencimiento?: string | null;
  agente_financiero?: string | null;
}

export interface AdminProjectionOptionRequest {
  numero_opcion: number;
  abono_adicional_mensual: number;
  nombre_opcion: string;
}

export interface AdminProjectionResponse {
  id: string;
  analisis_id: string;
  numero_opcion: number;
  nombre_opcion?: string | null;
  abono_adicional_mensual: number;
  cuotas_nuevas?: number | null;
  tiempo_restante_anios?: number | null;
  tiempo_restante_meses?: number | null;
  cuotas_reducidas?: number | null;
  tiempo_ahorrado_anios?: number | null;
  tiempo_ahorrado_meses?: number | null;
  nuevo_valor_cuota?: number | null;
  total_por_pagar_aprox?: number | null;
  valor_ahorrado_intereses?: number | null;
  veces_pagado?: number | null;
  honorarios_calculados?: number | null;
  honorarios_con_iva?: number | null;
  ingreso_minimo_requerido?: number | null;
  origen: string;
  es_opcion_seleccionada: boolean;
  created_at?: string | null;
}

export interface AdminAnalysesParams {
  page?: number;
  page_size?: number;
  customer_id_number?: string;
  customer_name?: string;
  credit_number?: string;
  bank_id?: number;
  uploaded_from?: string;
  uploaded_to?: string;
  sort_by?: 'uploaded_at' | 'customer_name' | 'bank_name' | 'credit_number';
  sort_dir?: 'asc' | 'desc';
}

export interface UVRResponse {
  fecha: string;
  valor: number;
  fuente: string;
  definicion?: string | null;
  warning?: string | null;
}

export interface IPCResponse {
  fecha: string;
  valor: number;
  variacion_mensual?: number | null;
  variacion_anual: number;
  fuente: string;
  tipo_serie?: string | null;
  definicion?: string | null;
  warning?: string | null;
}

export interface DTFResponse {
  fecha: string;
  valor: number;
  fuente: string;
  definicion?: string | null;
  warning?: string | null;
}

export interface IndicadoresConsolidadosResponse {
  fecha: string;
  uvr?: number | null;
  dtf?: number | null;
  ibr_overnight?: number | null;
  ipc_anual?: number | null;
  fuente?: string;
  fecha_actualizacion?: string;
  warning?: string | null;
}

export interface HistoricoUVRItem {
  fecha: string;
  valor: number;
  fuente: string;
  warning?: string | null;
}

export interface HistoricoUVRResponse {
  fecha_inicio: string;
  fecha_fin: string;
  total_registros: number;
  datos: HistoricoUVRItem[];
}

export interface ConversionUVRRequest {
  monto: number;
  valor_uvr?: number;
  direccion: 'uvr_a_pesos' | 'pesos_a_uvr';
}

export interface ConversionUVRResponse {
  monto_original: number;
  monto_convertido: number;
  valor_uvr_usado: number;
  direccion: 'uvr_a_pesos' | 'pesos_a_uvr';
}

export interface ProyeccionUVRRequest {
  meses: number;
  uvr_inicial?: number;
  inflacion_anual: number;
}

export interface ProyeccionUVRResponse {
  uvr_inicial: number;
  uvr_proyectado: number;
  meses: number;
  inflacion_anual: number;
  incremento_absoluto: number;
  incremento_porcentual: number;
}
