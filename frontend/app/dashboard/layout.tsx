'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

const Sidebar = dynamic(() => import('@/components/dashboard/Sidebar').then(m => m.Sidebar), {
  ssr: false,
});

const Navbar = dynamic(() => import('@/components/dashboard/Navbar').then(m => m.Navbar), {
  ssr: false,
});

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const isMobile = window.innerWidth < 1024;
    if (!isMobile) {
      document.body.style.overflow = '';
      return;
    }

    if (isSidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isSidebarOpen]);

  return (
    <div className="min-h-screen bg-[var(--gray-50)] font-sans">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <div className="w-full lg:pl-[270px] min-h-screen transition-all duration-300">
        <Navbar onMenuClick={() => setIsSidebarOpen(true)} />
        <main className="w-full min-h-[calc(100vh-4rem)]">
           <div className="w-full p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
              {children}
           </div>
        </main>
      </div>
    </div>
  );
}
