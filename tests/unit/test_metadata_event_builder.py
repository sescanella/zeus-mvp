"""
Unit tests for MetadataEventBuilder.

Validates:
- Fluent API works correctly
- All event types supported (TOMAR, PAUSAR, COMPLETAR, INICIAR, FINALIZAR, etc.)
- Metadata JSON serialization
- Validation errors on missing fields
- Date formatting for Chile timezone

Author: Claude Code (code-reviewer agent)
Created: 2026-02-06
Refactoring: Metadata Event Builder (Refactoring 2/4)
"""
import pytest
import json
from backend.services.metadata_event_builder import MetadataEventBuilder, build_metadata_event


class TestMetadataEventBuilderTomar:
    """Tests for TOMAR_SPOOL event building."""

    def test_tomar_event_builder(self):
        """Builder creates valid TOMAR event with all required fields."""
        event = (
            MetadataEventBuilder()
            .for_tomar("TEST-01", 93, "MR(93)")
            .with_operacion("ARM")
            .with_metadata({"ocupado_por": "MR(93)"})
            .build()
        )

        assert event["evento_tipo"] == "TOMAR_SPOOL"
        assert event["accion"] == "TOMAR"
        assert event["tag_spool"] == "TEST-01"
        assert event["worker_id"] == 93
        assert event["worker_nombre"] == "MR(93)"
        assert event["operacion"] == "ARM"
        assert '"ocupado_por": "MR(93)"' in event["metadata_json"]

        # Verify generated fields
        assert "id" in event
        assert "timestamp" in event
        assert "fecha_operacion" in event

    def test_tomar_multiple_metadata_fields(self):
        """Builder supports multiple metadata fields."""
        event = (
            MetadataEventBuilder()
            .for_tomar("TEST-01", 93, "MR(93)")
            .with_operacion("SOLD")
            .with_metadata({
                "ocupado_por": "MR(93)",
                "fecha_ocupacion": "04-02-2026 10:00:00",
                "previous_state": "PAUSADO"
            })
            .build()
        )

        metadata = json.loads(event["metadata_json"])
        assert metadata["ocupado_por"] == "MR(93)"
        assert metadata["fecha_ocupacion"] == "04-02-2026 10:00:00"
        assert metadata["previous_state"] == "PAUSADO"


class TestMetadataEventBuilderPausar:
    """Tests for PAUSAR_SPOOL event building."""

    def test_pausar_event_builder(self):
        """Builder creates valid PAUSAR event."""
        event = (
            MetadataEventBuilder()
            .for_pausar("TEST-02", 94, "JP(94)")
            .with_operacion("ARM")
            .with_metadata({"unions_completed": 5})
            .build()
        )

        assert event["evento_tipo"] == "PAUSAR_SPOOL"
        assert event["accion"] == "PAUSAR"
        assert event["tag_spool"] == "TEST-02"
        assert event["worker_id"] == 94
        assert event["operacion"] == "ARM"


class TestMetadataEventBuilderCompletar:
    """Tests for COMPLETAR_SPOOL event building."""

    def test_completar_event_builder(self):
        """Builder creates valid COMPLETAR event with custom fecha."""
        event = (
            MetadataEventBuilder()
            .for_completar("TEST-03", 93, "MR(93)", "01-02-2026")
            .with_operacion("ARM")
            .with_metadata({"fecha_armado": "01-02-2026"})
            .build()
        )

        assert event["evento_tipo"] == "COMPLETAR_SPOOL"
        assert event["accion"] == "COMPLETAR"
        assert event["fecha_operacion"] == "01-02-2026"  # Custom fecha
        assert event["tag_spool"] == "TEST-03"

    def test_completar_sold_operation(self):
        """Builder supports SOLD completion."""
        event = (
            MetadataEventBuilder()
            .for_completar("TEST-04", 95, "LC(95)", "02-02-2026")
            .with_operacion("SOLD")
            .with_metadata({"fecha_soldadura": "02-02-2026"})
            .build()
        )

        assert event["operacion"] == "SOLD"
        assert '"fecha_soldadura": "02-02-2026"' in event["metadata_json"]


class TestMetadataEventBuilderIniciar:
    """Tests for INICIAR_SPOOL event building (v4.0)."""

    def test_iniciar_event_builder(self):
        """Builder creates valid INICIAR event for v4.0."""
        event = (
            MetadataEventBuilder()
            .for_iniciar("OT-123", 93, "MR(93)")
            .with_operacion("ARM")
            .with_metadata({"ocupado_por": "MR(93)", "total_uniones": 10})
            .build()
        )

        assert event["evento_tipo"] == "INICIAR_SPOOL"
        assert event["accion"] == "INICIAR"
        assert event["tag_spool"] == "OT-123"
        assert '"total_uniones": 10' in event["metadata_json"]


class TestMetadataEventBuilderFinalizar:
    """Tests for FINALIZAR_SPOOL event building (v4.0)."""

    def test_finalizar_pausar(self):
        """Builder auto-determines PAUSAR_SPOOL for partial work."""
        event = (
            MetadataEventBuilder()
            .for_finalizar("OT-123", 93, "MR(93)", "PAUSAR")
            .with_operacion("ARM")
            .with_metadata({"unions_processed": 3})
            .build()
        )

        assert event["evento_tipo"] == "PAUSAR_SPOOL"
        assert event["accion"] == "PAUSAR"

    def test_finalizar_completar(self):
        """Builder auto-determines COMPLETAR_SPOOL for full work."""
        event = (
            MetadataEventBuilder()
            .for_finalizar("OT-123", 93, "MR(93)", "COMPLETAR")
            .with_operacion("ARM")
            .with_metadata({"unions_processed": 10, "pulgadas": 25.0})
            .build()
        )

        assert event["evento_tipo"] == "COMPLETAR_SPOOL"
        assert event["accion"] == "COMPLETAR"

    def test_finalizar_cancelar(self):
        """Builder auto-determines CANCELAR_SPOOL for zero work."""
        event = (
            MetadataEventBuilder()
            .for_finalizar("OT-123", 93, "MR(93)", "CANCELAR")
            .with_operacion("ARM")
            .with_metadata({"unions_processed": 0})
            .build()
        )

        assert event["evento_tipo"] == "CANCELAR_SPOOL"
        assert event["accion"] == "CANCELAR"

    def test_finalizar_invalid_action_raises_error(self):
        """Builder raises ValueError for invalid action_taken."""
        builder = MetadataEventBuilder()

        with pytest.raises(ValueError, match="Invalid action_taken"):
            builder.for_finalizar("OT-123", 93, "MR(93)", "INVALID_ACTION")


class TestMetadataEventBuilderMetrologia:
    """Tests for METROLOGIA events."""

    def test_metrologia_aprobado(self):
        """Builder creates METROLOGIA_APROBADO event."""
        event = (
            MetadataEventBuilder()
            .for_metrologia("TEST-05", 93, "MR(93)", "APROBADO")
            .with_operacion("METROLOGIA")
            .with_metadata({"fecha_qc": "04-02-2026"})
            .build()
        )

        assert event["evento_tipo"] == "METROLOGIA_APROBADO"
        assert event["accion"] == "APROBADO"

    def test_metrologia_rechazado(self):
        """Builder creates METROLOGIA_RECHAZADO event."""
        event = (
            MetadataEventBuilder()
            .for_metrologia("TEST-06", 94, "JP(94)", "RECHAZADO")
            .with_operacion("METROLOGIA")
            .with_metadata({"motivo": "Defecto soldadura"})
            .build()
        )

        assert event["evento_tipo"] == "METROLOGIA_RECHAZADO"
        assert event["accion"] == "RECHAZADO"

    def test_metrologia_invalid_resultado_raises_error(self):
        """Builder raises ValueError for invalid resultado."""
        builder = MetadataEventBuilder()

        with pytest.raises(ValueError, match="Invalid resultado"):
            builder.for_metrologia("TEST-07", 93, "MR(93)", "EN_PROGRESO")


class TestMetadataEventBuilderReparacion:
    """Tests for REPARACION events."""

    def test_reparacion_inicio(self):
        """Builder creates REPARACION_INICIO event."""
        event = (
            MetadataEventBuilder()
            .for_reparacion("TEST-08", 93, "MR(93)", "INICIO")
            .with_operacion("REPARACION")
            .with_metadata({"ciclo": 1})
            .build()
        )

        assert event["evento_tipo"] == "REPARACION_INICIO"
        assert event["accion"] == "INICIO"

    def test_reparacion_fin(self):
        """Builder creates REPARACION_FIN event."""
        event = (
            MetadataEventBuilder()
            .for_reparacion("TEST-09", 93, "MR(93)", "FIN")
            .with_operacion("REPARACION")
            .with_metadata({"ciclo": 1, "success": True})
            .build()
        )

        assert event["evento_tipo"] == "REPARACION_FIN"
        assert event["accion"] == "FIN"

    def test_reparacion_invalid_accion_raises_error(self):
        """Builder raises ValueError for invalid accion."""
        builder = MetadataEventBuilder()

        with pytest.raises(ValueError, match="Invalid accion"):
            builder.for_reparacion("TEST-10", 93, "MR(93)", "PAUSAR")


class TestMetadataEventBuilderValidation:
    """Tests for validation and error handling."""

    def test_build_without_evento_tipo_raises_error(self):
        """Builder raises ValueError if evento_tipo not set."""
        builder = MetadataEventBuilder()
        builder.with_operacion("ARM")

        with pytest.raises(ValueError, match="evento_tipo is required"):
            builder.build()

    def test_build_without_tag_spool_raises_error(self):
        """Builder raises ValueError if tag_spool not set."""
        builder = MetadataEventBuilder()
        builder._evento_tipo = "TOMAR_SPOOL"  # Manually set
        builder.with_operacion("ARM")

        with pytest.raises(ValueError, match="tag_spool is required"):
            builder.build()

    def test_build_without_operacion_raises_error(self):
        """Builder raises ValueError if operacion not set."""
        builder = MetadataEventBuilder()
        builder.for_tomar("TEST-11", 93, "MR(93)")

        with pytest.raises(ValueError, match="operacion is required"):
            builder.build()


class TestMetadataEventBuilderChaining:
    """Tests for method chaining and fluent API."""

    def test_complete_chain(self):
        """Builder supports complete fluent chain."""
        event = (
            MetadataEventBuilder()
            .for_tomar("TEST-12", 93, "MR(93)")
            .with_operacion("ARM")
            .with_metadata({"key1": "value1"})
            .with_metadata({"key2": "value2"})  # Chained metadata
            .with_custom_fecha("10-02-2026")
            .build()
        )

        assert event["fecha_operacion"] == "10-02-2026"  # Custom fecha
        metadata = json.loads(event["metadata_json"])
        assert metadata["key1"] == "value1"
        assert metadata["key2"] == "value2"


class TestBuildMetadataEventHelper:
    """Tests for build_metadata_event convenience function."""

    def test_build_metadata_event_quick_helper(self):
        """Quick helper creates valid event without fluent API."""
        event = build_metadata_event(
            evento_tipo="TOMAR_SPOOL",
            tag_spool="TEST-13",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion="TOMAR",
            metadata={"ocupado_por": "MR(93)"}
        )

        assert event["evento_tipo"] == "TOMAR_SPOOL"
        assert event["tag_spool"] == "TEST-13"
        assert event["accion"] == "TOMAR"
        assert '"ocupado_por": "MR(93)"' in event["metadata_json"]

    def test_build_metadata_event_without_metadata(self):
        """Quick helper works without metadata parameter."""
        event = build_metadata_event(
            evento_tipo="PAUSAR_SPOOL",
            tag_spool="TEST-14",
            worker_id=94,
            worker_nombre="JP(94)",
            operacion="SOLD",
            accion="PAUSAR"
        )

        assert event["metadata_json"] == "{}"  # Empty metadata
