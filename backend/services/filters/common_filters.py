"""
Filtros comunes reutilizables para todas las operaciones (v3.0 Occupation-Based).

Implementa filtros genéricos que se configuran con parámetros específicos por operación.
"""

from typing import Optional
from backend.models.spool import Spool
from .base import SpoolFilter, FilterResult


class PrerequisiteFilter(SpoolFilter):
    """
    Filtra spools basándose en que un prerequisito (fecha) esté completado.

    Ejemplo: Para SOLD, prerequisito es Fecha_Armado (ARM debe estar completado).
    """

    def __init__(self, field_name: str, display_name: str):
        """
        Args:
            field_name: Nombre del atributo del spool a verificar (ej: "fecha_armado")
            display_name: Nombre legible para logs (ej: "Armado")
        """
        self._field_name = field_name
        self._display_name = display_name

    def apply(self, spool: Spool) -> FilterResult:
        value = getattr(spool, self._field_name, None)
        if value is not None:
            return FilterResult(
                passed=True,
                reason=f"{self._display_name} completado ({self._field_name}={value})"
            )
        return FilterResult(
            passed=False,
            reason=f"{self._display_name} no completado ({self._field_name} vacío)"
        )

    @property
    def name(self) -> str:
        return f"Prerequisite_{self._display_name}"

    @property
    def description(self) -> str:
        return f"Verifica que {self._display_name} esté completado (campo {self._field_name} con dato)"


class OcupacionFilter(SpoolFilter):
    """
    Filtra spools que NO estén ocupados por otro trabajador (v3.0 Occupation-Based).

    Este filtro es crítico para evitar conflictos de concurrencia.
    """

    def apply(self, spool: Spool) -> FilterResult:
        if spool.ocupado_por is None or spool.ocupado_por == "" or spool.ocupado_por == "DISPONIBLE":
            return FilterResult(
                passed=True,
                reason=f"Spool disponible (ocupado_por={spool.ocupado_por or 'null'})"
            )
        return FilterResult(
            passed=False,
            reason=f"Spool ocupado por {spool.ocupado_por}"
        )

    @property
    def name(self) -> str:
        return "Ocupacion_Disponible"

    @property
    def description(self) -> str:
        return "Verifica que el spool NO esté ocupado (Ocupado_Por vacío o 'DISPONIBLE')"


class CompletionFilter(SpoolFilter):
    """
    Filtra spools que NO hayan sido completados para la operación actual.

    Ejemplo: Para METROLOGIA, verifica que Fecha_QC_Metrología esté vacía.
    """

    def __init__(self, field_name: str, display_name: str):
        """
        Args:
            field_name: Nombre del atributo del spool a verificar (ej: "fecha_qc_metrologia")
            display_name: Nombre legible para logs (ej: "Metrología")
        """
        self._field_name = field_name
        self._display_name = display_name

    def apply(self, spool: Spool) -> FilterResult:
        value = getattr(spool, self._field_name, None)
        if value is None or value == "":
            return FilterResult(
                passed=True,
                reason=f"{self._display_name} no completado ({self._field_name} vacío)"
            )
        return FilterResult(
            passed=False,
            reason=f"{self._display_name} ya completado ({self._field_name}={value})"
        )

    @property
    def name(self) -> str:
        return f"Completion_{self._display_name}"

    @property
    def description(self) -> str:
        return f"Verifica que {self._display_name} NO esté completado (campo {self._field_name} vacío)"


class StatusNVFilter(SpoolFilter):
    """
    Filtra spools basándose en el estado de la Nota de Venta (STATUS_NV).

    Valores comunes: 'ABIERTA', 'CERRADA'
    """

    def __init__(self, required_status: str):
        """
        Args:
            required_status: Estado requerido (ej: "ABIERTA")
        """
        self._required_status = required_status.upper()

    def apply(self, spool: Spool) -> FilterResult:
        # Normalizar valor a mayúsculas
        actual_status = (spool.status_nv or "").upper()

        if actual_status == self._required_status:
            return FilterResult(
                passed=True,
                reason=f"NV en estado correcto (STATUS_NV={actual_status})"
            )
        return FilterResult(
            passed=False,
            reason=f"NV en estado incorrecto (STATUS_NV={actual_status}, esperado={self._required_status})"
        )

    @property
    def name(self) -> str:
        return f"StatusNV_{self._required_status}"

    @property
    def description(self) -> str:
        return f"Verifica que STATUS_NV sea '{self._required_status}'"


class StatusSpoolFilter(SpoolFilter):
    """
    Filtra spools basándose en el estado del spool (Status_Spool).

    Valores comunes: 'EN_PROCESO', 'BLOQUEADO', 'COMPLETADO'
    """

    def __init__(self, required_status: str):
        """
        Args:
            required_status: Estado requerido (ej: "EN_PROCESO")
        """
        self._required_status = required_status.upper()

    def apply(self, spool: Spool) -> FilterResult:
        # Normalizar valor a mayúsculas
        actual_status = (spool.status_spool or "").upper()

        if actual_status == self._required_status:
            return FilterResult(
                passed=True,
                reason=f"Spool en estado correcto (Status_Spool={actual_status})"
            )
        return FilterResult(
            passed=False,
            reason=f"Spool en estado incorrecto (Status_Spool={actual_status}, esperado={self._required_status})"
        )

    @property
    def name(self) -> str:
        return f"StatusSpool_{self._required_status}"

    @property
    def description(self) -> str:
        return f"Verifica que Status_Spool sea '{self._required_status}'"


class SOLDCompletionFilter(SpoolFilter):
    """
    Filtra spools con SOLDADURA completada (v3.0 + v4.0 hybrid).

    REGLA DE NEGOCIO:
    - v3.0 (Total_Uniones == 0 o None): Verifica Fecha_Soldadura con dato
    - v4.0 (Total_Uniones >= 1): Verifica Uniones_SOLD_Completadas == Total_Uniones

    Este filtro es específico para METROLOGIA, que necesita validar que la
    soldadura esté completada antes de permitir inspección.
    """

    def apply(self, spool: Spool) -> FilterResult:
        # Condición 1: Fecha_QC_Metrología debe estar vacía (prerequisito)
        # (Esta condición se verifica en CompletionFilter separado)

        # Condición 2: SOLD completada (v3.0 OR v4.0)
        # Detectar versión del spool
        total_uniones = spool.total_uniones or 0

        if total_uniones == 0:
            # Spool v3.0 (legacy) - Usar Fecha_Soldadura
            if spool.fecha_soldadura is not None:
                return FilterResult(
                    passed=True,
                    reason=f"v3.0: Soldadura completada (Fecha_Soldadura={spool.fecha_soldadura})"
                )
            return FilterResult(
                passed=False,
                reason="v3.0: Soldadura no completada (Fecha_Soldadura vacía)"
            )
        else:
            # Spool v4.0 (con uniones) - Usar contadores
            uniones_sold = spool.uniones_sold_completadas or 0

            if uniones_sold == total_uniones:
                return FilterResult(
                    passed=True,
                    reason=f"v4.0: Todas las uniones soldadas ({uniones_sold}/{total_uniones})"
                )
            return FilterResult(
                passed=False,
                reason=f"v4.0: Soldadura incompleta ({uniones_sold}/{total_uniones} uniones)"
            )

    @property
    def name(self) -> str:
        return "SOLDCompletion_v3_v4_Hybrid"

    @property
    def description(self) -> str:
        return (
            "Verifica que SOLDADURA esté completada. "
            "v3.0 (Total_Uniones=0): Fecha_Soldadura con dato. "
            "v4.0 (Total_Uniones>=1): Uniones_SOLD_Completadas = Total_Uniones"
        )
