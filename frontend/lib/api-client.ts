import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  RegisterRequest,
  RegisterResponse,
  VerifyOtpRequest,
  VerifyOtpResponse,
  LoginRequest,
  TokenResponse,
  UserProfile,
  UpdatePasswordRequest,
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
  ApiError,
  DocumentUploadResponse,
  ExtractDataResponse,
  CreateAnalysisRequest,
  CreateAnalysisResponse,
  AdminClientAnalysisUploadRequest,
  AdminManualProjectionRequest,
  AnalysisDetailResponse,
  AnalysisSummary,
  ProjectionRequestOption,
  ProjectionResponse,
  UpdateManualFieldsRequest,
  EstudiosHistorialResponse,
  AdminAnalysesResponse,
  AdminAnalysesParams,
  AdminAnalysisDetailResponse,
  AdminUpdateAnalysisRequest,
  AdminProjectionOptionRequest,
  AdminCalculateProjectionsRequest,
  AdminProjectionResponse,
  PropuestaCompletaResponse,
  UVRResponse,
  IPCResponse,
  DTFResponse,
  IndicadoresConsolidadosResponse,
  HistoricoUVRResponse,
  ConversionUVRRequest,
  ConversionUVRResponse,
  ProyeccionUVRRequest,
  ProyeccionUVRResponse,
} from '@/types/api';

const API_BASE_URL = typeof window !== 'undefined' 
  ? (process.env.NEXT_PUBLIC_API_URL || '/api/v1')
  : (process.env.NEXT_PUBLIC_API_URL || '/api/v1');

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 300000,
    });

    // Request interceptor para agregar token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor para manejo de errores
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response) {
          // El servidor respondió con un código de error
          const responseData = error.response.data as any;
          // Check if responseData has actual content (not empty object)
          const hasContent = responseData && Object.keys(responseData).length > 0;
          
          // Handle FastAPI's default HTTPException format {"detail": "..."}
          // and convert to our ApiError format
          let apiError: ApiError;
          if (hasContent) {
            if (responseData.error && responseData.message) {
              // Already in our format
              apiError = responseData;
            } else if (responseData.detail) {
              // FastAPI HTTPException format
              apiError = {
                error: 'http_error',
                message: typeof responseData.detail === 'string' 
                  ? responseData.detail 
                  : JSON.stringify(responseData.detail),
                status_code: error.response.status,
                detail: responseData.detail
              };
            } else {
              // Unknown format - stringify it
              apiError = {
                error: 'unknown_error',
                message: JSON.stringify(responseData),
                status_code: error.response.status,
              };
            }
          } else {
            apiError = {
              error: 'unknown_error',
              message: `Error del servidor: ${error.response.status} ${error.response.statusText}`,
              status_code: error.response.status,
            };
          }
          return Promise.reject(apiError);
        } else if (error.request) {
          // La petición se hizo pero no hubo respuesta
          const networkError: ApiError = {
            error: 'network_error',
            message: 'No se pudo conectar con el servidor. Verifica tu conexión.',
            status_code: 0,
          };
          return Promise.reject(networkError);
        } else {
          // Algo salió mal al configurar la petición
          const unknownError: ApiError = {
            error: 'request_error',
            message: error.message || 'Error al procesar la petición',
            status_code: 0,
          };
          return Promise.reject(unknownError);
        }
      }
    );
  }

  // Token management
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  public setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  public removeToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }

  // Auth endpoints
  public async register(data: RegisterRequest): Promise<RegisterResponse> {
    const response = await this.client.post<RegisterResponse>('/auth/register', data);
    return response.data;
  }

  public async verifyOtp(data: VerifyOtpRequest): Promise<VerifyOtpResponse> {
    const response = await this.client.post<VerifyOtpResponse>('/auth/verify-otp', data);
    return response.data;
  }

  public async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/login', data);
    this.setToken(response.data.access_token);
    return response.data;
  }

  public async forgotPassword(data: ForgotPasswordRequest): Promise<ForgotPasswordResponse> {
    const response = await this.client.post<ForgotPasswordResponse>('/auth/forgot-password', data);
    return response.data;
  }

  public async resetPassword(data: ResetPasswordRequest): Promise<ResetPasswordResponse> {
    const response = await this.client.post<ResetPasswordResponse>('/auth/reset-password', data);
    return response.data;
  }

  public logout(): void {
    this.removeToken();
  }

  // User endpoints
  public async getProfile(): Promise<UserProfile> {
    const response = await this.client.get<UserProfile>('/users/me');
    return response.data;
  }

  public async updateProfile(data: { telefono?: string; ciudad_departamento?: string }): Promise<UserProfile> {
    const response = await this.client.patch<UserProfile>('/users/me', data);
    return response.data;
  }

  public async updatePassword(data: UpdatePasswordRequest): Promise<{ message: string }> {
    const response = await this.client.patch<{ message: string }>('/users/me/password', data);
    return response.data;
  }

  // Location endpoints
  public async getCities(): Promise<Array<{ valor: string; ciudad: string; departamento: string }>> {
    const response = await this.client.get(`/locations/cities`);
    return response.data;
  }

  public async getBanks(): Promise<Array<{ id: number; nombre: string }>> {
    const response = await this.client.get(`/locations/banks`);
    return response.data;
  }

  // Documents & Analysis endpoints
  public async uploadDocument(file: File, password?: string): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (password) {
      formData.append('password', password);
    }
    const response = await this.client.post<DocumentUploadResponse>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  public async extractDocumentData(documentId: string): Promise<ExtractDataResponse> {
    const response = await this.client.post<ExtractDataResponse>(`/documents/${documentId}/extract`);
    return response.data;
  }

  public async createAnalysis(data: CreateAnalysisRequest): Promise<CreateAnalysisResponse> {
    const response = await this.client.post<CreateAnalysisResponse>('/analyses', data);
    return response.data;
  }

  public async createAdminClientAnalysis(data: AdminClientAnalysisUploadRequest): Promise<CreateAnalysisResponse> {
    const formData = new FormData();
    formData.append('customer_full_name', data.customer_full_name);
    formData.append('customer_id_number', data.customer_id_number);
    formData.append('customer_email', data.customer_email);
    formData.append('customer_phone', data.customer_phone);
    formData.append('ingresos_mensuales', String(data.ingresos_mensuales));
    if (data.capacidad_pago_max !== undefined) {
      formData.append('capacidad_pago_max', String(data.capacidad_pago_max));
    }
    if (data.tipo_contrato_laboral) {
      formData.append('tipo_contrato_laboral', data.tipo_contrato_laboral);
    }
    formData.append('banco_id', String(data.banco_id));
    if (data.opcion_abono_1 !== undefined) {
      formData.append('opcion_abono_1', String(data.opcion_abono_1));
    }
    if (data.opcion_abono_2 !== undefined) {
      formData.append('opcion_abono_2', String(data.opcion_abono_2));
    }
    if (data.opcion_abono_3 !== undefined) {
      formData.append('opcion_abono_3', String(data.opcion_abono_3));
    }
    if (data.password) {
      formData.append('password', data.password);
    }
    formData.append('file', data.file);

    const response = await this.client.post<CreateAnalysisResponse>('/admin/clients/upload-analysis', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  public async createAdminManualProjection(data: AdminManualProjectionRequest): Promise<CreateAnalysisResponse> {
    const formData = new FormData();
    formData.append('customer_full_name', data.customer_full_name);
    formData.append('customer_id_number', data.customer_id_number);
    formData.append('customer_email', data.customer_email);
    formData.append('customer_phone', data.customer_phone);
    formData.append('ingresos_mensuales', String(data.ingresos_mensuales));
    if (data.capacidad_pago_max !== undefined) formData.append('capacidad_pago_max', String(data.capacidad_pago_max));
    if (data.tipo_contrato_laboral) formData.append('tipo_contrato_laboral', data.tipo_contrato_laboral);
    formData.append('banco_id', String(data.banco_id));
    if (data.opcion_abono_1 !== undefined) formData.append('opcion_abono_1', String(data.opcion_abono_1));
    if (data.opcion_abono_2 !== undefined) formData.append('opcion_abono_2', String(data.opcion_abono_2));
    if (data.opcion_abono_3 !== undefined) formData.append('opcion_abono_3', String(data.opcion_abono_3));
    formData.append('numero_credito', data.numero_credito);
    formData.append('sistema_amortizacion', data.sistema_amortizacion);
    if (data.plan_credito) formData.append('plan_credito', data.plan_credito);
    formData.append('valor_prestado_inicial', String(data.valor_prestado_inicial));
    if (data.fecha_desembolso) formData.append('fecha_desembolso', data.fecha_desembolso);
    formData.append('fecha_extracto', data.fecha_extracto);
    formData.append('plazo_total_meses', String(data.plazo_total_meses));
    formData.append('cuotas_pactadas', String(data.cuotas_pactadas));
    formData.append('cuotas_pagadas', String(data.cuotas_pagadas));
    formData.append('cuotas_pendientes', String(data.cuotas_pendientes));
    if (data.tasa_interes_pactada_ea !== undefined) formData.append('tasa_interes_pactada_ea', String(data.tasa_interes_pactada_ea));
    formData.append('tasa_interes_cobrada_ea', String(data.tasa_interes_cobrada_ea));
    if (data.tasa_interes_subsidiada_ea !== undefined) formData.append('tasa_interes_subsidiada_ea', String(data.tasa_interes_subsidiada_ea));
    if (data.tasa_mora_pactada_ea !== undefined) formData.append('tasa_mora_pactada_ea', String(data.tasa_mora_pactada_ea));
    if (data.valor_cuota_sin_seguros !== undefined) formData.append('valor_cuota_sin_seguros', String(data.valor_cuota_sin_seguros));
    formData.append('valor_cuota_con_seguros', String(data.valor_cuota_con_seguros));
    if (data.beneficio_frech_mensual !== undefined) formData.append('beneficio_frech_mensual', String(data.beneficio_frech_mensual));
    if (data.valor_cuota_con_subsidio !== undefined) formData.append('valor_cuota_con_subsidio', String(data.valor_cuota_con_subsidio));
    formData.append('saldo_capital_pesos', String(data.saldo_capital_pesos));
    if (data.total_por_pagar !== undefined) formData.append('total_por_pagar', String(data.total_por_pagar));
    if (data.saldo_capital_uvr !== undefined) formData.append('saldo_capital_uvr', String(data.saldo_capital_uvr));
    if (data.valor_uvr_fecha_extracto !== undefined) formData.append('valor_uvr_fecha_extracto', String(data.valor_uvr_fecha_extracto));
    if (data.valor_cuota_uvr !== undefined) formData.append('valor_cuota_uvr', String(data.valor_cuota_uvr));
    if (data.seguro_vida !== undefined) formData.append('seguro_vida', String(data.seguro_vida));
    if (data.seguro_incendio !== undefined) formData.append('seguro_incendio', String(data.seguro_incendio));
    if (data.seguro_terremoto !== undefined) formData.append('seguro_terremoto', String(data.seguro_terremoto));
    if (data.capital_pagado_periodo !== undefined) formData.append('capital_pagado_periodo', String(data.capital_pagado_periodo));
    if (data.intereses_corrientes_periodo !== undefined) formData.append('intereses_corrientes_periodo', String(data.intereses_corrientes_periodo));
    if (data.intereses_mora !== undefined) formData.append('intereses_mora', String(data.intereses_mora));
    if (data.otros_cargos !== undefined) formData.append('otros_cargos', String(data.otros_cargos));
    if (data.password) formData.append('password', data.password);
    formData.append('file', data.file);

    const response = await this.client.post<CreateAnalysisResponse>('/admin/analyses/manual-projection', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  public async getAnalysisSummary(analysisId: string): Promise<AnalysisSummary> {
    const response = await this.client.get<AnalysisSummary>(`/analyses/${analysisId}/summary`);
    return response.data;
  }

  public async getAnalysisDetail(analysisId: string): Promise<AnalysisDetailResponse> {
    const response = await this.client.get<AnalysisDetailResponse>(`/analyses/${analysisId}`);
    return response.data;
  }

  public async generateProjections(analysisId: string, opciones: ProjectionRequestOption[]): Promise<ProjectionResponse[]> {
    const response = await this.client.post<ProjectionResponse[]>(`/analyses/${analysisId}/projections`, { opciones });
    return response.data;
  }

  public async updateAnalysisManual(analysisId: string, data: UpdateManualFieldsRequest): Promise<CreateAnalysisResponse> {
    const response = await this.client.patch<CreateAnalysisResponse>(`/analyses/${analysisId}/manual`, data);
    return response.data;
  }

  // User Estudios/History endpoints
  public async getEstudiosHistorial(params?: { page?: number; limit?: number; status?: string }): Promise<EstudiosHistorialResponse> {
    const response = await this.client.get<EstudiosHistorialResponse>('/users/me/estudios', { params });
    return response.data;
  }

  // Admin analyses endpoints
  public async getAdminAnalyses(params?: AdminAnalysesParams): Promise<AdminAnalysesResponse> {
    const response = await this.client.get<AdminAnalysesResponse>('/admin/analyses', { params });
    return response.data;
  }

  public async getAdminAnalysisSummary(analysisId: string): Promise<AnalysisSummary> {
    const response = await this.client.get<AnalysisSummary>(`/admin/analyses/${analysisId}/summary`);
    return response.data;
  }

  public async getAdminAnalysisDetail(analysisId: string): Promise<AdminAnalysisDetailResponse> {
    const response = await this.client.get<AdminAnalysisDetailResponse>(`/admin/analyses/${analysisId}`);
    return response.data;
  }

  public async updateAdminAnalysis(analysisId: string, data: AdminUpdateAnalysisRequest): Promise<AdminAnalysisDetailResponse> {
    const response = await this.client.patch<AdminAnalysisDetailResponse>(`/admin/analyses/${analysisId}`, data);
    return response.data;
  }

  public async calculateAdminProjections(
    analysisId: string,
    data: AdminCalculateProjectionsRequest
  ): Promise<PropuestaCompletaResponse | AdminProjectionResponse[]> {
    const response = await this.client.post<PropuestaCompletaResponse | AdminProjectionResponse[]>(`/admin/analyses/${analysisId}/calculate`, data);
    return response.data;
  }

  public async downloadAdminDocument(documentId: string): Promise<Blob> {
    const response = await this.client.get(`/admin/documents/${documentId}/download`, {
      responseType: 'blob'
    });
    return response.data;
  }

  public async downloadAdminProposalPdf(analysisId: string): Promise<Blob> {
    const response = await this.client.get(`/admin/analyses/${analysisId}/proposal/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Document download - returns the download URL
  public getDocumentDownloadUrl(documentId: string): string {
    const token = this.getToken();
    return `${API_BASE_URL}/documents/${documentId}/download?token=${token}`;
  }

  // Download document as blob (for programmatic download)
  public async downloadDocument(documentId: string): Promise<Blob> {
    const response = await this.client.get(`/documents/${documentId}/download`, {
      responseType: 'blob'
    });
    return response.data;
  }

  public async getIndicadorUVR(fecha?: string): Promise<UVRResponse> {
    const response = await this.client.get<UVRResponse>('/indicadores/uvr', {
      params: fecha ? { fecha } : undefined,
    });
    return response.data;
  }

  public async getIndicadorIPC(anio?: number, mes?: number): Promise<IPCResponse> {
    const response = await this.client.get<IPCResponse>('/indicadores/ipc', {
      params: anio && mes ? { anio, mes } : undefined,
    });
    return response.data;
  }

  public async getIndicadorDTF(fecha?: string): Promise<DTFResponse> {
    const response = await this.client.get<DTFResponse>('/indicadores/dtf', {
      params: fecha ? { fecha } : undefined,
    });
    return response.data;
  }

  public async getIndicadoresConsolidados(): Promise<IndicadoresConsolidadosResponse> {
    const response = await this.client.get<IndicadoresConsolidadosResponse>('/indicadores/consolidados');
    return response.data;
  }

  public async getHistoricoUVR(fechaInicio: string, fechaFin: string): Promise<HistoricoUVRResponse> {
    const response = await this.client.get<HistoricoUVRResponse>('/indicadores/uvr/historico', {
      params: {
        fecha_inicio: fechaInicio,
        fecha_fin: fechaFin,
      },
    });
    return response.data;
  }

  public async convertirUVR(data: ConversionUVRRequest): Promise<ConversionUVRResponse> {
    const response = await this.client.post<ConversionUVRResponse>('/indicadores/uvr/convertir', data);
    return response.data;
  }

  public async proyectarUVR(data: ProyeccionUVRRequest): Promise<ProyeccionUVRResponse> {
    const response = await this.client.post<ProyeccionUVRResponse>('/indicadores/uvr/proyectar', data);
    return response.data;
  }
}

export const apiClient = new ApiClient();
