"""
Unit tests for ARMCompletionFilter (v3.0 + v4.0 hybrid).

Tests the hybrid filter that determines if ARM is sufficiently completed
for SOLD INICIAR eligibility:
- v3.0 (Total_Uniones=0): requires Fecha_Armado with data
- v4.0 (Total_Uniones>=1): requires Uniones_ARM_Completadas >= 1
"""
import pytest
from datetime import date

from backend.models.spool import Spool
from backend.services.filters.common_filters import ARMCompletionFilter


def _make_spool(**overrides) -> Spool:
    """Create a minimal Spool with sensible defaults for filter testing."""
    defaults = {
        "tag_spool": "TEST-SPOOL-001",
        "ot": "001",
        "total_uniones": None,
        "uniones_arm_completadas": None,
        "fecha_armado": None,
    }
    defaults.update(overrides)
    return Spool(**defaults)


class TestARMCompletionFilterV30:
    """Tests for v3.0 spools (Total_Uniones = 0 or None)."""

    def setup_method(self):
        self.filter = ARMCompletionFilter()

    def test_v30_with_fecha_armado_passes(self):
        """v3.0 spool with Fecha_Armado set should pass."""
        spool = _make_spool(
            total_uniones=None,
            fecha_armado=date(2026, 1, 15),
        )
        result = self.filter.apply(spool)

        assert result.passed is True
        assert "v3.0" in result.reason
        assert "completado" in result.reason

    def test_v30_without_fecha_armado_fails(self):
        """v3.0 spool without Fecha_Armado should fail."""
        spool = _make_spool(
            total_uniones=None,
            fecha_armado=None,
        )
        result = self.filter.apply(spool)

        assert result.passed is False
        assert "v3.0" in result.reason
        assert "no completado" in result.reason

    def test_v30_total_uniones_zero_with_fecha_armado_passes(self):
        """v3.0 spool with Total_Uniones=0 and Fecha_Armado should pass."""
        spool = _make_spool(
            total_uniones=0,
            fecha_armado=date(2026, 1, 20),
        )
        result = self.filter.apply(spool)

        assert result.passed is True
        assert "v3.0" in result.reason


class TestARMCompletionFilterV40:
    """Tests for v4.0 spools (Total_Uniones >= 1)."""

    def setup_method(self):
        self.filter = ARMCompletionFilter()

    def test_v40_partial_arm_passes(self):
        """v4.0 spool with 6/12 ARM completadas should pass (TEST-02 case)."""
        spool = _make_spool(
            total_uniones=12,
            uniones_arm_completadas=6,
        )
        result = self.filter.apply(spool)

        assert result.passed is True
        assert "v4.0" in result.reason
        assert "6/12" in result.reason

    def test_v40_zero_arm_fails(self):
        """v4.0 spool with 0/12 ARM completadas should fail."""
        spool = _make_spool(
            total_uniones=12,
            uniones_arm_completadas=0,
        )
        result = self.filter.apply(spool)

        assert result.passed is False
        assert "v4.0" in result.reason
        assert "0/12" in result.reason

    def test_v40_all_arm_passes(self):
        """v4.0 spool with 12/12 ARM completadas should pass."""
        spool = _make_spool(
            total_uniones=12,
            uniones_arm_completadas=12,
        )
        result = self.filter.apply(spool)

        assert result.passed is True
        assert "v4.0" in result.reason
        assert "12/12" in result.reason

    def test_v40_none_arm_completadas_treated_as_zero(self):
        """v4.0 spool with uniones_arm_completadas=None should fail (treated as 0)."""
        spool = _make_spool(
            total_uniones=8,
            uniones_arm_completadas=None,
        )
        result = self.filter.apply(spool)

        assert result.passed is False
        assert "v4.0" in result.reason
        assert "0/8" in result.reason

    def test_v40_single_arm_passes(self):
        """v4.0 spool with exactly 1 ARM completada should pass (minimum threshold)."""
        spool = _make_spool(
            total_uniones=5,
            uniones_arm_completadas=1,
        )
        result = self.filter.apply(spool)

        assert result.passed is True
        assert "v4.0" in result.reason
        assert "1/5" in result.reason


class TestARMCompletionFilterProperties:
    """Tests for filter metadata properties."""

    def test_name(self):
        f = ARMCompletionFilter()
        assert f.name == "ARMCompletion_v3_v4_Hybrid"

    def test_description_contains_versions(self):
        f = ARMCompletionFilter()
        desc = f.description
        assert "v3.0" in desc
        assert "v4.0" in desc
        assert "Fecha_Armado" in desc
        assert "Uniones_ARM_Completadas" in desc
