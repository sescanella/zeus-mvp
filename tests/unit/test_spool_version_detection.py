"""
Unit tests for v4.0 spool version detection via total_uniones field.

Tests that backend correctly parses and includes total_uniones field from
Google Sheets column 68, enabling frontend to detect v3.0 vs v4.0 workflows
without additional API calls.

Note: These tests focus on the Pydantic model only. Integration tests with
SpoolServiceV2.parse_spool_row() require full Google Sheets setup and are
tested separately.
"""
import pytest
from backend.models.spool import Spool
from backend.models.enums import ActionStatus


class TestSpoolModelV4:
    """Test Spool model with v4.0 fields."""

    def test_spool_model_accepts_total_uniones(self):
        """Test that Spool model accepts total_uniones field."""
        spool = Spool(
            tag_spool='TEST-SPOOL',
            ot='123',
            nv='NV-001',
            total_uniones=12,
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        assert spool.total_uniones == 12

    def test_spool_model_total_uniones_optional(self):
        """Test that total_uniones is optional (defaults to None)."""
        spool = Spool(
            tag_spool='TEST-SPOOL-2',
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        assert spool.total_uniones is None

    def test_spool_model_validates_non_negative_total_uniones(self):
        """Test that Pydantic validates total_uniones >= 0."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            Spool(
                tag_spool='TEST-SPOOL-3',
                total_uniones=-5,  # Invalid: negative
                arm=ActionStatus.PENDIENTE,
                sold=ActionStatus.PENDIENTE
            )

    def test_spool_model_total_uniones_zero_is_valid(self):
        """Test that total_uniones = 0 is valid (v3.0 spools)."""
        spool = Spool(
            tag_spool='V3-SPOOL',
            total_uniones=0,
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        assert spool.total_uniones == 0


class TestFrontendVersionDetection:
    """Unit tests simulating frontend version detection logic."""

    def test_detect_v4_spool_from_total_uniones(self):
        """Simulate frontend logic: total_uniones > 0 => v4.0."""
        spool = Spool(
            tag_spool='TEST-V4',
            total_uniones=12,
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        # Frontend logic: (spool.total_uniones && spool.total_uniones > 0) ? 'v4.0' : 'v3.0'
        version = 'v4.0' if (spool.total_uniones and spool.total_uniones > 0) else 'v3.0'

        assert version == 'v4.0'

    def test_detect_v3_spool_from_zero_unions(self):
        """Simulate frontend logic: total_uniones = 0 => v3.0."""
        spool = Spool(
            tag_spool='TEST-V3',
            total_uniones=0,
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        version = 'v4.0' if (spool.total_uniones and spool.total_uniones > 0) else 'v3.0'

        assert version == 'v3.0'

    def test_detect_v3_spool_from_none_unions(self):
        """Simulate frontend logic: total_uniones = None => v3.0."""
        spool = Spool(
            tag_spool='TEST-V3-LEGACY',
            total_uniones=None,
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        version = 'v4.0' if (spool.total_uniones and spool.total_uniones > 0) else 'v3.0'

        assert version == 'v3.0'
