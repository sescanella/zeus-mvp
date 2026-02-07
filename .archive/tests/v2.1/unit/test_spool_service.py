"""
Tests unitarios para SpoolService.

Prueba la lógica de filtrado y búsqueda de spools.
Coverage objetivo: >85%
"""
import pytest
from datetime import date
from unittest.mock import Mock, MagicMock

from backend.services.spool_service import SpoolService
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.spool import Spool
from backend.models.enums import ActionStatus, ActionType


# ==================== FIXTURES ====================

@pytest.fixture
def mock_sheets_repository(mocker):
    """Mock del repositorio de Google Sheets."""
    return mocker.Mock(spec=SheetsRepository)


@pytest.fixture
def validation_service():
    """Instancia real de ValidationService para tests."""
    return ValidationService()


@pytest.fixture
def spool_service(mock_sheets_repository, validation_service):
    """Instancia de SpoolService con dependencias mockeadas."""
    return SpoolService(
        sheets_repository=mock_sheets_repository,
        validation_service=validation_service
    )


@pytest.fixture
def sample_spools_data():
    """
    Datos de prueba con spools en diferentes estados.

    Incluye spools para probar todos los escenarios de filtrado.
    """
    return [
        # SP-001: Listo para iniciar ARM (BA llena, BB vacía, ARM=0)
        Spool(
            tag_spool="SP-001",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador=None,
            soldador=None
        ),
        # SP-002: ARM en progreso por Juan (ARM=0.1, BC=JP(93))
        Spool(
            tag_spool="SP-002",
            arm=ActionStatus.EN_PROGRESO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador="JP(93)",
            soldador=None
        ),
        # SP-003: ARM completado, listo para iniciar SOLD (BB llena, BD vacía, SOLD=0)
        Spool(
            tag_spool="SP-003",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=date(2025, 11, 8),
            fecha_soldadura=None,
            armador="JP(93)",
            soldador=None
        ),
        # SP-004: SOLD en progreso por María (SOLD=0.1, BE=MG(94))
        Spool(
            tag_spool="SP-004",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.EN_PROGRESO,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=date(2025, 11, 8),
            fecha_soldadura=None,
            armador="JP(93)",
            soldador="MG(94)"
        ),
        # SP-005: Sin materiales, no puede iniciar ARM (BA vacía)
        Spool(
            tag_spool="SP-005",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=None,
            fecha_armado=None,
            fecha_soldadura=None,
            armador=None,
            soldador=None
        ),
        # SP-006: ARM ya iniciado, no puede volver a iniciar
        Spool(
            tag_spool="SP-006",
            arm=ActionStatus.EN_PROGRESO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador="PL(95)",
            soldador=None
        ),
        # SP-007: ARM completado pero sin BB (inconsistente, no puede iniciar SOLD)
        Spool(
            tag_spool="SP-007",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,  # Inconsistente: completado pero sin fecha
            fecha_soldadura=None,
            armador="JP(93)",
            soldador=None
        ),
    ]


def mock_parse_spool_row(spools_data):
    """Helper para crear una función de parseo mockeada."""
    def parse_row(row):
        # Simplemente retornar el spool correspondiente al índice
        index = int(row[0])  # Asumiendo que row[0] es el índice
        return spools_data[index]
    return parse_row


# ==================== TESTS: FILTERING INICIAR ====================

class TestGetSpoolsParaIniciar:
    """Tests de filtrado para operaciones de INICIAR."""

    def test_get_spools_para_iniciar_arm_returns_eligible_only(
        self,
        spool_service,
        mock_sheets_repository,
        sample_spools_data,
        mocker
    ):
        """get_spools_para_iniciar(ARM) retorna solo spools elegibles."""
        # Mock repository para retornar filas dummy
        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],  # Header row
            *[['row'] for _ in sample_spools_data]  # Data rows
        ]

        # Mock sheets_service.parse_spool_row para retornar sample_spools_data
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=sample_spools_data
        )

        # Ejecutar filtrado
        result = spool_service.get_spools_para_iniciar(ActionType.ARM)

        # Verificar: solo SP-001 es elegible (BA llena, BB vacía, ARM=0)
        assert len(result) == 1
        assert result[0].tag_spool == "SP-001"

    def test_get_spools_para_iniciar_arm_excludes_started(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_iniciar(ARM) excluye spools ya iniciados."""
        # Crear spools con ARM en progreso o completado
        spools = [
            Spool(
                tag_spool="SP-010",
                arm=ActionStatus.EN_PROGRESO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador="JP(93)",
                soldador=None
            ),
            Spool(
                tag_spool="SP-011",
                arm=ActionStatus.COMPLETADO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=date(2025, 11, 8),
                fecha_soldadura=None,
                armador="JP(93)",
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar
        result = spool_service.get_spools_para_iniciar(ActionType.ARM)

        # Verificar: ninguno es elegible (ambos ya iniciados o completados)
        assert len(result) == 0

    def test_get_spools_para_iniciar_sold_requires_bb_filled(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_iniciar(SOLD) solo retorna spools con BB llena."""
        spools = [
            # SP-020: BB llena, elegible para SOLD
            Spool(
                tag_spool="SP-020",
                arm=ActionStatus.COMPLETADO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=date(2025, 11, 8),  # BB llena
                fecha_soldadura=None,
                armador="JP(93)",
                soldador=None
            ),
            # SP-021: BB vacía, NO elegible
            Spool(
                tag_spool="SP-021",
                arm=ActionStatus.PENDIENTE,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,  # BB vacía
                fecha_soldadura=None,
                armador=None,
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar
        result = spool_service.get_spools_para_iniciar(ActionType.SOLD)

        # Verificar: solo SP-020 es elegible
        assert len(result) == 1
        assert result[0].tag_spool == "SP-020"

    def test_get_spools_para_iniciar_sold_excludes_started(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_iniciar(SOLD) excluye spools ya iniciados."""
        spools = [
            Spool(
                tag_spool="SP-030",
                arm=ActionStatus.COMPLETADO,
                sold=ActionStatus.EN_PROGRESO,  # Ya iniciado
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=date(2025, 11, 8),
                fecha_soldadura=None,
                armador="JP(93)",
                soldador="MG(94)"
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar
        result = spool_service.get_spools_para_iniciar(ActionType.SOLD)

        # Verificar: ninguno elegible
        assert len(result) == 0

    def test_get_spools_para_iniciar_returns_empty_if_none_eligible(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_iniciar retorna lista vacía si no hay elegibles."""
        # Spools sin materiales
        spools = [
            Spool(
                tag_spool="SP-040",
                arm=ActionStatus.PENDIENTE,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=None,  # Sin materiales
                fecha_armado=None,
                fecha_soldadura=None,
                armador=None,
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar
        result = spool_service.get_spools_para_iniciar(ActionType.ARM)

        # Verificar: lista vacía
        assert len(result) == 0
        assert isinstance(result, list)


# ==================== TESTS: FILTERING COMPLETAR ====================

class TestGetSpoolsParaCompletar:
    """Tests CRÍTICOS de filtrado para COMPLETAR (ownership validation)."""

    def test_get_spools_para_completar_arm_returns_only_worker_spools(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_completar(ARM) retorna solo spools del trabajador."""
        spools = [
            # SP-050: Juan es el armador
            Spool(
                tag_spool="SP-050",
                arm=ActionStatus.EN_PROGRESO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador="JP(93)",
                soldador=None
            ),
            # SP-051: María es la armadora (no Juan)
            Spool(
                tag_spool="SP-051",
                arm=ActionStatus.EN_PROGRESO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador="MG(94)",
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar para Juan
        result = spool_service.get_spools_para_completar(
            ActionType.ARM,
            "JP(93)"
        )

        # Verificar: solo SP-050 (Juan es el armador)
        assert len(result) == 1
        assert result[0].tag_spool == "SP-050"
        assert result[0].armador == "JP(93)"

    def test_get_spools_para_completar_arm_excludes_other_workers(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_completar excluye spools de otros trabajadores."""
        spools = [
            Spool(
                tag_spool="SP-060",
                arm=ActionStatus.EN_PROGRESO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador="PL(95)",  # Otro trabajador
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar para Juan (no es el armador)
        result = spool_service.get_spools_para_completar(
            ActionType.ARM,
            "JP(93)"
        )

        # Verificar: lista vacía (Juan no es el armador)
        assert len(result) == 0

    def test_get_spools_para_completar_arm_excludes_not_started(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_completar excluye spools no iniciados (ARM != 0.1)."""
        spools = [
            Spool(
                tag_spool="SP-070",
                arm=ActionStatus.PENDIENTE,  # No iniciado
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador=None,
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar
        result = spool_service.get_spools_para_completar(
            ActionType.ARM,
            "JP(93)"
        )

        # Verificar: lista vacía (no iniciado)
        assert len(result) == 0

    def test_get_spools_para_completar_sold_returns_only_worker_spools(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_completar(SOLD) retorna solo spools del trabajador."""
        spools = [
            Spool(
                tag_spool="SP-080",
                arm=ActionStatus.COMPLETADO,
                sold=ActionStatus.EN_PROGRESO,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=date(2025, 11, 8),
                fecha_soldadura=None,
                armador="JP(93)",
                soldador="MG(94)"  # María es la soldadora
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar para María
        result = spool_service.get_spools_para_completar(
            ActionType.SOLD,
            "MG(94)"
        )

        # Verificar: SP-080 aparece (María es la soldadora)
        assert len(result) == 1
        assert result[0].tag_spool == "SP-080"

    def test_get_spools_para_completar_returns_empty_if_worker_has_none(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_completar retorna vacío si trabajador sin spools."""
        spools = [
            Spool(
                tag_spool="SP-090",
                arm=ActionStatus.EN_PROGRESO,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador="PL(95)",
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar para trabajador sin spools asignados
        result = spool_service.get_spools_para_completar(
            ActionType.ARM,
            "Trabajador Nuevo"
        )

        # Verificar: lista vacía
        assert len(result) == 0

    def test_get_spools_para_completar_case_insensitive_worker_match(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """get_spools_para_completar funciona case-insensitive."""
        spool = Spool(
            tag_spool="SP-100",
            arm=ActionStatus.EN_PROGRESO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador="JP(93)",  # Mayúsculas y minúsculas mixtas
            soldador=None
        )

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            ['row']
        ]

        # Use lambda to return same spool each time (not exhausted)
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            return_value=spool
        )

        # Ejecutar con diferentes combinaciones de case
        result_lower = spool_service.get_spools_para_completar(
            ActionType.ARM,
            "juan pérez"  # todo minúsculas
        )
        result_upper = spool_service.get_spools_para_completar(
            ActionType.ARM,
            "JUAN PÉREZ"  # todo mayúsculas
        )

        # Verificar: ambos retornan el spool
        assert len(result_lower) == 1
        assert len(result_upper) == 1


# ==================== TESTS: SEARCH ====================

class TestFindSpoolByTag:
    """Tests de búsqueda de spools por TAG."""

    def test_find_spool_by_tag_exact_match(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """find_spool_by_tag encuentra spool con TAG exacto."""
        spools = [
            Spool(
                tag_spool="MK-1335-CW-25238-011",
                arm=ActionStatus.PENDIENTE,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador=None,
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar
        result = spool_service.find_spool_by_tag("MK-1335-CW-25238-011")

        # Verificar
        assert result is not None
        assert result.tag_spool == "MK-1335-CW-25238-011"

    def test_find_spool_by_tag_case_insensitive(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """find_spool_by_tag funciona case-insensitive."""
        spool = Spool(
            tag_spool="MK-TEST-001",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador=None,
            soldador=None
        )

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            ['row']
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            return_value=spool
        )

        # Ejecutar con diferentes cases
        result_lower = spool_service.find_spool_by_tag("mk-test-001")
        result_upper = spool_service.find_spool_by_tag("MK-TEST-001")

        # Verificar: ambos encuentran el spool
        assert result_lower is not None
        assert result_upper is not None
        assert result_lower.tag_spool == "MK-TEST-001"

    def test_find_spool_by_tag_with_whitespace(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """find_spool_by_tag normaliza espacios."""
        spools = [
            Spool(
                tag_spool="MK-TEST-002",
                arm=ActionStatus.PENDIENTE,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador=None,
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar con espacios extra
        result = spool_service.find_spool_by_tag("  MK-TEST-002  ")

        # Verificar: encuentra el spool
        assert result is not None
        assert result.tag_spool == "MK-TEST-002"

    def test_find_spool_by_tag_not_found_returns_none(
        self,
        spool_service,
        mock_sheets_repository,
        mocker
    ):
        """find_spool_by_tag retorna None si no encuentra."""
        spools = [
            Spool(
                tag_spool="MK-TEST-003",
                arm=ActionStatus.PENDIENTE,
                sold=ActionStatus.PENDIENTE,
                fecha_materiales=date(2025, 11, 1),
                fecha_armado=None,
                fecha_soldadura=None,
                armador=None,
                soldador=None
            ),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in spools]
        ]
        mocker.patch.object(
            spool_service.sheets_service,
            'parse_spool_row',
            side_effect=spools
        )

        # Ejecutar con TAG inexistente
        result = spool_service.find_spool_by_tag("MK-NONEXISTENT")

        # Verificar: retorna None
        assert result is None
