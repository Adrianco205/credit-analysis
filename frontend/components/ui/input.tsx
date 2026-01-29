import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility to merge tailwind classes safely
 * Definida aquí para que el archivo sea autoportante, 
 * aunque puedes usar la de @/lib/utils si prefieres.
 */
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  containerClassName?: string;
  showPasswordToggle?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      className,
      containerClassName,
      leftIcon,
      rightIcon,
      type = 'text',
      disabled,
      id,
      name,
      showPasswordToggle = false,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = React.useState(false);
    const inputId = id || name;
    
    // Lógica para alternar visibilidad de contraseña
    const inputType = showPasswordToggle ? (showPassword ? 'text' : 'password') : type;

    return (
      <div className={cn('w-full flex flex-col gap-1.5', containerClassName)}>
        {/* Label con estados de enfoque y error */}
        {label && (
          <label
            htmlFor={inputId}
            className={cn(
              "text-sm font-semibold ml-1 transition-colors duration-200",
              disabled ? "text-gray-400" : "text-verde-bosque",
              error ? "text-red-600" : "hover:text-verde-hoja"
            )}
          >
            {label}
          </label>
        )}
        
        <div className="relative group">
          {leftIcon && (
            <div className={cn(
              "absolute left-4 top-1/2 -translate-y-1/2 transition-colors duration-200 z-10",
              error ? "text-red-400" : "text-gray-400 group-focus-within:text-verde-hoja"
            )}>
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            type={inputType}
            id={inputId}
            name={name}
            disabled={disabled}
            className={cn(
              // Estilos Base
              'w-full px-4 py-2.5 text-sm md:text-base border rounded-xl transition-all duration-200 outline-none',
              'bg-white text-gray-900',
              // Placeholder
              'placeholder:text-gray-400 placeholder:font-normal',
              // Focus state - Anillo sutil
              'focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja focus:bg-white',
              // Hover state
              'hover:border-gray-300 hover:bg-gray-50/50',
              // Error state
              error 
                ? 'border-red-400 focus:ring-red-200 focus:border-red-500 bg-red-50/30' 
                : 'border-gray-300',
              // Disabled state
              'disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed disabled:border-gray-200',
              // Padding dinámico según iconos (FIX para solapamiento)
              leftIcon && 'pl-12',
              (rightIcon || showPasswordToggle) && 'pr-12',
              className
            )}
            {...props}
          />
          
          {/* Botón de Password Toggle */}
          {showPasswordToggle && (
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-verde-hoja transition-colors duration-200 p-1"
              tabIndex={-1}
            >
              {showPassword ? (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              )}
            </button>
          )}
          
          {/* Icono Derecho (Solo si no hay toggle de password para evitar colisiones) */}
          {rightIcon && !showPasswordToggle && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-verde-hoja transition-colors duration-200">
              {rightIcon}
            </div>
          )}
        </div>

        {/* Mensajes de retroalimentación (Error o Helper) con altura mínima para evitar saltos de layout */}
        <div className="min-h-[20px] ml-1">
          {error ? (
            <p className="text-xs md:text-sm text-red-600 font-medium flex items-center gap-1.5 animate-in fade-in slide-in-from-top-1">
              <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </p>
          ) : helperText ? (
            <p className="text-xs text-gray-600">{helperText}</p>
          ) : null}
        </div>
      </div>
    );
  }
);

Input.displayName = 'Input';