"""
Tests unitarios para ValidationService.

Prueba la lógica de validación de reglas de negocio sin dependencias externas.
Coverage objetivo: >95%
"""
import pytest
from datetime import date

from backend.services.validation_service import ValidationService
from backend.models.spool import Spool
from backend.models.enums import ActionStatus, ActionType
from backend.exceptions import (
    OperacionNoPendienteError,
    OperacionYaIniciadaError,
    OperacionYaCompletadaError,
    DependenciasNoSatisfechasError,
    OperacionNoIniciadaError,
    NoAutorizadoError
)


# ==================== FIXTURES ====================

@pytest.fixture
def mock_metadata_repository(mocker):
    """
    Mock de MetadataRepository para v2.0.

    Genera eventos basados en el tag_spool para simular Event Sourcing:
    - SP-002: ARM en progreso (JP(93))
    - SP-003: ARM completado (JP(93))
    - SP-005: ARM completado + SOLD en progreso (MG(94))
    - Otros: Sin eventos (PENDIENTE)
    """
    from backend.models.metadata import MetadataEvent, EventoTipo, Accion
    from datetime import datetime

    def get_events_for_spool(tag_spool: str):
        """Genera eventos según el tag del spool para simular estados."""
        events = []

        if tag_spool == "SP-002":
            # ARM EN_PROGRESO: Solo evento INICIAR_ARM
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))
        elif tag_spool == "SP-003":
            # ARM COMPLETADO: INICIAR + COMPLETAR
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.COMPLETAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="08-11-2025",
                metadata_json=None
            ))
        elif tag_spool == "SP-005":
            # ARM COMPLETADO + SOLD EN_PROGRESO
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.COMPLETAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="08-11-2025",
                metadata_json=None
            ))
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_SOLD,
                tag_spool=tag_spool,
                worker_id=2,
                worker_nombre="MG(94)",
                operacion="SOLD",
                accion=Accion.INICIAR,
                fecha_operacion="09-11-2025",
                metadata_json=None
            ))
        elif tag_spool == "SP-020":
            # ARM EN_PROGRESO (para test ownership sin armador)
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="DESCONOCIDO",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))
        elif tag_spool == "SP-021":
            # SOLD EN_PROGRESO (para test ownership sin soldador)
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.COMPLETAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JP(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="08-11-2025",
                metadata_json=None
            ))
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_SOLD,
                tag_spool=tag_spool,
                worker_id=2,
                worker_nombre="DESCONOCIDO",
                operacion="SOLD",
                accion=Accion.INICIAR,
                fecha_operacion="09-11-2025",
                metadata_json=None
            ))
        elif tag_spool == "SP-030":
            # ARM EN_PROGRESO con trailing spaces
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="  JP(93)  ",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))
        elif tag_spool == "SP-031":
            # ARM EN_PROGRESO uppercase
            events.append(MetadataEvent(
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool=tag_spool,
                worker_id=1,
                worker_nombre="JUAN PÉREZ",
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="01-11-2025",
                metadata_json=None
            ))

        return events

    mock_repo = mocker.Mock()
    mock_repo.get_events_by_spool.side_effect = get_events_for_spool
    return mock_repo


@pytest.fixture
def validation_service():
    """Instancia del servicio de validación v2.1 Direct Read (sin dependencias)."""
    return ValidationService()


@pytest.fixture
def spool_arm_pendiente():
    """Spool listo para iniciar ARM (BA llena, BB vacía, ARM=0)."""
    return Spool(
        tag_spool="SP-001",
        arm=ActionStatus.PENDIENTE,
        sold=ActionStatus.PENDIENTE,
        fecha_materiales=date(2025, 11, 1),
        fecha_armado=None,
        fecha_soldadura=None,
        armador=None,
        soldador=None
    )


@pytest.fixture
def spool_arm_en_progreso():
    """Spool con ARM en progreso (ARM=0.1, BC llena)."""
    return Spool(
        tag_spool="SP-002",
        arm=ActionStatus.EN_PROGRESO,
        sold=ActionStatus.PENDIENTE,
        fecha_materiales=date(2025, 11, 1),
        fecha_armado=None,
        fecha_soldadura=None,
        armador="JP(93)",
        soldador=None
    )


@pytest.fixture
def spool_arm_completado():
    """Spool con ARM completado (ARM=1.0, BB llena)."""
    return Spool(
        tag_spool="SP-003",
        arm=ActionStatus.COMPLETADO,
        sold=ActionStatus.PENDIENTE,
        fecha_materiales=date(2025, 11, 1),
        fecha_armado=date(2025, 11, 8),
        fecha_soldadura=None,
        armador="JP(93)",
        soldador=None
    )


@pytest.fixture
def spool_sold_pendiente():
    """Spool listo para iniciar SOLD (BB llena, BD vacía, SOLD=0)."""
    return Spool(
        tag_spool="SP-004",
        arm=ActionStatus.COMPLETADO,
        sold=ActionStatus.PENDIENTE,
        fecha_materiales=date(2025, 11, 1),
        fecha_armado=date(2025, 11, 8),
        fecha_soldadura=None,
        armador="JP(93)",
        soldador=None
    )


@pytest.fixture
def spool_sold_en_progreso():
    """Spool con SOLD en progreso (SOLD=0.1, BE llena)."""
    return Spool(
        tag_spool="SP-005",
        arm=ActionStatus.COMPLETADO,
        sold=ActionStatus.EN_PROGRESO,
        fecha_materiales=date(2025, 11, 1),
        fecha_armado=date(2025, 11, 8),
        fecha_soldadura=None,
        armador="JP(93)",
        soldador="MG(94)"
    )


# ==================== HAPPY PATH TESTS ====================

class TestHappyPath:
    """Tests de casos exitosos (validaciones que pasan)."""

    def test_validar_puede_iniciar_arm_success(
        self,
        validation_service,
        spool_arm_pendiente
    ):
        """ARM puede iniciarse cuando todas las condiciones se cumplen."""
        # No debe lanzar excepción
        validation_service.validar_puede_iniciar_arm(spool_arm_pendiente)

    def test_validar_puede_completar_arm_success(
        self,
        validation_service,
        spool_arm_en_progreso
    ):
        """ARM puede completarse por el trabajador que la inició."""
        # No debe lanzar excepción (worker_id agregado en v2.0)
        validation_service.validar_puede_completar_arm(
            spool_arm_en_progreso,
            "JP(93)",
            worker_id=93
        )

    def test_validar_puede_iniciar_sold_success(
        self,
        validation_service,
        spool_sold_pendiente
    ):
        """SOLD puede iniciarse cuando todas las condiciones se cumplen."""
        # No debe lanzar excepción
        validation_service.validar_puede_iniciar_sold(spool_sold_pendiente)

    def test_validar_puede_completar_sold_success(
        self,
        validation_service,
        spool_sold_en_progreso
    ):
        """SOLD puede completarse por el trabajador que la inició."""
        # No debe lanzar excepción
        validation_service.validar_puede_completar_sold(spool_sold_en_progreso, "MG(94)", worker_id=94)


# ==================== STATUS VALIDATION TESTS ====================

class TestStatusValidation:
    """Tests de validación de estados (PENDIENTE/EN_PROGRESO)."""

    def test_iniciar_arm_fails_if_already_started(
        self,
        validation_service,
        spool_arm_en_progreso
    ):
        """No se puede iniciar ARM si ya está EN_PROGRESO."""
        with pytest.raises(OperacionYaIniciadaError) as exc_info:
            validation_service.validar_puede_iniciar_arm(spool_arm_en_progreso)

        assert exc_info.value.error_code == "OPERACION_YA_INICIADA"
        assert "SP-002" in exc_info.value.message
        assert "ARM" in exc_info.value.message

    def test_iniciar_arm_fails_if_completed(
        self,
        validation_service,
        spool_arm_completado
    ):
        """No se puede iniciar ARM si ya está COMPLETADO."""
        with pytest.raises(OperacionYaCompletadaError) as exc_info:
            validation_service.validar_puede_iniciar_arm(spool_arm_completado)

        assert exc_info.value.error_code == "OPERACION_YA_COMPLETADA"
        assert "SP-003" in exc_info.value.message

    def test_completar_arm_fails_if_not_started(
        self,
        validation_service,
        spool_arm_pendiente
    ):
        """No se puede completar ARM si no está EN_PROGRESO."""
        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_completar_arm(spool_arm_pendiente, "JP(93)", worker_id=93)

        assert exc_info.value.error_code == "OPERACION_NO_INICIADA"
        assert "SP-001" in exc_info.value.message
        assert "ARM" in exc_info.value.message

    def test_completar_arm_fails_if_completed(
        self,
        validation_service,
        spool_arm_completado
    ):
        """No se puede completar ARM si ya está COMPLETADO."""
        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_completar_arm(spool_arm_completado, "JP(93)", worker_id=93)

        assert exc_info.value.error_code == "OPERACION_NO_INICIADA"

    def test_iniciar_sold_fails_if_already_started(
        self,
        validation_service,
        spool_sold_en_progreso
    ):
        """No se puede iniciar SOLD si ya está EN_PROGRESO."""
        with pytest.raises(OperacionYaIniciadaError) as exc_info:
            validation_service.validar_puede_iniciar_sold(spool_sold_en_progreso)

        assert exc_info.value.error_code == "OPERACION_YA_INICIADA"
        assert "SP-005" in exc_info.value.message
        assert "SOLD" in exc_info.value.message

    def test_completar_sold_fails_if_not_started(
        self,
        validation_service,
        spool_sold_pendiente
    ):
        """No se puede completar SOLD si no está EN_PROGRESO."""
        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_completar_sold(spool_sold_pendiente, "MG(94)", worker_id=94)

        assert exc_info.value.error_code == "OPERACION_NO_INICIADA"
        assert "SP-004" in exc_info.value.message
        assert "SOLD" in exc_info.value.message


# ==================== DEPENDENCY TESTS ====================

class TestDependencies:
    """Tests de validación de dependencias (BA/BB/BD)."""

    def test_iniciar_arm_fails_if_ba_empty(self, validation_service):
        """No se puede iniciar ARM si BA (fecha_materiales) está vacía."""
        spool = Spool(
            tag_spool="SP-010",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=None,  # BA vacía
            fecha_armado=None,
            fecha_soldadura=None,
            armador=None,
            soldador=None
        )

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_iniciar_arm(spool)

        assert exc_info.value.error_code == "DEPENDENCIAS_NO_SATISFECHAS"
        assert "SP-010" in exc_info.value.message
        assert "fecha_materiales" in exc_info.value.message.lower()

    def test_iniciar_arm_fails_if_bb_filled(self, validation_service):
        """No se puede iniciar ARM si BB (fecha_armado) ya está llena."""
        spool = Spool(
            tag_spool="SP-011",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=date(2025, 11, 8),  # BB llena (incorrecto)
            fecha_soldadura=None,
            armador=None,
            soldador=None
        )

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_iniciar_arm(spool)

        assert exc_info.value.error_code == "DEPENDENCIAS_NO_SATISFECHAS"
        assert "SP-011" in exc_info.value.message
        assert "fecha_armado" in exc_info.value.message.lower()

    def test_iniciar_sold_fails_if_bb_empty(self, validation_service):
        """No se puede iniciar SOLD si BB (fecha_armado) está vacía."""
        spool = Spool(
            tag_spool="SP-012",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,  # BB vacía (ARM no completado)
            fecha_soldadura=None,
            armador=None,
            soldador=None
        )

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_iniciar_sold(spool)

        assert exc_info.value.error_code == "DEPENDENCIAS_NO_SATISFECHAS"
        assert "SP-012" in exc_info.value.message
        assert "fecha_armado" in exc_info.value.message.lower()

    def test_iniciar_sold_fails_if_bd_filled(self, validation_service):
        """No se puede iniciar SOLD si BD (fecha_soldadura) ya está llena."""
        spool = Spool(
            tag_spool="SP-013",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=date(2025, 11, 8),
            fecha_soldadura=date(2025, 11, 10),  # BD llena (incorrecto)
            armador="JP(93)",
            soldador=None
        )

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_iniciar_sold(spool)

        assert exc_info.value.error_code == "DEPENDENCIAS_NO_SATISFECHAS"
        assert "SP-013" in exc_info.value.message
        assert "fecha_soldadura" in exc_info.value.message.lower()


# ==================== CRITICAL: OWNERSHIP TESTS ====================

class TestOwnership:
    """Tests de validación de estado (sin restricción de ownership)."""

    def test_completar_arm_succeeds_with_different_worker(
        self,
        validation_service,
        spool_arm_en_progreso
    ):
        """Cualquier trabajador con rol Armador puede completar ARM iniciado por otro."""
        # spool_arm_en_progreso tiene armador="JP(93)"
        # Otro trabajador (MG(94)) puede completar si tiene el rol correcto
        # No debe lanzar excepción
        validation_service.validar_puede_completar_arm(
            spool_arm_en_progreso,
            "MG(94)",  # Trabajador diferente
            worker_id=94
        )

    def test_completar_arm_fails_if_bc_empty(self, validation_service):
        """No se puede completar ARM si BC (armador) está vacío (v2.1: NOT STARTED)."""
        spool = Spool(
            tag_spool="SP-020",
            arm=ActionStatus.EN_PROGRESO,  # v2.0 metadata state (ignored in v2.1)
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador=None,  # v2.1: armador=None means NOT STARTED
            soldador=None
        )

        # v2.1: armador=None → OperacionNoIniciadaError (operation never started)
        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_completar_arm(spool, "JP(93)", worker_id=93)

        assert exc_info.value.error_code == "OPERACION_NO_INICIADA"

    def test_completar_arm_case_insensitive_match(
        self,
        validation_service,
        spool_arm_en_progreso
    ):
        """Completar ARM es case-insensitive (JUAN PÉREZ == juan pérez)."""
        # spool_arm_en_progreso tiene armador="JP(93)"
        # Debe pasar con diferentes combinaciones de mayúsculas
        validation_service.validar_puede_completar_arm(
            spool_arm_en_progreso,
            "juan pérez",  # lowercase
            worker_id=93
        )
        validation_service.validar_puede_completar_arm(
            spool_arm_en_progreso,
            "JUAN PÉREZ",  # uppercase
            worker_id=93
        )
        validation_service.validar_puede_completar_arm(
            spool_arm_en_progreso,
            "JuAn PéReZ",  # mixed case
            worker_id=93
        )

    def test_completar_sold_succeeds_with_different_worker(
        self,
        validation_service,
        spool_sold_en_progreso
    ):
        """Cualquier trabajador con rol Soldador puede completar SOLD iniciado por otro."""
        # spool_sold_en_progreso tiene soldador="MG(94)"
        # Otro trabajador (JP(93)) puede completar si tiene el rol correcto
        # No debe lanzar excepción
        validation_service.validar_puede_completar_sold(
            spool_sold_en_progreso,
            "JP(93)",  # Trabajador diferente
            worker_id=93
        )

    def test_completar_sold_fails_if_be_empty(self, validation_service):
        """No se puede completar SOLD si BE (soldador) está vacío (v2.1: NOT STARTED)."""
        spool = Spool(
            tag_spool="SP-021",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.EN_PROGRESO,  # v2.0 metadata state (ignored in v2.1)
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=date(2025, 11, 8),
            fecha_soldadura=None,
            armador="JP(93)",
            soldador=None  # v2.1: soldador=None means NOT STARTED
        )

        # v2.1: soldador=None → OperacionNoIniciadaError (operation never started)
        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_completar_sold(spool, "MG(94)", worker_id=94)

        assert exc_info.value.error_code == "OPERACION_NO_INICIADA"

    def test_completar_sold_with_whitespace_normalization(
        self,
        validation_service,
        spool_sold_en_progreso
    ):
        """Completar SOLD normaliza espacios (trim leading/trailing)."""
        # spool_sold_en_progreso tiene soldador="MG(94)"
        # Debe pasar con espacios extra
        validation_service.validar_puede_completar_sold(
            spool_sold_en_progreso,
            "  MG(94)  ",  # espacios al inicio y final
            worker_id=94
        )
        validation_service.validar_puede_completar_sold(
            spool_sold_en_progreso,
            "MG(94) ",  # espacio al final
            worker_id=94
        )
        validation_service.validar_puede_completar_sold(
            spool_sold_en_progreso,
            " MG(94)",  # espacio al inicio
            worker_id=94
        )


# ==================== EDGE CASE TESTS ====================

class TestEdgeCases:
    """Tests de casos límite y situaciones especiales."""

    def test_completar_arm_with_trailing_spaces_in_worker_name(
        self,
        validation_service
    ):
        """Nombres con espacios extra deben normalizarse correctamente."""
        spool = Spool(
            tag_spool="SP-030",
            arm=ActionStatus.EN_PROGRESO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador="  JP(93)  ",  # Espacios extra en BC
            soldador=None
        )

        # Debe pasar con o sin espacios extra
        validation_service.validar_puede_completar_arm(spool, "JP(93)", worker_id=93)
        validation_service.validar_puede_completar_arm(spool, "  JP(93)  ", worker_id=93)

    def test_completar_with_uppercase_vs_lowercase_match(
        self,
        validation_service
    ):
        """Mayúsculas y minúsculas deben tratarse igual."""
        spool = Spool(
            tag_spool="SP-031",
            arm=ActionStatus.EN_PROGRESO,
            sold=ActionStatus.PENDIENTE,
            fecha_materiales=date(2025, 11, 1),
            fecha_armado=None,
            fecha_soldadura=None,
            armador="JUAN PÉREZ",  # Todo mayúsculas en BC
            soldador=None
        )

        # Debe pasar con cualquier combinación
        validation_service.validar_puede_completar_arm(spool, "juan pérez", worker_id=93)
        validation_service.validar_puede_completar_arm(spool, "JP(93)", worker_id=93)
        validation_service.validar_puede_completar_arm(spool, "JUAN PÉREZ", worker_id=93)

    # NOTE v2.0: Los siguientes tests se removieron porque en Event Sourcing
    # no es posible tener estados EN_PROGRESO con worker_nombre vacío/whitespace.
    # MetadataEvent valida que worker_nombre tenga al menos 1 carácter (post-strip).
    # Estos edge cases ya no pueden ocurrir en v2.0.
