import React from 'react';
import { Leaf } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen gradient-eco-subtle flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo y Título */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-eco-primary shadow-eco-lg mb-4">
            <Leaf className="w-8 h-8 text-white" strokeWidth={2.5} />
          </div>
          <h1 className="text-3xl font-bold text-verde-bosque tracking-tight">
            EcoFinanzas
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Análisis inteligente de crédito hipotecario
          </p>
        </div>

        {/* Contenido (formulario) */}
        {children}

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-500">
            © 2026 EcoFinanzas. Todos los derechos reservados.
          </p>
        </div>
      </div>
    </div>
  );
};
