"""
Unit tests for FINALIZAR action_override feature (API-03).

Tests that FinalizarRequest accepts action_override field and that
finalizar_spool() correctly handles:
- action_override=PAUSAR: clears occupation without writing to Uniones
- action_override=COMPLETAR: auto-selects all disponibles and processes them
- action_override=COMPLETAR with 0 disponibles: completes gracefully
- action_override=None (default): preserves existing auto-determination behavior

Reference: .planning/phases/00-backend-nuevos-endpoints/00-03-PLAN.md
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, date
from pydantic import ValidationError

from backend.services.occupation_service import OccupationService
from backend.models.occupation import (
    FinalizarRequest,
    OccupationResponse
)
from backend.models.spool import Spool
from backend.models.union import Union
from backend.models.enums import ActionType


# ============================================================================
# FIXTURES
# ============================================================================

def make_union(n: int, dn: float = 2.5, tipo: str = "BW") -> Union:
    """Create a test Union object."""
    return Union(
        id=f"OT-100+{n}",
        ot="100",
        tag_spool="TEST-SPOOL",
        n_union=n,
        dn_union=dn,
        tipo_union=tipo,
        arm_fecha_inicio=None,
        arm_fecha_fin=None,
        arm_worker=None,
        sol_fecha_inicio=None,
        sol_fecha_fin=None,
        sol_worker=None,
        ndt_fecha=None,
        ndt_status=None,
        version="uuid-test",
        creado_por="SYSTEM(0)",
        fecha_creacion=datetime(2026, 1, 1)
    )


@pytest.fixture
def mock_sheets_repo():
    repo = MagicMock()

    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "TEST-SPOOL"
    mock_spool.ot = "100"
    mock_spool.total_uniones = 5  # v4.0 spool
    mock_spool.ocupado_por = "MR(93)"
    mock_spool.fecha_ocupacion = "10-03-2026 09:00:00"
    mock_spool.fecha_materiales = date(2026, 1, 15)
    mock_spool.armador = None
    mock_spool.soldador = None
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None

    repo.get_spool_by_tag = MagicMock(return_value=mock_spool)

    # Headers for ColumnMapCache
    mock_headers = [
        "TAG_SPOOL", "OT", "NV", "Fecha_Materiales", "Fecha_Armado", "Armador",
        "Fecha_Soldadura", "Soldador", "Ocupado_Por", "Fecha_Ocupacion",
        "version", "Estado_Detalle", "Total_Uniones"
    ]
    repo.read_worksheet = MagicMock(return_value=[mock_headers])
    repo.find_row_by_column_value = MagicMock(return_value=2)
    repo.batch_update_by_column_name = MagicMock()
    repo._index_to_column_letter = MagicMock(return_value="A")

    return repo


@pytest.fixture
def mock_union_repo():
    repo = MagicMock()

    disponibles = [make_union(i) for i in range(1, 6)]  # 5 unions
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=disponibles)
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=disponibles)
    repo.batch_update_arm_full = MagicMock(return_value=5)
    repo.batch_update_sold_full = MagicMock(return_value=5)
    repo.get_by_ids = MagicMock(return_value=disponibles)

    return repo


@pytest.fixture
def mock_metadata_repo():
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_conflict_service():
    service = MagicMock()
    service.update_with_retry = AsyncMock(return_value="new-version")
    return service


@pytest.fixture
def occupation_service(mock_sheets_repo, mock_union_repo, mock_metadata_repo, mock_conflict_service):
    """OccupationService with union repository (v4.0)."""
    return OccupationService(
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        conflict_service=mock_conflict_service,
        union_repository=mock_union_repo
    )


# ============================================================================
# MODEL VALIDATION TESTS
# ============================================================================

class TestFinalizarRequestActionOverride:
    """Tests for FinalizarRequest.action_override field."""

    def test_action_override_none_by_default(self):
        """FinalizarRequest without action_override defaults to None."""
        req = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=["OT-100+1"]
        )
        assert req.action_override is None

    def test_action_override_pausar_accepted(self):
        """FinalizarRequest accepts action_override=PAUSAR."""
        req = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="PAUSAR"
        )
        assert req.action_override == "PAUSAR"

    def test_action_override_completar_accepted(self):
        """FinalizarRequest accepts action_override=COMPLETAR."""
        req = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="COMPLETAR"
        )
        assert req.action_override == "COMPLETAR"

    def test_action_override_invalid_rejected(self):
        """FinalizarRequest rejects invalid action_override values."""
        with pytest.raises(ValidationError):
            FinalizarRequest(
                tag_spool="TEST-SPOOL",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                selected_unions=[],
                action_override="INVALID"
            )

    def test_action_override_lowercase_rejected(self):
        """FinalizarRequest rejects lowercase action_override."""
        with pytest.raises(ValidationError):
            FinalizarRequest(
                tag_spool="TEST-SPOOL",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                selected_unions=[],
                action_override="pausar"
            )


# ============================================================================
# BEHAVIOR TESTS: action_override=PAUSAR
# ============================================================================

class TestFinalizarActionOverridePausar:
    """Tests for action_override=PAUSAR behavior."""

    @pytest.mark.asyncio
    async def test_pausar_override_skips_union_writes(
        self, occupation_service, mock_union_repo
    ):
        """action_override=PAUSAR does not write to Uniones sheet."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="PAUSAR"
        )

        result = await occupation_service.finalizar_spool(request)

        # No union batch writes
        mock_union_repo.batch_update_arm_full.assert_not_called()
        mock_union_repo.batch_update_sold_full.assert_not_called()

    @pytest.mark.asyncio
    async def test_pausar_override_clears_occupation(
        self, occupation_service, mock_sheets_repo
    ):
        """action_override=PAUSAR clears Ocupado_Por and Fecha_Ocupacion."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="PAUSAR"
        )

        result = await occupation_service.finalizar_spool(request)

        # Should call batch_update_by_column_name to clear occupation
        mock_sheets_repo.batch_update_by_column_name.assert_called()

        # Verify that Ocupado_Por is cleared
        call_args = mock_sheets_repo.batch_update_by_column_name.call_args
        updates = call_args[1]["updates"] if "updates" in call_args[1] else call_args[0][1]
        cleared_fields = {u["column_name"]: u["value"] for u in updates}
        assert cleared_fields.get("Ocupado_Por") == ""
        assert cleared_fields.get("Fecha_Ocupacion") == ""

    @pytest.mark.asyncio
    async def test_pausar_override_updates_estado_detalle(
        self, occupation_service, mock_sheets_repo
    ):
        """action_override=PAUSAR updates Estado_Detalle to paused state."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="PAUSAR"
        )

        result = await occupation_service.finalizar_spool(request)

        call_args = mock_sheets_repo.batch_update_by_column_name.call_args
        updates = call_args[1]["updates"] if "updates" in call_args[1] else call_args[0][1]
        cleared_fields = {u["column_name"]: u["value"] for u in updates}
        # Estado_Detalle should be set to some paused state
        assert "Estado_Detalle" in cleared_fields
        estado = cleared_fields["Estado_Detalle"]
        assert "ARM" in estado or "pausado" in estado or "parcial" in estado

    @pytest.mark.asyncio
    async def test_pausar_override_returns_pausar_action(
        self, occupation_service
    ):
        """action_override=PAUSAR returns action_taken=PAUSAR."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="PAUSAR"
        )

        result = await occupation_service.finalizar_spool(request)

        assert result.success is True
        assert result.action_taken == "PAUSAR"


# ============================================================================
# BEHAVIOR TESTS: action_override=COMPLETAR
# ============================================================================

class TestFinalizarActionOverrideCompletar:
    """Tests for action_override=COMPLETAR behavior."""

    @pytest.mark.asyncio
    async def test_completar_override_auto_selects_all_disponibles(
        self, occupation_service, mock_union_repo
    ):
        """action_override=COMPLETAR auto-selects all disponibles (5 unions)."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],  # Empty — backend fills from disponibles
            action_override="COMPLETAR"
        )

        result = await occupation_service.finalizar_spool(request)

        # Should have called batch_update_arm_full with all 5 union IDs
        mock_union_repo.batch_update_arm_full.assert_called_once()
        call_args = mock_union_repo.batch_update_arm_full.call_args
        union_ids = call_args[1]["union_ids"] if "union_ids" in call_args[1] else call_args[0][1]
        assert len(union_ids) == 5

    @pytest.mark.asyncio
    async def test_completar_override_returns_completar_action(
        self, occupation_service
    ):
        """action_override=COMPLETAR returns action_taken=COMPLETAR."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="COMPLETAR"
        )

        result = await occupation_service.finalizar_spool(request)

        assert result.success is True
        assert result.action_taken == "COMPLETAR"

    @pytest.mark.asyncio
    async def test_completar_override_with_zero_disponibles_does_not_crash(
        self, occupation_service, mock_union_repo
    ):
        """action_override=COMPLETAR with 0 disponibles completes without crashing."""
        # Override to return 0 disponibles
        mock_union_repo.get_disponibles_arm_by_ot = MagicMock(return_value=[])
        mock_union_repo.batch_update_arm_full = MagicMock(return_value=0)
        mock_union_repo.get_by_ids = MagicMock(return_value=[])

        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="COMPLETAR"
        )

        result = await occupation_service.finalizar_spool(request)

        # Should succeed (not crash), return COMPLETAR
        assert result.success is True
        assert result.action_taken == "COMPLETAR"

    @pytest.mark.asyncio
    async def test_completar_override_does_not_trigger_cancellation(
        self, occupation_service, mock_union_repo
    ):
        """action_override=COMPLETAR with empty selected_unions must NOT go through cancellation path."""
        mock_union_repo.get_disponibles_arm_by_ot = MagicMock(return_value=[])
        mock_union_repo.batch_update_arm_full = MagicMock(return_value=0)
        mock_union_repo.get_by_ids = MagicMock(return_value=[])

        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=[],
            action_override="COMPLETAR"
        )

        result = await occupation_service.finalizar_spool(request)

        # Should NOT be CANCELADO
        assert result.action_taken != "CANCELADO"


# ============================================================================
# BEHAVIOR TESTS: action_override=None (backward compat)
# ============================================================================

class TestFinalizarActionOverrideNone:
    """Tests that action_override=None preserves existing auto-determination."""

    @pytest.mark.asyncio
    async def test_no_override_uses_auto_determination_pausar(
        self, occupation_service, mock_union_repo
    ):
        """action_override=None with partial selection auto-determines PAUSAR."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=["OT-100+1", "OT-100+2"],  # 2 of 5 = PAUSAR
            action_override=None
        )

        result = await occupation_service.finalizar_spool(request)

        assert result.action_taken == "PAUSAR"

    @pytest.mark.asyncio
    async def test_no_override_uses_auto_determination_completar(
        self, occupation_service, mock_union_repo
    ):
        """action_override=None with all selected auto-determines COMPLETAR."""
        request = FinalizarRequest(
            tag_spool="TEST-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=["OT-100+1", "OT-100+2", "OT-100+3", "OT-100+4", "OT-100+5"],  # all 5 = COMPLETAR
            action_override=None
        )

        result = await occupation_service.finalizar_spool(request)

        assert result.action_taken == "COMPLETAR"
