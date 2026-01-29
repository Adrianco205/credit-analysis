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
  ApiError,
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
      timeout: 10000,
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
          const apiError: ApiError = error.response.data || {
            error: 'unknown_error',
            message: 'Ha ocurrido un error desconocido',
            status_code: error.response.status,
          };
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

  public logout(): void {
    this.removeToken();
  }

  // User endpoints
  public async getProfile(): Promise<UserProfile> {
    const response = await this.client.get<UserProfile>('/users/me');
    return response.data;
  }

  public async updatePassword(data: UpdatePasswordRequest): Promise<{ message: string }> {
    const response = await this.client.patch<{ message: string }>('/users/me/password', data);
    return response.data;
  }

  // Location endpoints
  public async searchCities(query: string): Promise<Array<{ id: number; nombre: string; departamento: string }>> {
    const response = await this.client.get(`/locations/cities`, {
      params: { q: query, limit: 50 }
    });
    return response.data;
  }
}

export const apiClient = new ApiClient();
