"""
Configuración compartida de pytest para todos los tests.

Este módulo proporciona fixtures reutilizables para:
- Mock de column_map (mapeo dinámico de columnas)
- Mock de SheetsService con column_map
- Mock de ColumnMapCache
- Limpieza de cache entre tests
"""
import pytest
from backend.services.sheets_service import SheetsService
from backend.core.column_map_cache import ColumnMapCache


@pytest.fixture
def mock_column_map_operaciones():
    """
    Fixture que retorna un column_map mockeado para la hoja Operaciones.

    Usa los índices CORRECTOS (actuales en producción):
    - TAG_SPOOL: 6 (columna G)
    - NV: 1 (columna B)
    - Fecha_Materiales: 32 (columna AG)
    - Fecha_Armado: 33 (columna AH)
    - Armador: 34 (columna AI)
    - Fecha_Soldadura: 35 (columna AJ)
    - Soldador: 36 (columna AK)

    Returns:
        dict[str, int]: Mapeo normalizado {nombre_columna: índice}
    """
    return {
        "tagspool": 6,
        "codigobarra": 6,  # Alternativa
        "nv": 1,
        "fechamateriales": 32,
        "fechaarmado": 33,
        "armador": 34,
        "fechasoldadura": 35,
        "soldador": 36,
        "fechaqcmetrologia": 37,
        # v3.0 columns (positions 64-66 per 01-01 plan)
        "ocupadopor": 64,
        "fechaocupacion": 65,
        "version": 66,
    }


@pytest.fixture
def mock_column_map_trabajadores():
    """
    Fixture que retorna un column_map mockeado para la hoja Trabajadores.

    La estructura de Trabajadores es estable:
    - Id: 0 (columna A)
    - Nombre: 1 (columna B)
    - Apellido: 2 (columna C)
    - Rol: 3 (columna D)
    - Activo: 4 (columna E)

    Returns:
        dict[str, int]: Mapeo normalizado {nombre_columna: índice}
    """
    return {
        "id": 0,
        "nombre": 1,
        "apellido": 2,
        "rol": 3,
        "activo": 4,
    }


@pytest.fixture
def sheets_service_with_mock_map(mock_column_map_operaciones):
    """
    Fixture que retorna una instancia de SheetsService con column_map mockeado.

    Útil para tests que necesitan parsear filas sin acceder a Google Sheets real.

    Args:
        mock_column_map_operaciones: Fixture de column_map mockeado

    Returns:
        SheetsService: Instancia configurada con column_map de prueba

    Example:
        def test_parse_spool(sheets_service_with_mock_map):
            row = [''] * 65
            row[6] = "TEST-SPOOL"
            spool = sheets_service_with_mock_map.parse_spool_row(row)
            assert spool.tag_spool == "TEST-SPOOL"
    """
    return SheetsService(column_map=mock_column_map_operaciones)


@pytest.fixture(autouse=True)
def clear_column_map_cache():
    """
    Fixture que limpia el cache de ColumnMapCache antes de cada test.

    autouse=True: Se ejecuta automáticamente antes de cada test.

    Esto asegura aislamiento entre tests y evita efectos secundarios
    del cache compartido.

    Yields:
        None: Ejecuta test y luego limpia cache
    """
    # Setup: Limpiar cache antes del test
    ColumnMapCache.clear_all()

    # Ejecutar test
    yield

    # Teardown: Limpiar cache después del test
    ColumnMapCache.clear_all()


@pytest.fixture
def mock_column_map_cache(monkeypatch, mock_column_map_operaciones):
    """
    Fixture que mockea ColumnMapCache.get_or_build() para retornar column_map de prueba.

    Útil para tests que usan servicios que dependen de ColumnMapCache pero
    no quieren acceder a Google Sheets real.

    Args:
        monkeypatch: Fixture de pytest para monkeypatching
        mock_column_map_operaciones: Fixture de column_map mockeado

    Returns:
        dict[str, int]: El column_map mockeado que será retornado por get_or_build()

    Example:
        def test_spool_service(mock_column_map_cache):
            # SpoolServiceV2.__init__ llamará a ColumnMapCache.get_or_build()
            # y recibirá mock_column_map_operaciones
            service = SpoolServiceV2(sheets_repository=mock_repo)
            ...
    """
    def mock_get_or_build(sheet_name, sheets_repository):
        return mock_column_map_operaciones

    monkeypatch.setattr(
        ColumnMapCache,
        "get_or_build",
        mock_get_or_build
    )

    return mock_column_map_operaciones
