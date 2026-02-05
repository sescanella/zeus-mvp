"""
Clase base para filtros de spools (v3.0 Occupation-Based).

Define la interfaz abstracta para todos los filtros de elegibilidad de spools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from backend.models.spool import Spool


@dataclass
class FilterResult:
    """
    Resultado de aplicar un filtro a un spool.

    Attributes:
        passed: True si el spool pasa el filtro, False si no
        reason: Razón detallada del resultado (para logging/debugging)
    """
    passed: bool
    reason: str


class SpoolFilter(ABC):
    """
    Clase base abstracta para filtros de spools.

    Cada filtro implementa una regla de negocio específica para determinar
    si un spool es elegible para una operación.

    Ejemplo:
        class MaterialesFilter(SpoolFilter):
            def apply(self, spool: Spool) -> FilterResult:
                if spool.fecha_materiales is not None:
                    return FilterResult(True, "Materiales disponibles")
                return FilterResult(False, "Materiales no disponibles")
    """

    @abstractmethod
    def apply(self, spool: Spool) -> FilterResult:
        """
        Aplica el filtro a un spool.

        Args:
            spool: Spool a evaluar

        Returns:
            FilterResult indicando si el spool pasa el filtro y la razón
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre descriptivo del filtro (para logging)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción detallada de la regla de negocio del filtro."""
        pass
