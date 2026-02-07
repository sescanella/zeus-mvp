"""
MetadataEventBuilder - Fluent API for constructing audit trail events.

Eliminates code duplication across services (occupation, metrologia, reparacion).
Provides type-safe, validated event construction with sensible defaults.

Usage:
    from backend.services.metadata_event_builder import MetadataEventBuilder

    # TOMAR event
    event = (
        MetadataEventBuilder()
        .for_tomar(tag_spool="TEST-01", worker_id=93, worker_nombre="MR(93)")
        .with_operacion("ARM")
        .with_metadata({"ocupado_por": "MR(93)", "fecha_ocupacion": "04-02-2026 10:00:00"})
        .build()
    )

    # Log event
    metadata_repository.log_event(**event)

Author: Claude Code (code-reviewer agent)
Created: 2026-02-06
Refactoring: Metadata Event Builder (Refactoring 2/4)
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Any

from backend.utils.date_formatter import (
    format_datetime_for_sheets,
    format_date_for_sheets,
    now_chile,
    today_chile
)


class MetadataEventBuilder:
    """
    Builder for MetadataEvent objects with fluent API.

    Ensures consistency across all metadata event creation:
    - Auto-generates UUID and timestamp
    - Validates required fields
    - Formats dates correctly for Chile timezone
    - Serializes metadata_json consistently

    All event types supported:
    - TOMAR_SPOOL (occupation start)
    - PAUSAR_SPOOL (pause work)
    - COMPLETAR_SPOOL (complete work)
    - INICIAR_SPOOL (v4.0 start)
    - FINALIZAR_SPOOL (v4.0 finish - auto-determined)
    - CANCELAR_SPOOL (v4.0 cancel)
    - METROLOGIA_APROBADO/RECHAZADO
    - REPARACION_INICIO/FIN
    """

    def __init__(self):
        """Initialize builder with defaults."""
        self._event_id = str(uuid.uuid4())
        self._timestamp = format_datetime_for_sheets(now_chile())
        self._fecha_operacion = format_date_for_sheets(today_chile())
        self._evento_tipo: Optional[str] = None
        self._tag_spool: Optional[str] = None
        self._worker_id: Optional[int] = None
        self._worker_nombre: Optional[str] = None
        self._operacion: Optional[str] = None
        self._accion: Optional[str] = None
        self._metadata: Dict[str, Any] = {}

    def for_tomar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> "MetadataEventBuilder":
        """
        Configure for TOMAR_SPOOL event.

        Sets:
        - evento_tipo = "TOMAR_SPOOL"
        - accion = "TOMAR"
        - tag_spool, worker_id, worker_nombre

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID (e.g., 93)
            worker_nombre: Worker name format "MR(93)"

        Returns:
            Self for method chaining
        """
        self._evento_tipo = "TOMAR_SPOOL"
        self._accion = "TOMAR"
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def for_pausar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> "MetadataEventBuilder":
        """
        Configure for PAUSAR_SPOOL event.

        Sets:
        - evento_tipo = "PAUSAR_SPOOL"
        - accion = "PAUSAR"
        - tag_spool, worker_id, worker_nombre

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"

        Returns:
            Self for method chaining
        """
        self._evento_tipo = "PAUSAR_SPOOL"
        self._accion = "PAUSAR"
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def for_completar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        fecha_operacion: str
    ) -> "MetadataEventBuilder":
        """
        Configure for COMPLETAR_SPOOL event.

        Sets:
        - evento_tipo = "COMPLETAR_SPOOL"
        - accion = "COMPLETAR"
        - tag_spool, worker_id, worker_nombre
        - Accepts custom fecha_operacion (user-provided date)

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"
            fecha_operacion: Operation date (format: "DD-MM-YYYY")

        Returns:
            Self for method chaining
        """
        self._evento_tipo = "COMPLETAR_SPOOL"
        self._accion = "COMPLETAR"
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        self._fecha_operacion = fecha_operacion
        return self

    def for_iniciar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> "MetadataEventBuilder":
        """
        Configure for INICIAR_SPOOL event (v4.0).

        Sets:
        - evento_tipo = "INICIAR_SPOOL"
        - accion = "INICIAR"
        - tag_spool, worker_id, worker_nombre

        Args:
            tag_spool: Spool identifier (v4.0 format, e.g., "OT-123")
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"

        Returns:
            Self for method chaining
        """
        self._evento_tipo = "INICIAR_SPOOL"
        self._accion = "INICIAR"
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def for_finalizar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        action_taken: str  # PAUSAR, COMPLETAR, or CANCELAR
    ) -> "MetadataEventBuilder":
        """
        Configure for FINALIZAR_SPOOL event (v4.0).

        Auto-determines evento_tipo based on action_taken:
        - PAUSAR → "PAUSAR_SPOOL"
        - COMPLETAR → "COMPLETAR_SPOOL"
        - CANCELAR → "CANCELAR_SPOOL"

        Args:
            tag_spool: Spool identifier (v4.0 format)
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"
            action_taken: Auto-determined action ("PAUSAR", "COMPLETAR", "CANCELAR")

        Returns:
            Self for method chaining

        Raises:
            ValueError: If action_taken not in valid actions
        """
        evento_tipo_map = {
            "PAUSAR": "PAUSAR_SPOOL",
            "COMPLETAR": "COMPLETAR_SPOOL",
            "CANCELAR": "CANCELAR_SPOOL"
        }

        if action_taken not in evento_tipo_map:
            raise ValueError(
                f"Invalid action_taken: {action_taken}. "
                f"Must be one of: {list(evento_tipo_map.keys())}"
            )

        self._evento_tipo = evento_tipo_map[action_taken]
        self._accion = action_taken
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def for_cancelar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> "MetadataEventBuilder":
        """
        Configure for CANCELAR_SPOOL event (v4.0).

        Sets:
        - evento_tipo = "CANCELAR_SPOOL"
        - accion = "CANCELAR"
        - tag_spool, worker_id, worker_nombre

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"

        Returns:
            Self for method chaining
        """
        self._evento_tipo = "CANCELAR_SPOOL"
        self._accion = "CANCELAR"
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def for_metrologia(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        resultado: str  # APROBADO or RECHAZADO
    ) -> "MetadataEventBuilder":
        """
        Configure for METROLOGIA event.

        Sets:
        - evento_tipo = "COMPLETAR_METROLOGIA"
        - accion = "COMPLETAR"
        - tag_spool, worker_id, worker_nombre
        - resultado stored in metadata (not in accion)

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"
            resultado: Inspection result ("APROBADO" or "RECHAZADO")

        Returns:
            Self for method chaining

        Raises:
            ValueError: If resultado not in valid values
        """
        valid_resultados = ["APROBADO", "RECHAZADO"]
        if resultado not in valid_resultados:
            raise ValueError(
                f"Invalid resultado: {resultado}. "
                f"Must be one of: {valid_resultados}"
            )

        self._evento_tipo = "COMPLETAR_METROLOGIA"
        self._accion = "COMPLETAR"
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def for_reparacion(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        accion: str  # INICIO or FIN
    ) -> "MetadataEventBuilder":
        """
        Configure for REPARACION event.

        Sets:
        - evento_tipo = "REPARACION_INICIO" or "REPARACION_FIN"
        - accion = accion
        - tag_spool, worker_id, worker_nombre

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name format "MR(93)"
            accion: Repair action ("INICIO" or "FIN")

        Returns:
            Self for method chaining

        Raises:
            ValueError: If accion not in valid values
        """
        valid_acciones = ["INICIO", "FIN"]
        if accion not in valid_acciones:
            raise ValueError(
                f"Invalid accion: {accion}. "
                f"Must be one of: {valid_acciones}"
            )

        self._evento_tipo = f"REPARACION_{accion}"
        self._accion = accion
        self._tag_spool = tag_spool
        self._worker_id = worker_id
        self._worker_nombre = worker_nombre
        return self

    def with_operacion(self, operacion: str) -> "MetadataEventBuilder":
        """
        Set operacion field.

        Args:
            operacion: Operation type ("ARM", "SOLD", "METROLOGIA", "REPARACION")

        Returns:
            Self for method chaining
        """
        self._operacion = operacion
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "MetadataEventBuilder":
        """
        Add metadata JSON fields.

        Merges with existing metadata (last write wins).

        Args:
            metadata: Dictionary of metadata fields to log

        Returns:
            Self for method chaining
        """
        self._metadata.update(metadata)
        return self

    def with_custom_fecha(self, fecha_operacion: str) -> "MetadataEventBuilder":
        """
        Override default fecha_operacion.

        Args:
            fecha_operacion: Custom operation date (format: "DD-MM-YYYY")

        Returns:
            Self for method chaining
        """
        self._fecha_operacion = fecha_operacion
        return self

    def build(self) -> Dict[str, Any]:
        """
        Build metadata event dict ready for log_event().

        Validates required fields and returns event dict compatible
        with MetadataRepository.log_event(**event).

        Returns:
            Dict with keys: id, timestamp, evento_tipo, tag_spool,
                           worker_id, worker_nombre, operacion, accion,
                           fecha_operacion, metadata_json

        Raises:
            ValueError: If required fields are missing
        """
        # Validation
        if not self._evento_tipo:
            raise ValueError(
                "evento_tipo is required. "
                "Use for_tomar(), for_pausar(), for_completar(), etc."
            )
        if not self._tag_spool:
            raise ValueError("tag_spool is required")
        if not self._operacion:
            raise ValueError(
                "operacion is required. "
                "Use with_operacion('ARM'|'SOLD'|'METROLOGIA'|'REPARACION')"
            )

        # Serialize metadata_json
        metadata_json = json.dumps(self._metadata, ensure_ascii=False)

        return {
            "id": self._event_id,
            "timestamp": self._timestamp,
            "evento_tipo": self._evento_tipo,
            "tag_spool": self._tag_spool,
            "worker_id": self._worker_id,
            "worker_nombre": self._worker_nombre,
            "operacion": self._operacion,
            "accion": self._accion,
            "fecha_operacion": self._fecha_operacion,
            "metadata_json": metadata_json
        }


# Convenience function for quick event creation
def build_metadata_event(
    evento_tipo: str,
    tag_spool: str,
    worker_id: int,
    worker_nombre: str,
    operacion: str,
    accion: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Quick helper to build metadata event without fluent API.

    Useful for simple events where builder fluency is overkill.

    Args:
        evento_tipo: Event type (e.g., "TOMAR_SPOOL")
        tag_spool: Spool identifier
        worker_id: Worker ID
        worker_nombre: Worker name format "MR(93)"
        operacion: Operation type ("ARM", "SOLD", etc.)
        accion: Action performed
        metadata: Optional metadata dictionary

    Returns:
        Event dict ready for log_event()

    Example:
        event = build_metadata_event(
            evento_tipo="TOMAR_SPOOL",
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion="TOMAR",
            metadata={"ocupado_por": "MR(93)"}
        )
    """
    builder = MetadataEventBuilder()
    builder._evento_tipo = evento_tipo
    builder._tag_spool = tag_spool
    builder._worker_id = worker_id
    builder._worker_nombre = worker_nombre
    builder._operacion = operacion
    builder._accion = accion
    if metadata:
        builder._metadata = metadata

    return builder.build()
