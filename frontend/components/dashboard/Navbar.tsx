'use client';

import { Bell, Menu, Search } from 'lucide-react';

export function Navbar() {
  return (
    <header className="fixed top-0 right-0 left-[270px] h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 z-40 transition-all duration-300 shadow-sm">
       <div className="flex items-center gap-4">
           {/* Mobile Toggle (Hidden for now as we focus on Deskop 270px) */}
           <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-full lg:hidden">
               <Menu size={24} />
           </button>
           <h2 className="text-xl font-semibold text-[var(--verde-bosque)]">Panel de Control</h2>
       </div>

       <div className="flex items-center gap-6">
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
