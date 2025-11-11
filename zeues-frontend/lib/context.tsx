'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface AppState {
  selectedWorker: string | null;
  selectedOperation: 'ARM' | 'SOLD' | null;
  selectedTipo: 'iniciar' | 'completar' | null;
  selectedSpool: string | null;
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
