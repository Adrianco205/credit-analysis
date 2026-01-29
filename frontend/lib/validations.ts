import { z } from 'zod';

// Reusable rules
const numericRegex = /^\d+$/;
const cedulaRegex = /^\d{6,10}$/;
const nombresRegex = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/;
const apellidoRegex = /^\S+$/;
const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

/**
 * Esquema para el inicio de sesión
 */
export const loginSchema = z.object({
  identificacion: z
    .string()
    .trim()
    .min(1, 'La identificación es requerida')
    .regex(numericRegex, 'La identificación solo debe contener números')
    .min(6, 'Debe tener al menos 6 dígitos')
    .max(10, 'No puede tener más de 10 dígitos'),
  password: z
    .string()
    .min(1, 'La contraseña es requerida'),
});

export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Esquema para el registro de usuarios
 */
export const registerSchema = z.object({
  nombres: z
    .string()
    .trim()
    .min(2, 'El nombre es obligatorio')
    .regex(nombresRegex, 'Solo se permiten letras y espacios'),
  primer_apellido: z
    .string()
    .trim()
    .min(2, 'El primer apellido es obligatorio')
    .regex(apellidoRegex, 'El apellido no puede contener espacios'),
  segundo_apellido: z
    .string()
    .trim()
    .optional(),
  tipo_identificacion: z.enum(['CC', 'CE', 'NIT', 'PAS'], {
    errorMap: () => ({ message: "Selecciona un tipo de documento válido" })
  }),
  identificacion: z
    .string()
    .regex(cedulaRegex, 'La cédula debe tener entre 6 y 10 dígitos'),
  identificacion_confirm: z.string(),
  email: z.string().trim().email('Correo inválido').toLowerCase(),
  email_confirm: z.string().trim().toLowerCase(),
  telefono: z.string().regex(/^3\d{9}$/, 'Debe ser un celular válido (10 dígitos empezando por 3)'),
  telefono_confirm: z.string(),
  genero: z.string().min(1, 'Selecciona un género'),
  password: z
    .string()
    .min(8, 'Mínimo 8 caracteres')
    .regex(passwordRegex, 'Debe incluir mayúsculas, minúsculas y números'),
  confirm_password: z.string(),
  // Usamos coerce por si el valor viene como string desde el HTML
  ciudad_id: z.coerce.number({ invalid_type_error: "Debes seleccionar una ciudad" }).min(1, 'Selecciona una ciudad'),
  ciudad_nombre: z.string().optional(),
})
.refine((data) => data.identificacion === data.identificacion_confirm, {
  message: "Los números de identificación no coinciden",
  path: ["identificacion_confirm"],
})
.refine((data) => data.email === data.email_confirm, {
  message: "Los correos electrónicos no coinciden",
  path: ["email_confirm"],
})
.refine((data) => data.telefono === data.telefono_confirm, {
  message: "Los números de teléfono no coinciden",
  path: ["telefono_confirm"],
})
.refine((data) => data.password === data.confirm_password, {
  message: "Las contraseñas no coinciden",
  path: ["confirm_password"],
});

export type RegisterFormData = z.infer<typeof registerSchema>;

/**
 * Esquema para verificación OTP
 */
export const otpSchema = z.object({
  code: z
    .string()
    .min(1, 'El código es requerido')
    .length(6, 'El código debe tener 6 dígitos')
    .regex(numericRegex, 'El código solo debe contener números'),
});

export type OtpFormData = z.infer<typeof otpSchema>;