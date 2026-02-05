"""
Registro centralizado de filtros por operación (v3.0 Occupation-Based).

Define qué filtros se aplican a cada combinación de:
- Operación: ARM, SOLD, METROLOGIA, REPARACION
- Acción: INICIAR, FINALIZAR

Este es el único lugar donde se configuran los filtros - facilita mantenimiento.
"""

from typing import List, Dict, Tuple
from backend.models.enums import ActionType
from .base import SpoolFilter
from .common_filters import (
    PrerequisiteFilter,
    OcupacionFilter,
    CompletionFilter,
    StatusNVFilter,
    StatusSpoolFilter,
    SOLDCompletionFilter
)


class FilterRegistry:
    """
    Registro centralizado de filtros por operación y acción.

    Cada combinación (operación, acción) tiene una lista de filtros específica.
    Para modificar filtros, solo edita este archivo.

    Ejemplo de uso:
        filters = FilterRegistry.get_filters("ARM", "INICIAR")
        for spool in all_spools:
            if FilterRegistry.passes_all_filters(spool, filters):
                eligible_spools.append(spool)
    """

    # ============================================================================
    # CONFIGURACIÓN DE FILTROS POR OPERACIÓN Y ACCIÓN
    # ============================================================================
    # IMPORTANTE: Este es el ÚNICO lugar donde se definen filtros.
    # Para modificar filtros de una operación, edita las listas a continuación.
    #
    # Estructura: Dict[(operacion, accion)] = [filtros]
    # - operacion: "ARM", "SOLD", "METROLOGIA", "REPARACION"
    # - accion: "INICIAR", "FINALIZAR"
    # ============================================================================

    # ============================================================================
    # ARM - INICIAR (v3.0 Occupation-Based)
    # ============================================================================
    # LÓGICA ACTUAL EN PRODUCCIÓN:
    # if spool.fecha_materiales is not None and spool.ocupado_por is None:
    #     spools_disponibles.append(spool)
    #
    # Incluye:
    # - Spools PENDIENTE: nunca iniciados (Armador=None, Ocupado_Por=None)
    # - Spools PAUSADO: pausados (Armador!=None, Ocupado_Por=None)
    # ============================================================================
    _ARM_INICIAR_FILTERS: List[SpoolFilter] = [
        # 1. Prerequisito: Materiales disponibles (fecha_materiales con dato)
        PrerequisiteFilter(
            field_name="fecha_materiales",
            display_name="Materiales"
        ),
        # 2. No ocupado por otro trabajador (ocupado_por vacío/null)
        OcupacionFilter(),
    ]

    # ============================================================================
    # ARM - FINALIZAR (v3.0/v4.0 Occupation-Based)
    # ============================================================================
    # LÓGICA ACTUAL EN PRODUCCIÓN (get_spools_ocupados_por_worker):
    # if spool.ocupado_por and f"({worker_id})" in spool.ocupado_por:
    #     spools_ocupados.append(spool)
    #
    # NOTA: El filtro de "ocupado por worker_id" se aplica en el método
    # get_spools_ocupados_por_worker, NO aquí. Estos son filtros adicionales.
    # ============================================================================
    _ARM_FINALIZAR_FILTERS: List[SpoolFilter] = [
        # Sin filtros adicionales - get_spools_ocupados_por_worker ya filtra por:
        # 1. Ocupado_Por contiene "(worker_id)"
        # 2. Operación = ARM
        #
        # NOTA: En v2.1 COMPLETAR había filtros adicionales (armador!=None, fecha_armado=None)
        # pero en v3.0/v4.0 FINALIZAR solo se basa en Ocupado_Por
    ]

    # ============================================================================
    # SOLD - INICIAR (v3.0 Occupation-Based)
    # ============================================================================
    # LÓGICA ACTUAL EN PRODUCCIÓN:
    # if spool.fecha_armado is not None and spool.ocupado_por is None:
    #     spools_disponibles.append(spool)
    #
    # Incluye:
    # - Spools PENDIENTE: nunca iniciados (Soldador=None, Ocupado_Por=None)
    # - Spools PAUSADO: pausados (Soldador!=None, Ocupado_Por=None)
    # ============================================================================
    _SOLD_INICIAR_FILTERS: List[SpoolFilter] = [
        # 1. Prerequisito: Armado completado (fecha_armado con dato)
        PrerequisiteFilter(
            field_name="fecha_armado",
            display_name="Armado"
        ),
        # 2. No ocupado por otro trabajador (ocupado_por vacío/null)
        OcupacionFilter(),
    ]

    # ============================================================================
    # SOLD - FINALIZAR (v3.0/v4.0 Occupation-Based)
    # ============================================================================
    # LÓGICA ACTUAL EN PRODUCCIÓN (get_spools_ocupados_por_worker):
    # if spool.ocupado_por and f"({worker_id})" in spool.ocupado_por:
    #     spools_ocupados.append(spool)
    #
    # NOTA: El filtro de "ocupado por worker_id" se aplica en el método
    # get_spools_ocupados_por_worker, NO aquí. Estos son filtros adicionales.
    # ============================================================================
    _SOLD_FINALIZAR_FILTERS: List[SpoolFilter] = [
        # Sin filtros adicionales - get_spools_ocupados_por_worker ya filtra por:
        # 1. Ocupado_Por contiene "(worker_id)"
        # 2. Operación = SOLD
        #
        # NOTA: En v2.1 COMPLETAR había filtros adicionales (soldador!=None, fecha_soldadura=None)
        # pero en v3.0/v4.0 FINALIZAR solo se basa en Ocupado_Por
    ]

    # ============================================================================
    # METROLOGIA - INICIAR (v3.0 + v4.0 Hybrid Logic)
    # ============================================================================
    # NUEVA LÓGICA (2026-02-05):
    # CONDICIÓN 1: Fecha_QC_Metrología debe estar vacía (metrología no completada)
    # CONDICIÓN 2: SOLD completada (v3.0 O v4.0):
    #   - v3.0 (Total_Uniones = 0): Fecha_Soldadura CON dato
    #   - v4.0 (Total_Uniones >= 1): Uniones_SOLD_Completadas = Total_Uniones
    #
    # DECISIÓN DEL USUARIO (2026-02-05):
    # ✅ NO filtrar por Ocupado_Por (permite ver spools ocupados por ARM/SOLD)
    # ✅ Usar lógica híbrida v3.0/v4.0 basada en Total_Uniones
    #
    # CASOS DE EJEMPLO:
    # - v3.0: TAG-001, Total_Uniones=0, Fecha_Soldadura=01-01-2026, Fecha_QC=None → ELEGIBLE
    # - v4.0 completo: TAG-002, Total_Uniones=5, Uniones_SOLD=5, Fecha_QC=None → ELEGIBLE
    # - v4.0 incompleto: TAG-003, Total_Uniones=5, Uniones_SOLD=2, Fecha_QC=None → NO ELEGIBLE
    # - v4.0 sin v3.0: TAG-004, Total_Uniones=5, Uniones_SOLD=5, Fecha_Soldadura=None → ELEGIBLE
    # ============================================================================
    _METROLOGIA_INICIAR_FILTERS: List[SpoolFilter] = [
        # 1. Metrología no completada (fecha_qc_metrologia vacía)
        CompletionFilter(
            field_name="fecha_qc_metrologia",
            display_name="Metrología"
        ),
        # 2. Soldadura completada (v3.0 + v4.0 hybrid logic)
        SOLDCompletionFilter(),
        # NOTA: NO se filtra por Ocupado_Por (decisión del usuario 2026-02-05)
        # NOTA: METROLOGIA es instantánea (sin FINALIZAR) - solo tiene INICIAR
    ]

    # ============================================================================
    # METROLOGIA - FINALIZAR: No aplica (METROLOGIA es operación instantánea)
    # ============================================================================
    _METROLOGIA_FINALIZAR_FILTERS: List[SpoolFilter] = []

    # REPARACION - INICIAR: Spools rechazados disponibles para reparar
    _REPARACION_INICIAR_FILTERS: List[SpoolFilter] = [
        # TODO: Definir filtros para REPARACION INICIAR según reglas de negocio
        # Ejemplo:
        # - Estado_Detalle contiene "RECHAZADO"
        # - No ocupado por otro trabajador
        # - Ciclo de reparación < 3
    ]

    # REPARACION - FINALIZAR: Spools en reparación ocupados por el trabajador
    _REPARACION_FINALIZAR_FILTERS: List[SpoolFilter] = [
        # TODO: Definir filtros para REPARACION FINALIZAR
    ]

    # ============================================================================
    # MAPEO: (operacion, accion) -> filtros
    # ============================================================================
    _FILTER_MAP: Dict[Tuple[str, str], List[SpoolFilter]] = {
        ("ARM", "INICIAR"): _ARM_INICIAR_FILTERS,
        ("ARM", "FINALIZAR"): _ARM_FINALIZAR_FILTERS,
        ("SOLD", "INICIAR"): _SOLD_INICIAR_FILTERS,
        ("SOLD", "FINALIZAR"): _SOLD_FINALIZAR_FILTERS,
        ("METROLOGIA", "INICIAR"): _METROLOGIA_INICIAR_FILTERS,
        ("METROLOGIA", "FINALIZAR"): _METROLOGIA_FINALIZAR_FILTERS,
        ("REPARACION", "INICIAR"): _REPARACION_INICIAR_FILTERS,
        ("REPARACION", "FINALIZAR"): _REPARACION_FINALIZAR_FILTERS,
    }

    @classmethod
    def get_filters(cls, operation: str, action: str) -> List[SpoolFilter]:
        """
        Obtiene la lista de filtros configurados para una combinación operación + acción.

        Args:
            operation: Tipo de operación ("ARM", "SOLD", "METROLOGIA", "REPARACION")
            action: Tipo de acción ("INICIAR", "FINALIZAR")

        Returns:
            Lista de filtros a aplicar (en orden)

        Raises:
            ValueError: Si la combinación (operación, acción) no está soportada

        Examples:
            >>> filters = FilterRegistry.get_filters("ARM", "INICIAR")
            >>> len(filters)
            4
            >>> filters = FilterRegistry.get_filters("METROLOGIA", "INICIAR")
            >>> len(filters)
            3
        """
        operation_upper = operation.upper()
        action_upper = action.upper()
        key = (operation_upper, action_upper)

        if key in cls._FILTER_MAP:
            return cls._FILTER_MAP[key].copy()
        else:
            raise ValueError(
                f"Combinación ('{operation}', '{action}') no soportada. "
                f"Combinaciones válidas: {list(cls._FILTER_MAP.keys())}"
            )

    @classmethod
    def get_filters_for_operation(cls, operation: str) -> List[SpoolFilter]:
        """
        DEPRECATED: Usa get_filters(operation, action) en su lugar.

        Método legacy para retrocompatibilidad. Por defecto retorna filtros de INICIAR.

        Args:
            operation: Tipo de operación

        Returns:
            Lista de filtros para INICIAR la operación
        """
        return cls.get_filters(operation, "INICIAR")

    @classmethod
    def passes_all_filters(cls, spool, filters: List[SpoolFilter]) -> bool:
        """
        Verifica si un spool pasa TODOS los filtros.

        Args:
            spool: Spool a evaluar
            filters: Lista de filtros a aplicar

        Returns:
            True si pasa todos los filtros, False si falla alguno
        """
        for filter_obj in filters:
            result = filter_obj.apply(spool)
            if not result.passed:
                return False
        return True

    @classmethod
    def get_filter_description(cls, operation: str, action: str) -> str:
        """
        Genera descripción legible de los filtros para una combinación operación + acción.

        Args:
            operation: Tipo de operación
            action: Tipo de acción ("INICIAR", "FINALIZAR")

        Returns:
            String con descripción de todos los filtros aplicados

        Example:
            >>> desc = FilterRegistry.get_filter_description("ARM", "INICIAR")
            >>> print(desc)
            ARM - INICIAR - Filtros aplicados:
            1. Prerequisite_Materiales: Verifica que Materiales esté completado
            2. Ocupacion_Disponible: Verifica que el spool NO esté ocupado
            ...
        """
        filters = cls.get_filters(operation, action)
        if not filters:
            return f"{operation.upper()} - {action.upper()}: Sin filtros configurados"

        lines = [f"{operation.upper()} - {action.upper()} - Filtros aplicados:"]
        for idx, filter_obj in enumerate(filters, start=1):
            lines.append(f"{idx}. {filter_obj.name}: {filter_obj.description}")
        return "\n".join(lines)
