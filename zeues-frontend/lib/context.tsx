'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Worker, BatchActionResponse } from './types';

interface AppState {
  allWorkers: Worker[];  // v2.0: Cache de todos los trabajadores (fetch en P1, filtrar en P2)
  selectedWorker: Worker | null;
  selectedOperation: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION' | null;  // v3.0: +REPARACION
  selectedTipo: 'iniciar' | 'completar' | 'cancelar' | null;  // v2.0: Añadido 'cancelar'
  selectedSpool: string | null;  // Single-select (backward compat)
  selectedSpools: string[];  // v2.0: Multiselect batch (array de TAGs)
  batchMode: boolean;  // v2.0: Flag si operación es batch
  batchResults: BatchActionResponse | null;  // v2.0: Resultados de batch operation
}

interface AppContextType {
  state: AppState;
  setState: (partial: Partial<AppState>) => void;
  resetState: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const initialState: AppState = {
  allWorkers: [],  // v2.0: Array vacío inicial (se llena en P1)
  selectedWorker: null,
  selectedOperation: null,
  selectedTipo: null,
  selectedSpool: null,
  selectedSpools: [],  // v2.0: Array vacío por defecto
  batchMode: false,  // v2.0: No batch por defecto
  batchResults: null,  // v2.0: Sin resultados por defecto
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setStateInternal] = useState<AppState>(initialState);

  // Memoizar setState para prevenir re-creación en cada renderizado
  const setState = useCallback((partial: Partial<AppState>) => {
    setStateInternal(prev => ({ ...prev, ...partial }));
  }, []);

  // Memoizar resetState para prevenir re-creación en cada renderizado
  const resetState = useCallback(() => {
    setStateInternal(initialState);
  }, []);

  return (
    <AppContext.Provider value={{ state, setState, resetState }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppState must be used within AppProvider');
  }
  return context;
}
