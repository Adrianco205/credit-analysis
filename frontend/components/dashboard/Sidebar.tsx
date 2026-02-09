'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, LogOut, User, FileText, History } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { useRouter } from 'next/navigation';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    apiClient.logout();
    router.push('/auth/login');
  };

  const links = [
    { href: '/dashboard', label: 'Inicio', icon: Home },
    { href: '/dashboard/analysis/new', label: 'Analizar crédito', icon: FileText },
    { href: '/dashboard/historial', label: 'Historial de Análisis', icon: History },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full w-[270px] bg-[var(--verde-bosque)] text-white z-50 shadow-2xl overflow-y-auto">
      <div className="h-full flex flex-col">
        {/* Header / Logo */}
        <div className="p-6 border-b border-[rgba(255,255,255,0.1)]">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-[var(--verde-bosque)] font-bold text-xl shadow-lg">
               E
             </div>
             <h1 className="text-2xl font-bold tracking-tight">EcoFinanzas</h1>
          </div>
        </div>

        {/* User Info Tile (Visual only) */}
        <div className="p-6 border-b border-[rgba(255,255,255,0.1)] bg-[rgba(0,0,0,0.1)] text-center">
            <div className="w-16 h-16 bg-white/20 rounded-full mx-auto mb-3 flex items-center justify-center border-2 border-[var(--verde-claro)]">
                <User size={32} className="text-white" />
            </div>
            <p className="font-medium text-sm text-[var(--verde-suave)]">Bienvenido al Panel</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-4 space-y-2">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href;
            return (
              <Link 
                key={link.href}
                href={link.href}
                className={`flex items-center gap-4 px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive 
                    ? 'bg-[var(--verde-hoja)] text-white shadow-md translate-x-1 font-medium' 
                    : 'text-[var(--verde-suave)] hover:bg-[rgba(255,255,255,0.1)] hover:text-white'
                }`}
              >
                <Icon size={20} />
                <span className="">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer actions */}
        <div className="p-4 border-t border-[rgba(255,255,255,0.1)]">
            <button 
                onClick={handleLogout}
                className="flex items-center gap-4 px-4 py-3 w-full rounded-lg text-red-200 hover:bg-red-900/20 hover:text-red-100 transition-colors"
            >
                <LogOut size={20} />
                <span className="font-medium">Cerrar Sesión</span>
            </button>
        </div>
      </div>
    </aside>
  );
}
