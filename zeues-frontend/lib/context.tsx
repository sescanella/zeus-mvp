'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Worker, BatchActionResponse, Union } from './types';

interface AppState {
  allWorkers: Worker[];  // v2.0: Cache de todos los trabajadores (fetch en P1, filtrar en P2)
  selectedWorker: Worker | null;
  selectedOperation: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION' | null;  // v3.0: +REPARACION
  selectedTipo: 'tomar' | 'pausar' | 'completar' | 'cancelar' | null;  // v3.0: TOMAR/PAUSAR/COMPLETAR workflow
  selectedSpool: string | null;  // Single-select (backward compat)
  selectedSpools: string[];  // v2.0: Multiselect batch (array de TAGs)
  batchMode: boolean;  // v2.0: Flag si operación es batch
  batchResults: BatchActionResponse | null;  // v2.0: Resultados de batch operation
  // v4.0: Union-level workflow fields
  accion: 'INICIAR' | 'FINALIZAR' | null;  // v4.0: Workflow action (replaces selectedTipo for v4.0 spools)
  selectedUnions: number[];  // v4.0: Selected union numbers (N_UNION values)
  pulgadasCompletadas: number;  // v4.0: Calculated pulgadas-diámetro for selected unions
}

interface AppContextType {
  state: AppState;
  setState: (partial: Partial<AppState>) => void;
  resetState: () => void;
  // v4.0: Helper functions for union-level workflow
  resetV4State: () => void;
  calculatePulgadas: (unions: Union[], selectedUnionNumbers: number[]) => number;
  toggleUnionSelection: (unionNumber: number, isSelected: boolean) => void;
  selectAllAvailableUnions: (availableUnionNumbers: number[]) => void;
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
  // v4.0: Initialize union-level workflow state
  accion: null,
  selectedUnions: [],
  pulgadasCompletadas: 0,
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

  // v4.0: Reset only v4.0-specific state (preserves worker, operation, spool selection)
  const resetV4State = useCallback(() => {
    setStateInternal(prev => ({
      ...prev,
      accion: null,
      selectedUnions: [],
      pulgadasCompletadas: 0,
    }));
  }, []);

  // v4.0: Calculate total pulgadas-diámetro for selected unions
  const calculatePulgadas = useCallback((unions: Union[], selectedUnionNumbers: number[]): number => {
    if (selectedUnionNumbers.length === 0) return 0;

    const total = unions
      .filter(u => selectedUnionNumbers.includes(u.n_union))
      .reduce((sum, u) => sum + u.dn_union, 0);

    return Math.round(total * 10) / 10; // 1 decimal precision (service layer presentation)
  }, []);

  // v4.0: Toggle single union selection
  const toggleUnionSelection = useCallback((unionNumber: number, isSelected: boolean) => {
    setStateInternal(prev => {
      const newSelected = isSelected
        ? [...prev.selectedUnions, unionNumber]
        : prev.selectedUnions.filter(n => n !== unionNumber);

      return {
        ...prev,
        selectedUnions: newSelected,
      };
    });
  }, []);

  // v4.0: Select all available unions at once
  const selectAllAvailableUnions = useCallback((availableUnionNumbers: number[]) => {
    setStateInternal(prev => ({
      ...prev,
      selectedUnions: [...availableUnionNumbers],
    }));
  }, []);

  return (
    <AppContext.Provider value={{
      state,
      setState,
      resetState,
      resetV4State,
      calculatePulgadas,
      toggleUnionSelection,
      selectAllAvailableUnions,
    }}>
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
