'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Home, LogOut, User, FileText, History, Sparkles, ChartColumn, X } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [userName, setUserName] = useState('');
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    const loadUserName = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        const user = await apiClient.getProfile();
        setUserName(user.nombres || '');
        setUserRole(user.rol || null);
      } catch {
        setUserName('');
        setUserRole(null);
      }
    };

    loadUserName();
  }, []);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => {
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  const handleLogout = () => {
    apiClient.logout();
    router.push('/auth/login');
  };

  const handleNavClick = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      onClose();
    }
  };

  const links = userRole === 'ADMIN'
    ? [
        { href: '/dashboard', label: 'Inicio', icon: Home },
        { href: '/dashboard/admin/analyses', label: 'Ver historial de análisis', icon: History },
        { href: '/dashboard/admin/proyecciones', label: 'Generar proyecciones', icon: Sparkles },
        { href: '/dashboard/admin/indicadores-financieros', label: 'Indicadores Financieros', icon: ChartColumn },
      ]
    : [
        { href: '/dashboard', label: 'Inicio', icon: Home },
        { href: '/dashboard/analysis/new', label: 'Analizar crédito', icon: FileText },
        { href: '/dashboard/historial', label: 'Historial de Análisis', icon: History },
      ];

  return (
    <>
      <div
        className={`fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 lg:hidden ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`fixed inset-y-0 left-0 w-[270px] bg-[var(--verde-bosque)] text-white z-50 shadow-2xl overflow-y-auto transform transition-transform duration-300 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
      <div className="h-full flex flex-col">
        {/* Header / Logo */}
        <div className="p-6 border-b border-[rgba(255,255,255,0.1)]">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-lg">
               <Image src="/assets/brand/logo.png" alt="EcoFinanzas" width={28} height={28} />
             </div>
             <h1 className="text-2xl font-bold tracking-tight">EcoFinanzas</h1>
             <button
               type="button"
               onClick={onClose}
               className="ml-auto p-2 rounded-lg hover:bg-white/10 lg:hidden"
               aria-label="Cerrar menú lateral"
             >
               <X size={18} />
             </button>
          </div>
        </div>

        {/* User Info Tile (Visual only) */}
        <div className="p-6 border-b border-[rgba(255,255,255,0.1)] bg-[rgba(0,0,0,0.1)] text-center">
            <div className="w-16 h-16 bg-white/20 rounded-full mx-auto mb-3 flex items-center justify-center border-2 border-[var(--verde-claro)]">
                <User size={32} className="text-white" />
            </div>
            <p className="font-medium text-sm text-[var(--verde-suave)]">
              {userName ? `Bienvenido ${userName}` : 'Bienvenido'}
            </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-4 space-y-2">
          {links.map((link) => {
            const Icon = link.icon;
            const isHomeLink = link.href === '/dashboard';
            const isActive = isHomeLink
              ? pathname === '/dashboard'
              : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link 
                key={link.href}
                href={link.href}
                onClick={handleNavClick}
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
    </>
  );
}
