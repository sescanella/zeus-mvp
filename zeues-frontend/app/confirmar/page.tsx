'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, Button, Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';
import { iniciarAccion, completarAccion } from '@/lib/api';
import type { ActionPayload } from '@/lib/types';

function ConfirmarContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar';
  const { state, resetState } = useAppState();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorType, setErrorType] = useState<'network' | 'not-found' | 'validation' | 'forbidden' | 'server' | 'generic'>('generic');

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation || !state.selectedSpool || !tipo) {
      router.push('/');
    }
  }, [state, tipo, router]);

  const handleConfirm = async () => {
    try {
      setLoading(true);
      setError('');
      setErrorType('generic');

      // Construir payload para API
      const payload: ActionPayload = {
        worker_nombre: state.selectedWorker!,
        operacion: state.selectedOperation as 'ARM' | 'SOLD',
        tag_spool: state.selectedSpool!,
        // Solo incluir timestamp si es completar
        ...(tipo === 'completar' && { timestamp: new Date().toISOString() }),
      };

      // Llamar API según tipo de acción
      if (tipo === 'iniciar') {
        await iniciarAccion(payload);
      } else {
        await completarAccion(payload);
      }

      // Si llegamos aquí, la acción fue exitosa
      router.push('/exito');
    } catch (err) {
      // Manejar errores específicos según código HTTP
      const errorMessage = err instanceof Error ? err.message : 'Error al procesar acción';

      if (errorMessage.includes('red') || errorMessage.includes('conexión') || errorMessage.includes('Failed to fetch')) {
        setErrorType('network');
        setError('Error de conexión con el servidor. Verifica que el backend esté disponible.');
      } else if (errorMessage.includes('404') || errorMessage.includes('no encontrado')) {
        setErrorType('not-found');
        setError(errorMessage);
      } else if (errorMessage.includes('400') || errorMessage.includes('ya iniciada') || errorMessage.includes('ya completada') || errorMessage.includes('dependencias')) {
        setErrorType('validation');
        setError(errorMessage);
      } else if (errorMessage.includes('403') || errorMessage.includes('autorizado') || errorMessage.includes('completar')) {
        setErrorType('forbidden');
        setError(errorMessage);
      } else if (errorMessage.includes('503') || errorMessage.includes('Sheets') || errorMessage.includes('servidor')) {
        setErrorType('server');
        setError('Error del servidor de Google Sheets. Intenta más tarde.');
      } else {
        setErrorType('generic');
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (confirm('¿Seguro que quieres cancelar? Se perderá toda la información.')) {
      resetState();
      router.push('/');
    }
  };

  if (!state.selectedWorker || !state.selectedOperation || !state.selectedSpool) {
    return null;
  }

  const title = tipo === 'iniciar'
    ? `¿Confirmas INICIAR ${state.selectedOperation}?`
    : `¿Confirmas COMPLETAR ${state.selectedOperation}?`;

  const variant = tipo === 'iniciar' ? 'iniciar' : 'completar';

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6 text-xl"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-6">
          {title}
        </h1>

        <Card>
          <h2 className="text-xl font-bold mb-4">Resumen</h2>
          <div className="space-y-2 text-lg">
            <p>
              <strong>Trabajador:</strong> {state.selectedWorker}
            </p>
            <p>
              <strong>Operación:</strong>{' '}
              {state.selectedOperation === 'ARM' ? 'ARMADO (ARM)' : 'SOLDADO (SOLD)'}
            </p>
            <p>
              <strong>Spool:</strong> {state.selectedSpool}
            </p>
            {tipo === 'completar' && (
              <p>
                <strong>Fecha:</strong> {new Date().toLocaleDateString('es-ES')}
              </p>
            )}
          </div>
        </Card>

        {error && (
          <div className="mt-4">
            <ErrorMessage message={error} type={errorType} onRetry={errorType === 'server' || errorType === 'network' ? handleConfirm : undefined} />
          </div>
        )}

        {loading ? (
          <div className="mt-6">
            <Loading message="Actualizando Google Sheets..." />
          </div>
        ) : (
          <div className="space-y-3 mt-6">
            <Button variant={variant} onClick={handleConfirm}>
              ✓ CONFIRMAR
            </Button>
            <Button variant="cancel" onClick={handleCancel}>
              Cancelar
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ConfirmarPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ConfirmarContent />
    </Suspense>
  );
}
