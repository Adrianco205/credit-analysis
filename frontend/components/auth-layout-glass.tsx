'use client';

import React from 'react';
import Image from 'next/image';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen relative overflow-hidden gradient-eco-primary">
      {/* Formas abstractas de fondo */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 opacity-40">
          <Image
            src="/assets/images/background/grid.svg"
            alt=""
            fill
            className="object-cover"
            priority
          />
        </div>

        <div className="absolute -top-32 -right-24 w-[520px] h-[520px] opacity-70">
          <Image
            src="/assets/images/background/blob-1.svg"
            alt=""
            fill
            className="object-contain"
          />
        </div>

        <div className="absolute -bottom-24 -left-20 w-[420px] h-[420px] opacity-70">
          <Image
            src="/assets/images/background/blob-2.svg"
            alt=""
            fill
            className="object-contain"
          />
        </div>
      </div>

      {/* Contenedor principal */}
      <div className="relative z-10 flex min-h-screen items-center justify-center px-5 sm:px-8 lg:px-12 py-8 sm:py-12 lg:py-16">
        <div className="w-full max-w-xl sm:max-w-2xl lg:max-w-3xl">
          {/* Logo */}
          <div className="mb-6 sm:mb-8 text-center">
            <div className="inline-flex items-center gap-2 sm:gap-3 px-4 sm:px-6 py-2 sm:py-3 bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 hover:border-white/40 transition-colors">
              {/* Contenedor del Logo con bordes redondeados */}
              <div className="relative w-8 h-8 sm:w-10 sm:h-10 rounded-xl overflow-hidden shadow-sm">
                <Image
                  src="/assets/brand/logo.png"
                  alt="EcoFinanzas"
                  fill
                  className="object-cover"
                />
              </div>
              <span className="text-xl sm:text-2xl font-bold text-white">EcoFinanzas</span>
            </div>
          </div>

          {/* Contenedor con glassmorphism mejorado */}
          <div className="bg-white/95 backdrop-blur-md rounded-2xl sm:rounded-3xl shadow-eco-lg border border-white/80 p-6 sm:p-8 lg:p-10 border-b-2 border-b-verde-hoja/20">
            {children}
          </div>

          {/* Footer */}
          <div className="mt-5 sm:mt-6 text-center px-5">
            <p className="text-xs sm:text-sm text-white/80">
              © 2026 EcoFinanzas. Todos los derechos reservados.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};