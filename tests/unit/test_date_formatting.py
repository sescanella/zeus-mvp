"""
Tests específicos para validar estandarización de formatos de fecha.

Valida que todos los formatos de fecha usen DD-MM-YYYY y timezone Santiago.
"""
import pytest
from datetime import date, datetime
import pytz
from backend.utils.date_formatter import (
    now_chile,
    today_chile,
    format_date_for_sheets,
    format_datetime_for_sheets,
    get_timezone
)
from backend.models.metadata import MetadataEvent, EventoTipo, Accion


class TestDateFormatter:
    """Tests para funciones de date_formatter.py"""

    def test_timezone_is_santiago(self):
        """Verificar que timezone es America/Santiago"""
        tz = get_timezone()
        assert tz.zone == 'America/Santiago'

    def test_now_chile_returns_santiago_timezone(self):
        """now_chile() debe retornar datetime con timezone Santiago"""
        dt = now_chile()
        assert dt.tzinfo is not None
        assert dt.tzinfo.zone == 'America/Santiago'

    def test_today_chile_returns_date(self):
        """today_chile() debe retornar date object (sin hora)"""
        d = today_chile()
        assert isinstance(d, date)
        assert not isinstance(d, datetime)

    def test_format_date_for_sheets_dd_mm_yyyy(self):
        """format_date_for_sheets() debe retornar DD-MM-YYYY"""
        d = date(2026, 1, 28)
        result = format_date_for_sheets(d)
        assert result == "28-01-2026"

    def test_format_datetime_for_sheets_dd_mm_yyyy_hh_mm_ss(self):
        """format_datetime_for_sheets() debe retornar DD-MM-YYYY HH:MM:SS"""
        dt = datetime(2026, 1, 28, 14, 30, 45)
        result = format_datetime_for_sheets(dt)
        assert result == "28-01-2026 14:30:45"

    def test_format_date_with_leading_zeros(self):
        """format_date_for_sheets() debe añadir ceros a la izquierda"""
        d = date(2026, 1, 5)  # Day and month single digit
        result = format_date_for_sheets(d)
        assert result == "05-01-2026"

    def test_format_datetime_with_leading_zeros(self):
        """format_datetime_for_sheets() debe añadir ceros en hora/minuto/segundo"""
        dt = datetime(2026, 1, 5, 9, 5, 3)
        result = format_datetime_for_sheets(dt)
        assert result == "05-01-2026 09:05:03"


class TestMetadataEventFormatting:
    """Tests para MetadataEvent con nuevos formatos"""

    def test_metadata_event_timestamp_uses_santiago_timezone(self):
        """MetadataEvent debe usar timezone Santiago por defecto"""
        event = MetadataEvent(
            evento_tipo=EventoTipo.INICIAR_ARM,
            tag_spool="TEST-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="28-01-2026"
        )
        assert event.timestamp.tzinfo.zone == 'America/Santiago'

    def test_to_sheets_row_formats_timestamp_dd_mm_yyyy(self):
        """to_sheets_row() debe formatear timestamp como DD-MM-YYYY HH:MM:SS"""
        tz = pytz.timezone('America/Santiago')
        dt = datetime(2026, 1, 28, 14, 30, 0, tzinfo=tz)

        event = MetadataEvent(
            timestamp=dt,
            evento_tipo=EventoTipo.COMPLETAR_ARM,
            tag_spool="TEST-002",
            worker_id=94,
            worker_nombre="CP(94)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="28-01-2026"
        )

        row = event.to_sheets_row()
        # row[1] es el timestamp
        assert row[1] == "28-01-2026 14:30:00"

    def test_to_sheets_row_keeps_fecha_operacion_dd_mm_yyyy(self):
        """to_sheets_row() debe mantener fecha_operacion en DD-MM-YYYY"""
        event = MetadataEvent(
            evento_tipo=EventoTipo.INICIAR_SOLD,
            tag_spool="TEST-003",
            worker_id=95,
            worker_nombre="JP(95)",
            operacion="SOLD",
            accion=Accion.INICIAR,
            fecha_operacion="28-01-2026"
        )

        row = event.to_sheets_row()
        # row[8] es fecha_operacion
        assert row[8] == "28-01-2026"

    def test_timestamp_format_structure(self):
        """Timestamp debe tener estructura DD-MM-YYYY HH:MM:SS (2 guiones, 2 dos puntos)"""
        event = MetadataEvent(
            evento_tipo=EventoTipo.COMPLETAR_SOLD,
            tag_spool="TEST-004",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="SOLD",
            accion=Accion.COMPLETAR,
            fecha_operacion="28-01-2026"
        )

        row = event.to_sheets_row()
        timestamp_str = row[1]

        # Validar formato: DD-MM-YYYY HH:MM:SS
        assert timestamp_str.count('-') == 2  # DD-MM-YYYY
        assert timestamp_str.count(':') == 2  # HH:MM:SS
        assert ' ' in timestamp_str  # Espacio entre fecha y hora


class TestBackwardCompatibilityParsing:
    """Tests para validar que seguimos leyendo formatos antiguos"""

    def test_from_sheets_row_parses_new_format(self):
        """from_sheets_row() debe parsear nuevo formato DD-MM-YYYY HH:MM:SS"""
        row = [
            "uuid-123",
            "28-01-2026 14:30:00",  # Nuevo formato
            "COMPLETAR_ARM",
            "TEST-004",
            "93",
            "MR(93)",
            "ARM",
            "COMPLETAR",
            "28-01-2026",
            ""
        ]

        event = MetadataEvent.from_sheets_row(row)
        assert event.timestamp.year == 2026
        assert event.timestamp.month == 1
        assert event.timestamp.day == 28
        assert event.timestamp.hour == 14
        assert event.timestamp.minute == 30

    def test_from_sheets_row_parses_old_iso_format(self):
        """from_sheets_row() debe TAMBIÉN parsear formato antiguo ISO 8601"""
        row = [
            "uuid-456",
            "2025-12-10T14:30:00Z",  # Formato antiguo
            "INICIAR_ARM",
            "TEST-005",
            "94",
            "CP(94)",
            "ARM",
            "INICIAR",
            "10-12-2025",
            ""
        ]

        event = MetadataEvent.from_sheets_row(row)
        assert event.timestamp.year == 2025
        assert event.timestamp.month == 12
        assert event.timestamp.day == 10
        assert event.timestamp.hour == 14
        assert event.timestamp.minute == 30

    def test_new_format_has_santiago_timezone(self):
        """Nuevo formato debe tener timezone Santiago"""
        row = [
            "uuid-789",
            "28-01-2026 16:45:30",
            "COMPLETAR_SOLD",
            "TEST-006",
            "95",
            "JP(95)",
            "SOLD",
            "COMPLETAR",
            "28-01-2026",
            ""
        ]

        event = MetadataEvent.from_sheets_row(row)
        assert event.timestamp.tzinfo is not None
        assert event.timestamp.tzinfo.zone == 'America/Santiago'


class TestRoundTripFormatting:
    """Tests de round-trip: write → read → write"""

    def test_round_trip_metadata_event(self):
        """Escribir y leer MetadataEvent debe preservar formato"""
        # Create event
        original = MetadataEvent(
            evento_tipo=EventoTipo.COMPLETAR_SOLD,
            tag_spool="TEST-ROUNDTRIP",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="SOLD",
            accion=Accion.COMPLETAR,
            fecha_operacion="28-01-2026"
        )

        # to_sheets_row
        row = original.to_sheets_row()

        # from_sheets_row
        parsed = MetadataEvent.from_sheets_row(row)

        # Verify
        assert parsed.fecha_operacion == "28-01-2026"
        assert row[1].count(':') == 2  # DD-MM-YYYY HH:MM:SS tiene 2 ":"
        assert row[1].count('-') == 2  # DD-MM-YYYY tiene 2 "-"

    def test_round_trip_preserves_timestamp_format(self):
        """Round-trip debe preservar formato DD-MM-YYYY HH:MM:SS"""
        tz = pytz.timezone('America/Santiago')
        original_dt = datetime(2026, 1, 28, 10, 15, 30, tzinfo=tz)

        event = MetadataEvent(
            timestamp=original_dt,
            evento_tipo=EventoTipo.INICIAR_ARM,
            tag_spool="TEST-RT-2",
            worker_id=94,
            worker_nombre="CP(94)",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="28-01-2026"
        )

        row = event.to_sheets_row()
        parsed = MetadataEvent.from_sheets_row(row)

        # Verify timestamp components match
        assert parsed.timestamp.year == 2026
        assert parsed.timestamp.month == 1
        assert parsed.timestamp.day == 28
        assert parsed.timestamp.hour == 10
        assert parsed.timestamp.minute == 15
        assert parsed.timestamp.second == 30

    def test_round_trip_multiple_events(self):
        """Round-trip con múltiples eventos mantiene formato consistente"""
        events = [
            MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=f"TEST-{i}",
                worker_id=93 + i,
                worker_nombre=f"W{93 + i}({93 + i})",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="28-01-2026"
            )
            for i in range(3)
        ]

        for event in events:
            row = event.to_sheets_row()
            parsed = MetadataEvent.from_sheets_row(row)

            # All should have DD-MM-YYYY format
            assert parsed.fecha_operacion == "28-01-2026"
            # All timestamps should be DD-MM-YYYY HH:MM:SS
            assert row[1].count('-') == 2
            assert row[1].count(':') == 2
