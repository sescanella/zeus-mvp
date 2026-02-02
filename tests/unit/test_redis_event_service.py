"""
Unit tests for RedisEventService.

Tests event publishing to Redis pub/sub channel with various scenarios.
"""
import json
import re
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from backend.services.redis_event_service import RedisEventService


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(return_value=2)  # 2 subscribers
    return mock_client


@pytest.fixture
def event_service(mock_redis_client):
    """Create RedisEventService with mock client."""
    return RedisEventService(mock_redis_client)


class TestRedisEventService:
    """Test suite for RedisEventService."""

    @pytest.mark.asyncio
    async def test_publish_spool_update_tomar_success(
        self, event_service, mock_redis_client
    ):
        """Test publishing TOMAR event successfully."""
        # Arrange
        event_type = "TOMAR"
        tag_spool = "SPOOL-001"
        worker_nombre = "MR(93)"
        estado_detalle = "ARM: En Progreso"
        additional_data = {"operacion": "ARM"}

        # Act
        result = await event_service.publish_spool_update(
            event_type=event_type,
            tag_spool=tag_spool,
            worker_nombre=worker_nombre,
            estado_detalle=estado_detalle,
            additional_data=additional_data
        )

        # Assert
        assert result is True
        mock_redis_client.publish.assert_called_once()

        # Verify published message structure
        call_args = mock_redis_client.publish.call_args
        assert call_args[0][0] == "spools:updates"  # Channel name

        # Parse JSON payload
        message_json = call_args[0][1]
        message = json.loads(message_json)

        assert message["event_type"] == event_type
        assert message["tag_spool"] == tag_spool
        assert message["worker_nombre"] == worker_nombre
        assert message["estado_detalle"] == estado_detalle
        assert message["operacion"] == "ARM"
        assert "timestamp" in message
        # Chile format DD-MM-YYYY HH:MM:SS (America/Santiago)
        assert re.match(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}", message["timestamp"])

    @pytest.mark.asyncio
    async def test_publish_spool_update_pausar_success(
        self, event_service, mock_redis_client
    ):
        """Test publishing PAUSAR event successfully."""
        # Act
        result = await event_service.publish_spool_update(
            event_type="PAUSAR",
            tag_spool="SPOOL-002",
            worker_nombre="JP(94)",
            estado_detalle="ARM: Disponible",
            additional_data={"operacion": "ARM", "razon": "break"}
        )

        # Assert
        assert result is True
        call_args = mock_redis_client.publish.call_args
        message = json.loads(call_args[0][1])
        assert message["event_type"] == "PAUSAR"
        assert message["razon"] == "break"

    @pytest.mark.asyncio
    async def test_publish_spool_update_completar_success(
        self, event_service, mock_redis_client
    ):
        """Test publishing COMPLETAR event successfully."""
        # Act
        result = await event_service.publish_spool_update(
            event_type="COMPLETAR",
            tag_spool="SPOOL-003",
            worker_nombre="MR(93)",
            estado_detalle="ARM: Completado 27-01-2026",
            additional_data={"operacion": "ARM", "fecha": "27-01-2026"}
        )

        # Assert
        assert result is True
        call_args = mock_redis_client.publish.call_args
        message = json.loads(call_args[0][1])
        assert message["event_type"] == "COMPLETAR"
        assert message["fecha"] == "27-01-2026"

    @pytest.mark.asyncio
    async def test_publish_spool_update_state_change_success(
        self, event_service, mock_redis_client
    ):
        """Test publishing STATE_CHANGE event successfully."""
        # Act
        result = await event_service.publish_spool_update(
            event_type="STATE_CHANGE",
            tag_spool="SPOOL-004",
            worker_nombre="JP(94)",
            estado_detalle="SOLD: Disponible (ARM completo)",
            additional_data={"operacion": "SOLD", "can_start": True}
        )

        # Assert
        assert result is True
        call_args = mock_redis_client.publish.call_args
        message = json.loads(call_args[0][1])
        assert message["event_type"] == "STATE_CHANGE"
        assert message["can_start"] is True

    @pytest.mark.asyncio
    async def test_publish_spool_update_without_additional_data(
        self, event_service, mock_redis_client
    ):
        """Test publishing event without additional data."""
        # Act
        result = await event_service.publish_spool_update(
            event_type="TOMAR",
            tag_spool="SPOOL-005",
            worker_nombre="MR(93)",
            estado_detalle="ARM: En Progreso"
        )

        # Assert
        assert result is True
        call_args = mock_redis_client.publish.call_args
        message = json.loads(call_args[0][1])

        # Check only required fields present
        assert message["event_type"] == "TOMAR"
        assert message["tag_spool"] == "SPOOL-005"
        assert message["worker_nombre"] == "MR(93)"
        assert message["estado_detalle"] == "ARM: En Progreso"
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_publish_spool_update_redis_error(
        self, event_service, mock_redis_client
    ):
        """Test handling Redis connection error."""
        # Arrange
        mock_redis_client.publish.side_effect = RedisConnectionError("Connection lost")

        # Act
        result = await event_service.publish_spool_update(
            event_type="TOMAR",
            tag_spool="SPOOL-006",
            worker_nombre="MR(93)",
            estado_detalle="ARM: En Progreso"
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_spool_update_redis_generic_error(
        self, event_service, mock_redis_client
    ):
        """Test handling generic Redis error."""
        # Arrange
        mock_redis_client.publish.side_effect = RedisError("Publish failed")

        # Act
        result = await event_service.publish_spool_update(
            event_type="COMPLETAR",
            tag_spool="SPOOL-007",
            worker_nombre="JP(94)",
            estado_detalle="SOLD: Completado"
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_spool_update_unexpected_error(
        self, event_service, mock_redis_client
    ):
        """Test handling unexpected error during publish."""
        # Arrange
        mock_redis_client.publish.side_effect = ValueError("Invalid data")

        # Act
        result = await event_service.publish_spool_update(
            event_type="PAUSAR",
            tag_spool="SPOOL-008",
            worker_nombre="MR(93)",
            estado_detalle="ARM: Disponible"
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_channel_name_constant(self, event_service):
        """Test channel name is correctly set."""
        assert event_service.channel == "spools:updates"
        assert event_service.CHANNEL == "spools:updates"

    @pytest.mark.asyncio
    async def test_timestamp_format(self, event_service, mock_redis_client):
        """Test timestamp is in Chile format DD-MM-YYYY HH:MM:SS (America/Santiago)."""
        from backend.utils.date_formatter import format_datetime_for_sheets
        fixed_dt = datetime(2026, 1, 27, 15, 30, 45)
        expected_ts = format_datetime_for_sheets(fixed_dt)  # "27-01-2026 15:30:45"

        with patch('backend.services.redis_event_service.now_chile', return_value=fixed_dt):
            await event_service.publish_spool_update(
                event_type="TOMAR",
                tag_spool="SPOOL-009",
                worker_nombre="MR(93)",
                estado_detalle="ARM: En Progreso"
            )

            call_args = mock_redis_client.publish.call_args
            message = json.loads(call_args[0][1])
            assert message["timestamp"] == expected_ts
