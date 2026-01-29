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
  ciudad_id?: number;
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
  nombres: string;
  primer_apellido: string;
  segundo_apellido?: string;
  apellidos: string;  // Computed field from backend
  genero?: string;
  email: string;
  telefono?: string;
  status: string;
  email_verificado: boolean;
}

export interface UpdatePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ApiError {
  error: string;
  message: string;
  status_code: number;
  detail?: string | object;
}
