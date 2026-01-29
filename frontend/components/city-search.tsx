'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Loader2, X } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

export interface Ciudad {
  id: number;
  nombre: string;
  departamento: string;
}

interface CitySearchProps {
  value?: number;
  onChange: (ciudadId: number, ciudadNombre: string) => void;
  error?: string;
  disabled?: boolean;
}

export const CitySearch: React.FC<CitySearchProps> = ({
  value,
  onChange,
  error,
  disabled = false,
}) => {
  const [query, setQuery] = useState('');
  const [ciudades, setCiudades] = useState<Ciudad[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCity, setSelectedCity] = useState<Ciudad | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Buscar ciudades cuando cambia el query
  useEffect(() => {
    const searchCities = async () => {
      setLoading(true);
      try {
        // Si query está vacío, traer todas las ciudades
        const response = await apiClient.searchCities(query);
        console.log('Cities response:', response);
        setCiudades(Array.isArray(response) ? response : []);
      } catch (error) {
        console.error('Error searching cities:', error);
        setCiudades([]);
      } finally {
        setLoading(false);
      }
    };

    if (!isOpen) return;
    const debounce = setTimeout(searchCities, 300);
    return () => clearTimeout(debounce);
  }, [query, isOpen]);

  const handleSelect = (ciudad: Ciudad) => {
    setSelectedCity(ciudad);
    setQuery(`${ciudad.nombre}, ${ciudad.departamento}`);
    setIsOpen(false);
    onChange(ciudad.id, ciudad.nombre);
  };

  const handleClear = () => {
    setSelectedCity(null);
    setQuery('');
    setCiudades([]);
    onChange(0, '');
  };

  return (
    <div ref={wrapperRef} className="relative w-full flex flex-col gap-1.5">
      <label className="block text-sm font-semibold text-gray-700 ml-1">
        Ciudad *
      </label>
      
      <div className="relative group">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Ej: Medellín"
          disabled={disabled}
          className={`
            w-full px-4 py-3 text-sm md:text-base border rounded-xl 
            transition-all duration-200 outline-none bg-white text-gray-900
            placeholder:text-gray-400 placeholder:font-normal
            focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja focus:bg-white
            hover:border-gray-300 hover:bg-gray-50/50
            ${error ? 'border-red-400 focus:ring-red-200 focus:border-red-500 bg-red-50/30' : 'border-gray-300'}
            ${disabled ? 'bg-gray-100 text-gray-500 cursor-not-allowed border-gray-200' : ''}
          `}
        />        {loading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <Loader2 size={20} className="animate-spin text-verde-hoja" />
          </div>
        )}

        {!loading && query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
            tabIndex={-1}
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Dropdown de resultados */}
      {isOpen && ciudades.length > 0 && !disabled && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
          {ciudades.map((ciudad) => (
            <button
              key={ciudad.id}
              type="button"
              onClick={() => handleSelect(ciudad)}
              className="w-full px-4 py-3 text-left hover:bg-verde-bosque/5 transition-colors border-b border-gray-100 last:border-b-0 flex items-center gap-3 group"
            >
              <MapPin size={18} className="text-verde-bosque flex-shrink-0 group-hover:text-verde-hoja" />
              <div>
                <p className="font-medium text-gray-900 group-hover:text-verde-bosque">
                  {ciudad.nombre}
                </p>
                <p className="text-xs text-gray-500">{ciudad.departamento}</p>
              </div>
            </button>
          ))}
        </div>
      )}

      {isOpen && query.length > 0 && !loading && ciudades.length === 0 && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-lg p-4 text-center text-gray-500 text-sm">
          No se encontraron ciudades
        </div>
      )}

      {/* Error message */}
      <div className="min-h-[20px]">
        {error ? (
          <p className="text-xs md:text-sm text-red-600 flex items-center gap-1.5">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
};
