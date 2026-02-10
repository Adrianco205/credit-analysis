'use client';

import dynamic from 'next/dynamic';

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
  return (
    <div className="min-h-screen bg-[var(--gray-50)] font-sans">
      <Sidebar />
      <Navbar />
      <main className="pl-[270px] pt-16 min-h-screen transition-all duration-300">
         <div className="p-8 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            {children}
         </div>
      </main>
    </div>
  );
}
