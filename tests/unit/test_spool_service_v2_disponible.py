"""
Tests unitarios para fix v3.0: Spools pausados deben aparecer como disponibles.

Bug: Spools con Armador/Soldador pero sin Ocupado_Por (estado PAUSADO) no aparecían
como disponibles porque el filtro verificaba armador/soldador en lugar de ocupado_por.

Fix: Cambiar filtros de disponibilidad para verificar ocupado_por en lugar de
armador/soldador, permitiendo que spools PAUSADOS aparezcan como disponibles.

Compatible con v4.0 Uniones.
"""
import pytest
from unittest.mock import Mock, patch
from backend.services.spool_service_v2 import SpoolServiceV2
from backend.models.spool import Spool
from backend.models.enums import ActionStatus


class TestSpoolDisponibleFix:
    """Tests para verificar que spools PAUSADOS aparecen como disponibles."""

    @pytest.fixture
    def mock_sheets_repository(self):
        """Mock del SheetsRepository con header y filas de prueba."""
        mock = Mock()

        # Header row (row 1)
        header = [
            "", "NV", "", "", "", "", "TAG_SPOOL",  # cols 0-6
            *[""] * 25,  # cols 7-31
            "Fecha_Materiales",  # col 32
            "Fecha_Armado",  # col 33
            "Armador",  # col 34
            "Fecha_Soldadura",  # col 35
            "Soldador",  # col 36
            "Fecha_QC_Metrología",  # col 37
            *[""] * 26,  # cols 38-63
            "Ocupado_Por",  # col 64 (v3.0)
        ]

        # Data rows for different test cases
        rows = [
            header,  # Row 1 (header)

            # Row 2: PAUSADO ARM (armador filled, ocupado_por empty)
            # Should appear in disponible ARM list
            [
                "", "OT-001", "", "", "", "", "TEST-PAUSADO-ARM",
                *[""] * 25,
                "20-01-2026",  # Fecha_Materiales
                "",  # Fecha_Armado (empty - not complete)
                "MR(93)",  # Armador (filled - work initiated)
                "",  # Fecha_Soldadura
                "",  # Soldador
                "",  # Fecha_QC_Metrología
                *[""] * 26,
                "",  # Ocupado_Por (empty - paused/released)
            ],

            # Row 3: PENDIENTE ARM (armador empty, ocupado_por empty)
            # Should appear in disponible ARM list
            [
                "", "OT-002", "", "", "", "", "TEST-PENDIENTE-ARM",
                *[""] * 25,
                "21-01-2026",  # Fecha_Materiales
                "",  # Fecha_Armado
                "",  # Armador (empty - never started)
                "",  # Fecha_Soldadura
                "",  # Soldador
                "",  # Fecha_QC_Metrología
                *[""] * 26,
                "",  # Ocupado_Por (empty)
            ],

            # Row 4: OCUPADO ARM (armador filled, ocupado_por filled)
            # Should NOT appear in disponible ARM list
            [
                "", "OT-003", "", "", "", "", "TEST-OCUPADO-ARM",
                *[""] * 25,
                "22-01-2026",  # Fecha_Materiales
                "",  # Fecha_Armado
                "MR(93)",  # Armador (filled)
                "",  # Fecha_Soldadura
                "",  # Soldador
                "",  # Fecha_QC_Metrología
                *[""] * 26,
                "MR(93)",  # Ocupado_Por (filled - currently occupied)
            ],

            # Row 5: PAUSADO SOLD (soldador filled, ocupado_por empty)
            # Should appear in disponible SOLD list
            [
                "", "OT-004", "", "", "", "", "TEST-PAUSADO-SOLD",
                *[""] * 25,
                "20-01-2026",  # Fecha_Materiales
                "25-01-2026",  # Fecha_Armado (ARM complete)
                "MR(93)",  # Armador
                "",  # Fecha_Soldadura (empty - not complete)
                "JD(45)",  # Soldador (filled - work initiated)
                "",  # Fecha_QC_Metrología
                *[""] * 26,
                "",  # Ocupado_Por (empty - paused/released)
            ],

            # Row 6: PENDIENTE SOLD (soldador empty, ocupado_por empty)
            # Should appear in disponible SOLD list
            [
                "", "OT-005", "", "", "", "", "TEST-PENDIENTE-SOLD",
                *[""] * 25,
                "20-01-2026",  # Fecha_Materiales
                "26-01-2026",  # Fecha_Armado (ARM complete)
                "MR(93)",  # Armador
                "",  # Fecha_Soldadura
                "",  # Soldador (empty - never started)
                "",  # Fecha_QC_Metrología
                *[""] * 26,
                "",  # Ocupado_Por (empty)
            ],
        ]

        mock.read_worksheet.return_value = rows
        return mock

    @pytest.fixture
    def spool_service(self, mock_sheets_repository):
        """Instancia de SpoolServiceV2 con mock repository."""
        with patch('backend.services.spool_service_v2.SheetsRepository', return_value=mock_sheets_repository):
            with patch('backend.core.column_map_cache.ColumnMapCache.get_or_build') as mock_cache:
                # Mock column map
                mock_cache.return_value = {
                    "TAG_SPOOL": 6,
                    "NV": 1,
                    "Fecha_Materiales": 32,
                    "Fecha_Armado": 33,
                    "Armador": 34,
                    "Fecha_Soldadura": 35,
                    "Soldador": 36,
                    "Fecha_QC_Metrología": 37,
                    "Ocupado_Por": 64,
                }

                with patch('backend.core.column_map_cache.ColumnMapCache.validate_critical_columns') as mock_validate:
                    mock_validate.return_value = (True, [])

                    service = SpoolServiceV2(sheets_repository=mock_sheets_repository)
                    return service

    def test_pausado_arm_appears_as_disponible(self, spool_service):
        """
        Test: Spools pausados ARM (Armador filled, Ocupado_Por empty) deben aparecer como disponibles.

        Bug original: No aparecían porque filtro verificaba armador is None.
        Fix v3.0: Verificar ocupado_por is None.
        """
        # Act
        result = spool_service.get_spools_disponibles_para_iniciar_arm()
        tags = [s.tag_spool for s in result]

        # Assert
        assert "TEST-PAUSADO-ARM" in tags, "Spool pausado ARM debe aparecer como disponible"

        # Verify spool properties
        spool_pausado = next(s for s in result if s.tag_spool == "TEST-PAUSADO-ARM")
        assert spool_pausado.armador == "MR(93)", "Armador debe estar preservado"
        assert spool_pausado.ocupado_por is None, "Ocupado_Por debe estar vacío (pausado)"
        assert spool_pausado.fecha_materiales is not None, "Fecha_Materiales debe estar llena"

    def test_pendiente_arm_still_works(self, spool_service):
        """
        Test de regresión: Spools PENDIENTE ARM (Armador=None, Ocupado_Por=None) deben seguir funcionando.

        Verifica que el fix no rompa el comportamiento existente para spools nunca iniciados.
        """
        # Act
        result = spool_service.get_spools_disponibles_para_iniciar_arm()
        tags = [s.tag_spool for s in result]

        # Assert
        assert "TEST-PENDIENTE-ARM" in tags, "Spool pendiente ARM debe aparecer como disponible"

        # Verify spool properties
        spool_pendiente = next(s for s in result if s.tag_spool == "TEST-PENDIENTE-ARM")
        assert spool_pendiente.armador is None, "Armador debe estar vacío (nunca iniciado)"
        assert spool_pendiente.ocupado_por is None, "Ocupado_Por debe estar vacío"

    def test_ocupado_arm_does_not_appear(self, spool_service):
        """
        Test: Spools OCUPADOS ARM (Ocupado_Por filled) NO deben aparecer como disponibles.

        Verifica que el filtro sigue excluyendo spools actualmente ocupados.
        """
        # Act
        result = spool_service.get_spools_disponibles_para_iniciar_arm()
        tags = [s.tag_spool for s in result]

        # Assert
        assert "TEST-OCUPADO-ARM" not in tags, "Spool ocupado ARM NO debe aparecer como disponible"

    def test_pausado_sold_appears_as_disponible(self, spool_service):
        """
        Test: Spools pausados SOLD (Soldador filled, Ocupado_Por empty) deben aparecer como disponibles.

        Mismo fix para SOLD que para ARM.
        """
        # Act
        result = spool_service.get_spools_disponibles_para_iniciar_sold()
        tags = [s.tag_spool for s in result]

        # Assert
        assert "TEST-PAUSADO-SOLD" in tags, "Spool pausado SOLD debe aparecer como disponible"

        # Verify spool properties
        spool_pausado = next(s for s in result if s.tag_spool == "TEST-PAUSADO-SOLD")
        assert spool_pausado.soldador == "JD(45)", "Soldador debe estar preservado"
        assert spool_pausado.ocupado_por is None, "Ocupado_Por debe estar vacío (pausado)"
        assert spool_pausado.fecha_armado is not None, "Fecha_Armado debe estar llena (prerequisito)"

    def test_pendiente_sold_still_works(self, spool_service):
        """
        Test de regresión: Spools PENDIENTE SOLD (Soldador=None, Ocupado_Por=None) deben seguir funcionando.
        """
        # Act
        result = spool_service.get_spools_disponibles_para_iniciar_sold()
        tags = [s.tag_spool for s in result]

        # Assert
        assert "TEST-PENDIENTE-SOLD" in tags, "Spool pendiente SOLD debe aparecer como disponible"

        # Verify spool properties
        spool_pendiente = next(s for s in result if s.tag_spool == "TEST-PENDIENTE-SOLD")
        assert spool_pendiente.soldador is None, "Soldador debe estar vacío (nunca iniciado)"
        assert spool_pendiente.ocupado_por is None, "Ocupado_Por debe estar vacío"

    def test_parse_spool_row_includes_ocupado_por(self, spool_service):
        """
        Test: parse_spool_row() debe parsear correctamente la columna Ocupado_Por.

        Verifica que el método parse_spool_row incluye el nuevo campo v3.0.
        """
        # Arrange
        row = [
            "", "OT-999", "", "", "", "", "TEST-PARSE",
            *[""] * 25,
            "20-01-2026",  # Fecha_Materiales
            "",  # Fecha_Armado
            "MR(93)",  # Armador
            "",  # Fecha_Soldadura
            "",  # Soldador
            "",  # Fecha_QC_Metrología
            *[""] * 26,
            "JP(94)",  # Ocupado_Por
        ]

        # Act
        spool = spool_service.parse_spool_row(row)

        # Assert
        assert spool.ocupado_por == "JP(94)", "parse_spool_row debe incluir ocupado_por"
        assert spool.armador == "MR(93)", "Armador debe estar parseado correctamente"

    def test_empty_ocupado_por_is_none(self, spool_service):
        """
        Test: Ocupado_Por vacío debe convertirse en None (no string vacío).

        Verifica normalización de valores vacíos.
        """
        # Arrange
        row = [
            "", "OT-999", "", "", "", "", "TEST-EMPTY",
            *[""] * 25,
            "20-01-2026",  # Fecha_Materiales
            "",  # Fecha_Armado
            "",  # Armador
            "",  # Fecha_Soldadura
            "",  # Soldador
            "",  # Fecha_QC_Metrología
            *[""] * 26,
            "",  # Ocupado_Por (empty string)
        ]

        # Act
        spool = spool_service.parse_spool_row(row)

        # Assert
        assert spool.ocupado_por is None, "Ocupado_Por vacío debe ser None, no string vacío"
