'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { UserProfile, EstudiosHistorialResponse } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader } from '@/components/ui/card';
import { Lock, Phone, MapPin, User as UserIcon, Shield, Mail, BadgeCheck, FileText, History, TrendingUp, Clock } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function DashboardPage() {
    const router = useRouter();
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [successMsg, setSuccessMsg] = useState('');

    // Form states
    const [phone, setPhone] = useState('');
    const [ciudadDepartamento, setCiudadDepartamento] = useState('');
    const [cities, setCities] = useState<Array<{ valor: string; ciudad: string; departamento: string }>>([]);
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');

    // Stats for welcome section
    const [totalAnalisis, setTotalAnalisis] = useState(0);
    const [ultimoAnalisis, setUltimoAnalisis] = useState<string | null>(null);

    useEffect(() => {
        loadProfile();
        apiClient.getCities().then(setCities).catch(console.error);
    }, []);

    useEffect(() => {
        if (user && user.rol === 'CLIENT') {
            loadStats();
        }
    }, [user]);

    const loadProfile = async () => {
        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                router.push('/auth/login');
                return;
            }
            const u = await apiClient.getProfile();
            setUser(u);
            setPhone(u.telefono || '');
            setCiudadDepartamento(u.ciudad_departamento || '');
        } catch (err: any) {
            console.error('Error loading profile:', err?.message || err?.error || JSON.stringify(err));
            setError(err?.message || 'No se pudo cargar el perfil');
            if (err?.status_code === 401) {
                 router.push('/auth/login');
            }
        } finally {
            setLoading(false);
        }
    };

    const loadStats = async () => {
        try {
            const response = await apiClient.getEstudiosHistorial({ page: 1, limit: 1 });
            setTotalAnalisis(response.total);
            if (response.estudios.length > 0 && response.estudios[0].fecha_subida) {
                setUltimoAnalisis(response.estudios[0].fecha_subida);
            }
        } catch (err) {
            console.error('Error loading stats:', err);
        }
    };

    const handleUpdateContact = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccessMsg('');
        try {
            await apiClient.updateProfile({ 
                telefono: phone, 
                ciudad_departamento: ciudadDepartamento || undefined 
            });
            setSuccessMsg('Información de contacto actualizada correctamente');
            loadProfile(); // Refresh
        } catch (err: any) {
             setError(err.message || 'Error al actualizar información');
        }
    };

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccessMsg('');
        try {
            await apiClient.updatePassword({ 
                current_password: currentPassword,
                new_password: newPassword 
            });
            setSuccessMsg('Contraseña actualizada correctamente');
            setCurrentPassword('');
            setNewPassword('');
        } catch (err: any) {
            setError(err.message || 'Error al actualizar contraseña');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]"></div>
            </div>
        );
    }

    if (!user) return <div className="text-red-500">Error al cargar usuario. Intente recargar.</div>;

    return (
        <div className="space-y-8">
            <h1 className="text-3xl font-bold text-[var(--verde-bosque)] border-b pb-4 border-gray-200">
                Mi Perfil
            </h1>

            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-200 flex items-center gap-2">
                    <span className="font-bold">Error:</span> {error}
                </div>
            )}

            {successMsg && (
                <div className="bg-green-50 text-green-600 p-4 rounded-lg border border-green-200 flex items-center gap-2">
                    <BadgeCheck size={20} />
                    <span className="font-bold">Éxito:</span> {successMsg}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* User Info Card */}
                <Card className="shadow-lg border-t-4 border-[var(--verde-hoja)]">
                    <CardHeader>
                        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
                            <UserIcon className="text-[var(--verde-hoja)]" />
                            Información Personal
                        </h2>
                    </CardHeader>
                    
                    <div className="space-y-4">
                        <div className="flex border-b border-gray-100 py-3">
                            <span className="w-1/3 text-gray-500 font-medium">Nombre Completo</span>
                            <span className="w-2/3 font-semibold text-gray-800">
                                {user.nombres} {user.primer_apellido} {user.segundo_apellido}
                            </span>
                        </div>
                        
                        <div className="flex border-b border-gray-100 py-3">
                            <span className="w-1/3 text-gray-500 font-medium flex items-center gap-2">
                                <Shield size={16} /> Identificación
                            </span>
                            <span className="w-2/3 text-gray-800">
                                {user.identificacion} <span className="text-xs bg-gray-200 px-2 py-0.5 rounded text-gray-600 ml-2">{user.tipo_identificacion}</span>
                            </span>
                        </div>

                        <div className="flex border-b border-gray-100 py-3">
                            <span className="w-1/3 text-gray-500 font-medium flex items-center gap-2">
                                <Mail size={16} /> Email
                            </span>
                            <span className="w-2/3 text-gray-800">{user.email}</span>
                        </div>

                        <div className="flex border-b border-gray-100 py-3">
                            <span className="w-1/3 text-gray-500 font-medium flex items-center gap-2">
                                <BadgeCheck size={16} /> Rol
                            </span>
                            <span className="w-2/3 text-gray-800 font-medium bg-[var(--verde-suave)] px-3 py-1 rounded-full inline-block text-[var(--verde-bosque)] text-sm">
                                {user.rol || 'N/A'}
                            </span>
                        </div>

                         <div className="flex py-3">
                            <span className="w-1/3 text-gray-500 font-medium flex items-center gap-2">
                                <MapPin size={16} /> Ubicación
                            </span>
                            <span className="w-2/3 text-gray-800">
                                {user.ciudad_departamento || 'No registrada'}
                            </span>
                        </div>
                    </div>
                </Card>

                {/* Forms Column */}
                <div className="space-y-8">
                    {/* Update Contact */}
                    <Card variant="bordered">
                        <CardHeader>
                             <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
                                <Phone className="text-[var(--verde-hoja)]" />
                                Datos de Contacto
                            </h2>
                        </CardHeader>
                        <form onSubmit={handleUpdateContact} className="space-y-4">
                            <Input 
                                label="Número de Teléfono / Celular"
                                value={phone}
                                onChange={(e) => setPhone(e.target.value)}
                                placeholder="+57 300 123 4567"
                            />
                            
                            <div>
                                <label className="block text-sm font-semibold text-verde-bosque mb-2 ml-1">
                                    Ciudad / Departamento
                                </label>
                                <select
                                    className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja outline-none transition-all text-sm md:text-base hover:border-gray-300 text-gray-900 font-medium"
                                    value={ciudadDepartamento}
                                    onChange={(e) => setCiudadDepartamento(e.target.value)}
                                >
                                    <option value="">Selecciona tu ciudad...</option>
                                    {cities.map((c) => (
                                        <option key={c.valor} value={c.valor}>
                                            {c.ciudad}, {c.departamento}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex justify-end">
                                <Button type="submit" variant="secondary" size="sm">
                                    Actualizar Datos
                                </Button>
                            </div>
                        </form>
                    </Card>

                    {/* Change Password */}
                    <Card variant="bordered">
                        <CardHeader>
                             <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
                                <Lock className="text-[var(--verde-hoja)]" />
                                Seguridad
                            </h2>
                        </CardHeader>
                        <form onSubmit={handleChangePassword} className="space-y-4">
                            <Input 
                                label="Contraseña Actual"
                                type="password"
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                showPasswordToggle
                            />
                             <Input 
                                label="Nueva Contraseña"
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                showPasswordToggle
                                helperText="Mínimo 8 caracteres"
                            />
                            <div className="flex justify-end">
                                <Button type="submit" variant="primary" size="sm">
                                    Cambiar Contraseña
                                </Button>
                            </div>
                        </form>
                    </Card>
                </div>
            </div>

            {/* Welcome Section - Only for CLIENTs */}
            {user.rol === 'CLIENT' && (
                <Card className="shadow-lg border-t-4 border-[var(--verde-hoja)] bg-gradient-to-r from-[var(--verde-suave)]/10 to-white">
                    <div className="space-y-6">
                        {/* Welcome Header */}
                        <div className="flex items-center gap-4">
                            <div className="w-14 h-14 bg-[var(--verde-hoja)] rounded-xl flex items-center justify-center shadow-lg">
                                <TrendingUp className="text-white" size={28} />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-[var(--verde-bosque)]">
                                    ¡Bienvenido, {user.nombres}!
                                </h2>
                                <p className="text-gray-600">Tu panel de control de EcoFinanzas</p>
                            </div>
                        </div>

                        {/* Quick Stats */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                        <FileText size={20} className="text-blue-600" />
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-gray-800">{totalAnalisis}</p>
                                        <p className="text-xs text-gray-500">Análisis realizados</p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                        <Clock size={20} className="text-green-600" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-800">
                                            {ultimoAnalisis 
                                                ? new Date(ultimoAnalisis).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
                                                : 'Sin análisis'
                                            }
                                        </p>
                                        <p className="text-xs text-gray-500">Último análisis</p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                                        <History size={20} className="text-purple-600" />
                                    </div>
                                    <div>
                                        <Link href="/dashboard/historial" className="text-sm font-semibold text-[var(--verde-hoja)] hover:underline">
                                            Ver historial →
                                        </Link>
                                        <p className="text-xs text-gray-500">Acceso rápido</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </Card>
            )}
        </div>
    );
}
