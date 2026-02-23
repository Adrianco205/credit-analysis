'use client';

import { Menu } from 'lucide-react';

interface NavbarProps {
  onMenuClick: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
  return (
    <header className="sticky top-0 h-16 bg-white/85 supports-[backdrop-filter]:bg-white/70 backdrop-blur-md border-b border-gray-200/80 flex items-center px-4 sm:px-6 lg:px-8 z-30 transition-all duration-300 shadow-sm">
       <div className="flex items-center gap-4">
           <button
             onClick={onMenuClick}
             className="p-2 text-gray-500 hover:bg-gray-100 rounded-full lg:hidden"
             aria-label="Abrir menú lateral"
           >
               <Menu size={24} />
           </button>
           <h2 className="text-base sm:text-lg lg:text-xl font-semibold text-[var(--verde-bosque)]">Panel de Control</h2>
       </div>
    </header>
  );
}
