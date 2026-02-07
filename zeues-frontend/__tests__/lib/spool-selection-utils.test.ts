import {
  MAX_BATCH_SELECTION,
  getOperationLabel,
  getActionLabel,
  getPageTitle,
  getEmptyMessage,
} from '@/lib/spool-selection-utils';

describe('MAX_BATCH_SELECTION', () => {
  it('equals 50', () => {
    expect(MAX_BATCH_SELECTION).toBe(50);
  });
});

describe('getOperationLabel', () => {
  it('returns ARMADO for ARM', () => {
    expect(getOperationLabel('ARM')).toBe('ARMADO');
  });

  it('returns SOLDADURA for SOLD', () => {
    expect(getOperationLabel('SOLD')).toBe('SOLDADURA');
  });

  it('returns METROLOGÍA for METROLOGIA', () => {
    expect(getOperationLabel('METROLOGIA')).toBe('METROLOGÍA');
  });

  it('returns REPARACIÓN for REPARACION', () => {
    expect(getOperationLabel('REPARACION')).toBe('REPARACIÓN');
  });
});

describe('getActionLabel', () => {
  it('returns TOMAR for tomar', () => {
    expect(getActionLabel('tomar')).toBe('TOMAR');
  });

  it('returns PAUSAR for pausar', () => {
    expect(getActionLabel('pausar')).toBe('PAUSAR');
  });

  it('returns COMPLETAR for completar', () => {
    expect(getActionLabel('completar')).toBe('COMPLETAR');
  });

  it('returns CANCELAR for cancelar', () => {
    expect(getActionLabel('cancelar')).toBe('CANCELAR');
  });

  it('returns INSPECCIONAR for metrologia', () => {
    expect(getActionLabel('metrologia')).toBe('INSPECCIONAR');
  });

  it('returns REPARAR for reparacion', () => {
    expect(getActionLabel('reparacion')).toBe('REPARAR');
  });

  it('returns SELECCIONAR for null', () => {
    expect(getActionLabel(null)).toBe('SELECCIONAR');
  });
});

describe('getPageTitle', () => {
  const baseParams = {
    accion: null as 'INICIAR' | 'FINALIZAR' | null,
    tipo: null as 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion' | null,
    operationLabel: 'ARMADO',
    selectedOperation: 'ARM' as const,
  };

  it('returns INICIAR title for accion=INICIAR', () => {
    expect(getPageTitle({ ...baseParams, accion: 'INICIAR' })).toBe(
      'SELECCIONAR SPOOL PARA INICIAR - ARMADO'
    );
  });

  it('returns FINALIZAR title for accion=FINALIZAR', () => {
    expect(getPageTitle({ ...baseParams, accion: 'FINALIZAR' })).toBe(
      'SELECCIONAR SPOOL PARA FINALIZAR - ARMADO'
    );
  });

  it('returns tomar title for tipo=tomar', () => {
    expect(getPageTitle({ ...baseParams, tipo: 'tomar' })).toBe(
      'SELECCIONAR SPOOL PARA TOMAR - ARMADO'
    );
  });

  it('returns pausar title for tipo=pausar', () => {
    expect(getPageTitle({ ...baseParams, tipo: 'pausar' })).toBe(
      'SELECCIONAR SPOOL PARA PAUSAR - ARMADO'
    );
  });

  it('returns completar title for tipo=completar', () => {
    expect(getPageTitle({ ...baseParams, tipo: 'completar' })).toBe(
      'SELECCIONAR SPOOL PARA COMPLETAR - ARMADO'
    );
  });

  it('returns cancelar title for ARM tipo=cancelar', () => {
    expect(getPageTitle({ ...baseParams, tipo: 'cancelar' })).toBe(
      'SELECCIONAR SPOOL PARA CANCELAR - ARMADO'
    );
  });

  it('returns REPARACION-specific cancelar title', () => {
    expect(getPageTitle({
      ...baseParams,
      tipo: 'cancelar',
      selectedOperation: 'REPARACION',
      operationLabel: 'REPARACION',
    })).toBe('SELECCIONAR REPARACION PARA CANCELAR');
  });

  it('returns metrologia title for tipo=metrologia', () => {
    expect(getPageTitle({ ...baseParams, tipo: 'metrologia' })).toBe(
      'SELECCIONAR SPOOL PARA INSPECCION'
    );
  });

  it('returns reparacion title for tipo=reparacion', () => {
    expect(getPageTitle({ ...baseParams, tipo: 'reparacion' })).toBe(
      'SELECCIONAR SPOOL PARA REPARAR'
    );
  });

  it('returns fallback title for null tipo', () => {
    expect(getPageTitle({ ...baseParams, tipo: null })).toBe(
      'ARMADO - SELECCIONAR'
    );
  });

  it('prioritizes accion over tipo', () => {
    expect(getPageTitle({ ...baseParams, accion: 'INICIAR', tipo: 'tomar' })).toBe(
      'SELECCIONAR SPOOL PARA INICIAR - ARMADO'
    );
  });
});

describe('getEmptyMessage', () => {
  const baseParams = {
    accion: null as 'INICIAR' | 'FINALIZAR' | null,
    tipo: null as 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion' | null,
    operationLabel: 'ARMADO',
    selectedOperation: 'ARM' as const,
  };

  it('returns INICIAR empty message', () => {
    expect(getEmptyMessage({ ...baseParams, accion: 'INICIAR' })).toBe(
      'No hay spools disponibles para iniciar en ARMADO'
    );
  });

  it('returns FINALIZAR empty message', () => {
    expect(getEmptyMessage({ ...baseParams, accion: 'FINALIZAR' })).toBe(
      'No tienes spools ocupados actualmente para ARMADO'
    );
  });

  it('returns tomar empty message', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: 'tomar' })).toBe(
      'No hay spools disponibles para ARMADO'
    );
  });

  it('returns pausar empty message', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: 'pausar' })).toBe(
      'No tienes spools en progreso para pausar'
    );
  });

  it('returns completar empty message', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: 'completar' })).toBe(
      'No tienes spools en progreso para completar'
    );
  });

  it('returns cancelar empty message for ARM', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: 'cancelar' })).toBe(
      'No tienes spools en progreso para cancelar'
    );
  });

  it('returns cancelar empty message for REPARACION', () => {
    expect(getEmptyMessage({
      ...baseParams,
      tipo: 'cancelar',
      selectedOperation: 'REPARACION',
      operationLabel: 'REPARACION',
    })).toBe('No tienes reparaciones en progreso para cancelar');
  });

  it('returns metrologia empty message', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: 'metrologia' })).toBe(
      'No hay spools disponibles para inspeccion de metrologia'
    );
  });

  it('returns reparacion empty message', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: 'reparacion' })).toBe(
      'No hay spools rechazados disponibles para reparacion'
    );
  });

  it('returns default empty message for null tipo', () => {
    expect(getEmptyMessage({ ...baseParams, tipo: null })).toBe(
      'No hay spools disponibles'
    );
  });

  it('prioritizes accion over tipo', () => {
    expect(getEmptyMessage({ ...baseParams, accion: 'FINALIZAR', tipo: 'tomar' })).toBe(
      'No tienes spools ocupados actualmente para ARMADO'
    );
  });
});
