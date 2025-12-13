'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import { Worker, BatchActionResponse } from './types';

interface AppState {
  selectedWorker: Worker | null;
  selectedOperation: 'ARM' | 'SOLD' | null;
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

  const setState = (partial: Partial<AppState>) => {
    setStateInternal(prev => ({ ...prev, ...partial }));
  };

  const resetState = () => {
    setStateInternal(initialState);
  };

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
