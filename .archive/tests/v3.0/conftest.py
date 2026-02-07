"""
v3.0 test fixtures.

Provides fixtures specific to v3.0 features:
- v3.0 column access
- Occupation state validation
- Version token testing
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from backend.services.sheets_service import SheetsService
from backend.core.column_map_cache import ColumnMapCache


@pytest.fixture
def mock_column_map_v3():
    """Mock column map including v3.0 columns (66 columns total)."""
    return {
        "tagspool": 6,
        "fechamateriales": 32,
        "armador": 34,
        "soldador": 36,
        # v3.0 columns at positions 64, 65, 66 (1-indexed) = 63, 64, 65 (0-indexed)
        "ocupadopor": 63,
        "fechaocupacion": 64,
        "version": 65,
    }
