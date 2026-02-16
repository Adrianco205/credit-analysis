'use client';

import { Bell, Menu, Search } from 'lucide-react';

interface NavbarProps {
  onMenuClick: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
  return (
    <header className="sticky top-0 h-16 bg-white/85 supports-[backdrop-filter]:bg-white/70 backdrop-blur-md border-b border-gray-200/80 flex items-center justify-between px-4 sm:px-6 lg:px-8 z-30 transition-all duration-300 shadow-sm">
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

       <div className="flex items-center gap-3 sm:gap-6">
           <div className="relative hidden md:block group">
               <input 
                 type="text" 
                 placeholder="Buscar en el sistema..." 
                 className="pl-10 pr-4 py-2 rounded-full bg-gray-100 border-none focus:ring-2 focus:ring-[var(--verde-hoja)] text-sm w-64 transition-all focus:w-80"
               />
               <Search className="absolute left-3 top-2.5 text-gray-400 group-focus-within:text-[var(--verde-hoja)]" size={18} />
           </div>
           
           <button className="relative p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors">
               <Bell size={24} />
               <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white animate-pulse"></span>
           </button>
       </div>
    </header>
  );
}
