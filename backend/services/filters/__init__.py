"""
Filtros de spools por operación (v3.0 Occupation-Based).

Este módulo implementa un sistema unificado de filtros para todas las operaciones
(ARM, SOLD, METROLOGIA, REPARACION).

Arquitectura:
- SpoolFilter: Clase base abstracta para definir filtros
- FilterRegistry: Registro centralizado de filtros por operación
- Filtros configurables y extensibles para cada operación

Ejemplo de uso:
    from backend.services.filters import FilterRegistry

    filters = FilterRegistry.get_filters_for_operation("ARM")
    eligible_spools = [spool for spool in all_spools if all(f.apply(spool) for f in filters)]
"""

from .base import SpoolFilter, FilterResult
from .registry import FilterRegistry
from .common_filters import (
    PrerequisiteFilter,
    OcupacionFilter,
    CompletionFilter,
    StatusNVFilter,
    StatusSpoolFilter,
    SOLDCompletionFilter
)

__all__ = [
    'SpoolFilter',
    'FilterResult',
    'FilterRegistry',
    'PrerequisiteFilter',
    'OcupacionFilter',
    'CompletionFilter',
    'StatusNVFilter',
    'StatusSpoolFilter',
    'SOLDCompletionFilter'
]
