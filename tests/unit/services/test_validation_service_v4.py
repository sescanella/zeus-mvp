"""
Unit tests for ValidationService v4.0 features (ARM prerequisite validation).

Tests:
- validate_arm_prerequisite with various scenarios
- INICIAR SOLD with validation failure
- SOLD disponibles filtering
- SOLD completion with mixed union types
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from backend.services.validation_service import ValidationService
from backend.exceptions import ArmPrerequisiteError
from backend.models.union import Union


class TestArmPrerequisiteValidation:
    """Test ARM prerequisite validation for SOLD operations."""

    @pytest.fixture
    def union_repository(self):
        """Mock UnionRepository."""
        return Mock()

    @pytest.fixture
    def validation_service(self, union_repository):
        """Create ValidationService with mocked dependencies."""
        return ValidationService(
            role_service=None,
            union_repository=union_repository
        )

    def test_validate_arm_prerequisite_no_unions(self, validation_service, union_repository):
        """Test validation fails when no ARM unions completed."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # No unions for this OT
        union_repository.get_by_ot.return_value = []

        # Act & Assert
        with pytest.raises(ArmPrerequisiteError) as exc_info:
            validation_service.validate_arm_prerequisite(tag_spool, ot)

        assert exc_info.value.data["tag_spool"] == tag_spool
        assert exc_info.value.data["unions_sin_armar"] == 0
        assert "Cannot start SOLD" in str(exc_info.value)

    def test_validate_arm_prerequisite_no_arm_completed(self, validation_service, union_repository):
        """Test validation fails when unions exist but none ARM-completed."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # Create unions without ARM completion (arm_fecha_fin is None)
        unions = [
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),
        ]
        union_repository.get_by_ot.return_value = unions

        # Act & Assert
        with pytest.raises(ArmPrerequisiteError) as exc_info:
            validation_service.validate_arm_prerequisite(tag_spool, ot)

        assert exc_info.value.data["tag_spool"] == tag_spool
        assert exc_info.value.data["unions_sin_armar"] == 3
        assert "Cannot start SOLD" in str(exc_info.value)

    def test_validate_arm_prerequisite_one_arm_completed(self, validation_service, union_repository):
        """Test validation passes with at least one ARM-completed union."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # Create unions with at least one ARM-completed
        unions = [
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=None),  # ARM done
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),  # ARM pending
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),  # ARM pending
        ]
        union_repository.get_by_ot.return_value = unions

        # Act
        result = validation_service.validate_arm_prerequisite(tag_spool, ot)

        # Assert
        assert result["valid"] is True
        assert result["unions_armadas"] == 1

    def test_validate_arm_prerequisite_all_arm_completed(self, validation_service, union_repository):
        """Test validation passes when all unions ARM-completed."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # Create unions all ARM-completed
        unions = [
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=None),
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=None),
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=datetime(2026, 2, 2)),
        ]
        union_repository.get_by_ot.return_value = unions

        # Act
        result = validation_service.validate_arm_prerequisite(tag_spool, ot)

        # Assert
        assert result["valid"] is True
        assert result["unions_armadas"] == 3

    def test_validate_arm_prerequisite_no_repository(self, validation_service):
        """Test validation fails gracefully when UnionRepository not configured."""
        # Arrange
        validation_service.union_repository = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            validation_service.validate_arm_prerequisite("OT-123", "123")

        assert "UnionRepository not configured" in str(exc_info.value)


class TestSOLDDisponiblesFiltering:
    """Test SOLD disponibles filtering to only show ARM-completed unions."""

    @pytest.fixture
    def union_repository(self):
        """Create actual UnionRepository with mocked sheets."""
        from backend.repositories.union_repository import UnionRepository
        from backend.repositories.sheets_repository import SheetsRepository

        sheets_repo = Mock(spec=SheetsRepository)
        return UnionRepository(sheets_repo)

    def test_get_disponibles_sold_filters_arm_complete(self, union_repository):
        """Test get_disponibles_sold_by_ot only returns ARM-completed unions."""
        # Arrange
        ot = "123"

        # Mock union data with mixed ARM completion
        unions = [
            Mock(
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM complete
                sol_fecha_fin=None,  # SOLD pending
                tipo_union="BW"
            ),
            Mock(
                arm_fecha_fin=None,  # ARM pending
                sol_fecha_fin=None,
                tipo_union="BW"
            ),
            Mock(
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM complete
                sol_fecha_fin=datetime(2026, 2, 2),  # SOLD complete
                tipo_union="BW"
            ),
        ]

        # Mock get_by_ot to return all unions
        union_repository.get_by_ot = Mock(return_value=unions)

        # Act
        disponibles = union_repository.get_disponibles_sold_by_ot(ot)

        # Assert
        # Only first union should be returned (ARM complete, SOLD pending)
        assert len(disponibles) == 1
        assert disponibles[0].arm_fecha_fin is not None
        assert disponibles[0].sol_fecha_fin is None


class TestSOLDCompletionLogic:
    """Test SOLD completion logic with mixed union types."""

    def test_sold_completion_counts_only_required_types(self):
        """Test SOLD COMPLETAR only counts BW/BR/SO/FILL/LET unions."""
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Verify constant includes expected types
        assert 'BW' in SOLD_REQUIRED_TYPES
        assert 'BR' in SOLD_REQUIRED_TYPES
        assert 'SO' in SOLD_REQUIRED_TYPES
        assert 'FILL' in SOLD_REQUIRED_TYPES
        assert 'LET' in SOLD_REQUIRED_TYPES
        assert 'FW' not in SOLD_REQUIRED_TYPES  # FW is ARM-only

    def test_sold_disponibles_filtering_by_type(self):
        """Test filtering disponibles to SOLD-required types only."""
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Simulate disponibles list with mixed types
        all_disponibles = [
            Mock(tipo_union='BW'),  # SOLD-required
            Mock(tipo_union='FW'),  # ARM-only (should filter out)
            Mock(tipo_union='BR'),  # SOLD-required
            Mock(tipo_union='FW'),  # ARM-only (should filter out)
            Mock(tipo_union='SO'),  # SOLD-required
        ]

        # Filter logic (from occupation_service.finalizar_spool)
        sold_disponibles = [
            u for u in all_disponibles
            if u.tipo_union in SOLD_REQUIRED_TYPES
        ]

        # Assert
        assert len(sold_disponibles) == 3  # Only BW, BR, SO
        assert all(u.tipo_union in SOLD_REQUIRED_TYPES for u in sold_disponibles)
        assert not any(u.tipo_union == 'FW' for u in sold_disponibles)




class TestIniciarSoldValidation:
    """Test INICIAR SOLD with ARM prerequisite validation."""

    @pytest.fixture
    def mocked_services(self):
        """Create mocked service dependencies."""
        from backend.repositories.sheets_repository import SheetsRepository
        from unittest.mock import AsyncMock

        redis_lock = Mock()
        redis_lock.acquire_lock = AsyncMock(return_value="lock-token-123")
        redis_lock.lazy_cleanup_one_abandoned_lock = AsyncMock()

        sheets_repo = Mock(spec=SheetsRepository)
        metadata_repo = Mock()

        conflict_service = Mock()
        conflict_service.update_with_retry = AsyncMock(return_value="version-uuid")

        redis_event = Mock()
        redis_event.publish_spool_update = AsyncMock()

        union_repo = Mock()
        validation_service = Mock()

        return {
            "redis_lock": redis_lock,
            "sheets_repo": sheets_repo,
            "metadata_repo": metadata_repo,
            "conflict_service": conflict_service,
            "redis_event": redis_event,
            "union_repo": union_repo,
            "validation_service": validation_service
        }





# =============================================================================
# H2 hardening — T-096 second line of defense on metrología entry
# =============================================================================
#
# Narrow scope (locked 2026-04-21 via empirical production audit):
#   Only partial SOLD blocks entry. ARM-level completeness is NOT checked,
#   because production contains legitimate legacy spools whose ARM was never
#   tracked at union level (MK-1343-MO-26627-016 is the observed case).
#   Blocking those would be a regression with no counterpart in the T-096
#   incident.
#
# See backend/scripts/diagnose_H2_guard_impact.py for the analysis that
# produced the REGRESSION_RISK count supporting this design.


class TestMetrologiaPreEntryUnionsGuard:
    """Ensure metrología entry validates Uniones state, not just dates."""

    @pytest.fixture
    def union_repository(self):
        return Mock()

    @pytest.fixture
    def validation_service(self, union_repository):
        return ValidationService(
            role_service=None, union_repository=union_repository
        )

    @staticmethod
    def _make_spool(
        tag="T-96-TEST", fecha_armado=True, fecha_soldadura=True, ocupado_por=None
    ):
        spool = Mock()
        spool.tag_spool = tag
        spool.fecha_armado = datetime(2026, 4, 1) if fecha_armado else None
        spool.fecha_soldadura = datetime(2026, 4, 2) if fecha_soldadura else None
        spool.fecha_qc_metrologia = None
        spool.estado_detalle = ""
        spool.ocupado_por = ocupado_por
        return spool

    def test_blocks_metrologia_when_sold_unions_pending(
        self, validation_service, union_repository
    ):
        """Reproduces the MK-1923-TW-17422-004 incident at validation time."""
        from backend.exceptions import DependenciasNoSatisfechasError

        spool = self._make_spool()
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),
                sol_fecha_fin=None,
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),
                sol_fecha_fin=None,
            ),
        ]

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_completar_metrologia(spool, worker_id=99)

        assert "SOLD" in exc_info.value.data["dependencia_faltante"]

    def test_allows_legacy_spool_whose_arm_was_not_tracked_at_union_level(
        self, validation_service, union_repository
    ):
        """Observed in production: MK-1343-MO-26627-016.
        Every SOLD-required union is soldered, but ARM was done at spool level
        (Fecha_Armado on the Operaciones row) and arm_fecha_fin was never set
        on any union. This spool must NOT be blocked from metrología."""
        spool = self._make_spool()
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=None,  # ARM never tracked per-union
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=None,  # ARM never tracked per-union
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
            Mock(
                tipo_union="FW",  # ARM-only type, legitimately SOLD-less
                arm_fecha_fin=None,
                sol_fecha_fin=None,
            ),
        ]

        # Must not raise: SOLD-required unions are complete, and no union is
        # ARM-tracked, so the conditional ARM check skips.
        validation_service.validar_puede_completar_metrologia(spool, worker_id=99)

    def test_blocks_metrologia_when_arm_partially_tracked_and_some_pending(
        self, validation_service, union_repository
    ):
        """Manual-edit scenario (round-2 auditor flag): a reviewer edited
        Fecha_Soldadura on Operaciones for a spool that IS tracked at union
        level (some unions already have arm_fecha_fin set) but not all unions
        finished ARM. Under the narrow SOLD-only guard this would have slipped
        through. The conditional ARM check catches it: "at least one union
        ARM-tracked" flips the guard on."""
        from backend.exceptions import DependenciasNoSatisfechasError

        spool = self._make_spool()
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),  # ARM tracked and done
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=None,  # ARM tracked (by spool convention) but pending
                sol_fecha_fin=datetime(2026, 4, 2),  # SOLD somehow set
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
        ]

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_completar_metrologia(spool, worker_id=99)

        assert "ARM" in exc_info.value.data["dependencia_faltante"]

    def test_allows_metrologia_when_all_unions_complete(
        self, validation_service, union_repository
    ):
        spool = self._make_spool()
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 4, 1),
                sol_fecha_fin=datetime(2026, 4, 2),
            ),
        ]

        # Should not raise.
        validation_service.validar_puede_completar_metrologia(spool, worker_id=99)

    def test_allows_legacy_spool_without_union_rows(
        self, validation_service, union_repository
    ):
        """Spools in Operaciones without any matching Uniones rows (legacy v2.1
        pre-migration) must pass through. get_by_spool returns an empty list."""
        spool = self._make_spool()
        union_repository.get_by_spool.return_value = []

        # Must not raise — empty list bypasses the cross-check.
        validation_service.validar_puede_completar_metrologia(spool, worker_id=99)

    def test_fallback_noop_when_union_repository_raises(
        self, validation_service, union_repository
    ):
        """If get_by_spool errors (Sheets down, timeout, etc.) the guard
        skips with a [H2_GUARD_FAILED] log rather than blocking. This is
        defence-in-depth — primary protection is the write-side fix in
        occupation_service."""
        spool = self._make_spool()
        union_repository.get_by_spool.side_effect = RuntimeError("sheets unavailable")

        # Must not raise — gracefully degrades to legacy behaviour.
        validation_service.validar_puede_completar_metrologia(spool, worker_id=99)

    def test_fallback_noop_when_union_repository_is_none(self):
        """ValidationService must remain backward-compatible with no UnionRepository."""
        service = ValidationService(role_service=None, union_repository=None)
        spool = self._make_spool()
        # Should not raise.
        service.validar_puede_completar_metrologia(spool, worker_id=99)


# ─── ARM fallback for stale Fecha_Armado ─────────────────────────────────────
#
# Production incident 2026-05-08: Matías reported "falta ARM completado" when
# attempting metrología on MK-1344-GW-27133-009. Direct sheet inspection
# showed Operaciones.Fecha_Armado='' but every Uniones.ARM_FECHA_FIN populated
# and counters at expected values. Root cause is in the write path (only
# OccupationService.finalizar_spool with action_taken==COMPLETAR writes the
# v2.1 columns); when the operation takes the PAUSAR branch the columns stay
# empty even though ARM is really done at the union level.
#
# These tests pin the read-side fallback that unblocks the user without
# requiring a data-fix migration: when Fecha_Armado is None, consult unions.


class TestArmFallbackForStaleFechaArmado:
    """ARM fallback in validar_puede_completar_metrologia."""

    @pytest.fixture
    def union_repository(self):
        return Mock()

    @pytest.fixture
    def validation_service(self, union_repository):
        return ValidationService(
            role_service=None, union_repository=union_repository
        )

    @staticmethod
    def _make_spool(tag="MK-1344-GW-27133-009", fecha_armado=False):
        """Default fecha_armado=False reproduces the bug scenario."""
        spool = Mock()
        spool.tag_spool = tag
        spool.fecha_armado = datetime(2026, 5, 8) if fecha_armado else None
        spool.fecha_soldadura = datetime(2026, 5, 8)
        spool.fecha_qc_metrologia = None
        spool.estado_detalle = ""
        spool.ocupado_por = None
        return spool

    def test_a_arm_fallback_passes_when_all_unions_have_arm_fecha_fin(
        self, validation_service, union_repository
    ):
        """The bug fix scenario: Fecha_Armado='' but all unions ARM-completed.
        Reproduces MK-1344-GW-27133-009 from 2026-05-08."""
        spool = self._make_spool(fecha_armado=False)
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 5, 8, 9, 47, 5),
                sol_fecha_fin=datetime(2026, 5, 8, 9, 49, 16),
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 5, 8, 9, 47, 5),
                sol_fecha_fin=datetime(2026, 5, 8, 9, 50, 26),
            ),
        ]
        # Must NOT raise — all unions ARM done, fallback accepts.
        validation_service.validar_puede_completar_metrologia(spool, worker_id=76)

    def test_b_arm_fallback_blocks_when_any_union_arm_fecha_fin_is_none(
        self, validation_service, union_repository
    ):
        """If even one union has arm_fecha_fin=None, fallback rejects.
        Mirrors the existing strict semantics: ARM means ALL uniones armed."""
        from backend.exceptions import DependenciasNoSatisfechasError

        spool = self._make_spool(fecha_armado=False)
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 5, 8),
                sol_fecha_fin=datetime(2026, 5, 8),
            ),
            Mock(
                tipo_union="BW",
                arm_fecha_fin=None,  # one pending → fallback must reject
                sol_fecha_fin=None,
            ),
        ]

        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            validation_service.validar_puede_completar_metrologia(spool, worker_id=76)

        assert exc_info.value.data["dependencia_faltante"] == "ARM completado"

    def test_c_arm_fallback_blocks_when_union_repository_unavailable(self):
        """If union_repository is None or get_by_spool raises, the fallback
        does NOT pretend ARM is done. We bail back to the strict legacy
        behavior — better to block than to admit an unverified spool."""
        from backend.exceptions import DependenciasNoSatisfechasError

        # Variant 1: union_repository is None.
        service_no_repo = ValidationService(
            role_service=None, union_repository=None
        )
        spool = self._make_spool(fecha_armado=False)
        with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
            service_no_repo.validar_puede_completar_metrologia(spool, worker_id=76)
        assert exc_info.value.data["dependencia_faltante"] == "ARM completado"

        # Variant 2: union_repository present but get_by_spool raises.
        union_repository = Mock()
        union_repository.get_by_spool.side_effect = RuntimeError("sheets down")
        service_failing_repo = ValidationService(
            role_service=None, union_repository=union_repository
        )
        with pytest.raises(DependenciasNoSatisfechasError):
            service_failing_repo.validar_puede_completar_metrologia(
                spool, worker_id=76
            )

        # Variant 3: get_by_spool returns empty list (no Uniones rows).
        # Fallback can't verify — must block.
        union_repository_empty = Mock()
        union_repository_empty.get_by_spool.return_value = []
        service_empty = ValidationService(
            role_service=None, union_repository=union_repository_empty
        )
        with pytest.raises(DependenciasNoSatisfechasError):
            service_empty.validar_puede_completar_metrologia(spool, worker_id=76)

    def test_d_existing_behavior_preserved_when_fecha_armado_is_set(
        self, validation_service, union_repository
    ):
        """Regression guard: when Fecha_Armado is populated, the new code path
        must not run. SOLD/H2 checks proceed as before."""
        spool = self._make_spool(fecha_armado=True)
        union_repository.get_by_spool.return_value = [
            Mock(
                tipo_union="BW",
                arm_fecha_fin=datetime(2026, 5, 8),
                sol_fecha_fin=datetime(2026, 5, 8),
            ),
        ]

        # Should not raise. The ARM check is short-circuited because
        # fecha_armado is truthy; existing flow continues.
        validation_service.validar_puede_completar_metrologia(spool, worker_id=76)

        # Confirm get_by_spool was still called (by the H2 SOLD guard, NOT by
        # the new ARM fallback). This proves we did not introduce a duplicate
        # query and that the SOLD guard remains active.
        assert union_repository.get_by_spool.call_count == 1

