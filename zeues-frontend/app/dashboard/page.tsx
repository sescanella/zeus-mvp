'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { useSSE } from '@/lib/hooks/useSSE';
import type { SSEEvent } from '@/lib/types';

interface OccupiedSpool {
  tag_spool: string;
  worker_nombre: string;
  estado_detalle: string;
  fecha_ocupacion: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DashboardPage() {
  const router = useRouter();
  const [spools, setSpools] = useState<Map<string, OccupiedSpool>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [connected, setConnected] = useState(false);

  // Initial REST fetch
  useEffect(() => {
    const fetchOccupiedSpools = async () => {
      try {
        setLoading(true);
        setError('');

        const res = await fetch(`${API_URL}/api/dashboard/occupied`);
        if (!res.ok) {
          throw new Error('Error al cargar el dashboard');
        }

        const data: OccupiedSpool[] = await res.json();

        // Initialize map with fetched data
        const spoolsMap = new Map<string, OccupiedSpool>();
        data.forEach(spool => {
          spoolsMap.set(spool.tag_spool, spool);
        });

        setSpools(spoolsMap);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Error al cargar el dashboard';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchOccupiedSpools();
  }, []);

  // SSE real-time updates
  const { isConnected } = useSSE(`${API_URL}/api/sse/stream`, {
    onMessage: (event: SSEEvent) => {
      setSpools(prevSpools => {
        const newSpools = new Map(prevSpools);

        switch (event.type) {
          case 'TOMAR':
            // Add or update spool
            if (event.worker && event.estado_detalle) {
              newSpools.set(event.tag_spool, {
                tag_spool: event.tag_spool,
                worker_nombre: event.worker,
                estado_detalle: event.estado_detalle,
                fecha_ocupacion: event.timestamp
              });
            }
            break;

          case 'PAUSAR':
          case 'COMPLETAR':
            // Remove spool from occupied list
            newSpools.delete(event.tag_spool);
            break;

          case 'STATE_CHANGE':
            // Update estado_detalle if spool exists in map
            const existingSpool = newSpools.get(event.tag_spool);
            if (existingSpool && event.estado_detalle) {
              newSpools.set(event.tag_spool, {
                ...existingSpool,
                estado_detalle: event.estado_detalle
              });
            }
            break;
        }

        return newSpools;
      });
    },
    onConnectionChange: (isConnected) => {
      setConnected(isConnected);
    },
    onError: (error) => {
      console.error('SSE connection error:', error);
    }
  });

  // Convert map to array for rendering
  const spoolsList = Array.from(spools.values());

  // Loading state
  if (loading) {
    return (
      <div
        className="min-h-screen bg-[#001F3F] flex flex-col items-center justify-center"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      >
        <div className="mb-12">
          <Image
            src="/logos/logo-grisclaro-F8F9FA.svg"
            alt="Kronos Mining"
            width={200}
            height={80}
            priority
          />
        </div>
        <div className="text-white text-xl font-mono font-black">CARGANDO...</div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="min-h-screen bg-[#001F3F] flex flex-col items-center justify-center px-6"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      >
        <div className="mb-12">
          <Image
            src="/logos/logo-grisclaro-F8F9FA.svg"
            alt="Kronos Mining"
            width={200}
            height={80}
            priority
          />
        </div>
        <div className="text-white text-xl font-mono font-black mb-6">{error}</div>
        <Link
          href="/"
          className="px-6 py-3 bg-transparent border-2 border-white hover:bg-white/10 text-white text-lg font-black font-mono"
        >
          VOLVER
        </Link>
      </div>
    );
  }

  // Main dashboard view
  return (
    <div
      className="min-h-screen bg-[#001F3F]"
      style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    >
      {/* Connection Status */}
      <ConnectionStatus connected={isConnected} />

      {/* Header */}
      <div className="flex items-center justify-between px-8 pt-8 pb-6 border-b-4 border-white/30">
        <Link
          href="/"
          className="flex items-center gap-2 px-4 py-3 bg-transparent border-2 border-white hover:bg-white/10 transition-all"
        >
          <ArrowLeft size={24} strokeWidth={3} className="text-white" />
          <span className="text-sm font-black font-mono text-white tracking-wider">
            VOLVER
          </span>
        </Link>

        <Image
          src="/logos/logo-grisclaro-F8F9FA.svg"
          alt="Kronos Mining"
          width={200}
          height={80}
          priority
        />

        {/* Spacer for balance */}
        <div className="w-32"></div>
      </div>

      {/* Title */}
      <div className="px-10 narrow:px-5 py-6 border-b-4 border-white/30">
        <h2 className="text-3xl narrow:text-2xl font-black text-center text-white tracking-[0.25em] font-mono">
          CARRETES OCUPADOS
        </h2>
      </div>

      {/* Spools List */}
      <div className="p-8 narrow:p-5">
        {spoolsList.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center py-20">
            <div className="text-white text-2xl font-black font-mono mb-4 text-center">
              NO HAY CARRETES OCUPADOS ACTUALMENTE
            </div>
            <div className="text-white/60 text-lg font-mono text-center">
              Todos los carretes están disponibles
            </div>
          </div>
        ) : (
          // Spools grid
          <div className="grid gap-4">
            {spoolsList.map((spool) => (
              <div
                key={spool.tag_spool}
                className="bg-transparent border-4 border-white p-6 flex flex-col gap-3"
              >
                {/* TAG_SPOOL - Prominent */}
                <div className="text-3xl narrow:text-2xl font-black text-zeues-orange font-mono tracking-wide">
                  {spool.tag_spool}
                </div>

                {/* Worker Name */}
                <div className="flex items-baseline gap-2">
                  <span className="text-white/60 text-sm font-mono font-black">TRABAJADOR:</span>
                  <span className="text-white text-xl font-black font-mono">
                    {spool.worker_nombre}
                  </span>
                </div>

                {/* Estado Detalle */}
                <div className="flex items-baseline gap-2">
                  <span className="text-white/60 text-sm font-mono font-black">ESTADO:</span>
                  <span className="text-white text-lg font-mono">
                    {spool.estado_detalle}
                  </span>
                </div>

                {/* Fecha Ocupación */}
                <div className="flex items-baseline gap-2">
                  <span className="text-white/60 text-sm font-mono font-black">OCUPADO DESDE:</span>
                  <span className="text-white text-base font-mono">
                    {spool.fecha_ocupacion}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
