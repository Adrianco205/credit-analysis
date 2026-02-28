import { type ClassValue, clsx } from 'clsx';

const COP_CURRENCY_FORMATTER = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Utility para combinar clases de Tailwind CSS
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Formatea números de identificación (cédula)
 */
export function formatIdentificacion(value: string): string {
  // Elimina caracteres no numéricos
  const numbers = value.replace(/\D/g, '');
  
  // Limita a 10 dígitos
  return numbers.slice(0, 10);
}

/**
 * Valida formato de email
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Valida formato de teléfono colombiano
 */
export function isValidPhone(phone: string): boolean {
  // Acepta formato: +57 3XX XXXXXXX o 3XXXXXXXXX
  const phoneRegex = /^(\+57)?3\d{9}$/;
  return phoneRegex.test(phone.replace(/\s/g, ''));
}

/**
 * Formatea número de teléfono
 */
export function formatPhone(value: string): string {
  const numbers = value.replace(/\D/g, '');
  
  if (numbers.length <= 3) return numbers;
  if (numbers.length <= 6) return `${numbers.slice(0, 3)} ${numbers.slice(3)}`;
  return `${numbers.slice(0, 3)} ${numbers.slice(3, 6)} ${numbers.slice(6, 10)}`;
}

export function formatCopCurrency(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-';
  }
  return COP_CURRENCY_FORMATTER.format(Number(value));
}
