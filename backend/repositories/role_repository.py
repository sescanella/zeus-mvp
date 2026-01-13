"""
Repositorio para acceso a hoja "Roles" en Google Sheets (v2.0).

Maneja lectura de roles operativos de trabajadores (multi-rol support).
Estructura Sheets: A=Id | B=Rol | C=Activo
"""
import gspread
from typing import List
import logging

from backend.models.role import WorkerRole, RolTrabajador
from backend.exceptions import SheetsConnectionError

logger = logging.getLogger(__name__)


class RoleRepository:
    """
    Acceso a hoja "Roles" en Google Sheets.

    Operaciones:
    - get_roles_by_worker_id: Obtener todos los roles activos de un trabajador
    - get_all_roles: Obtener todos los roles (para admin)
    - worker_has_role: Verificar si trabajador tiene rol específico
    - get_worker_roles_as_enum: Obtener solo los enum RolTrabajador activos

    Estructura esperada en Sheets:
    | A (Id) | B (Rol)        | C (Activo) |
    |--------|----------------|------------|
    | 93     | Armador        | TRUE       |
    | 93     | Soldador       | TRUE       | ← Multi-rol
    | 94     | Armador        | TRUE       |
    | 95     | Soldador       | TRUE       |
    | 95     | Metrologia     | TRUE       | ← Multi-rol
    """

    # Índices de columnas (0-indexed)
    IDX_ID = 0       # A - Id del trabajador
    IDX_ROL = 1      # B - Rol (string)
    IDX_ACTIVO = 2   # C - Activo (TRUE/FALSE)

    def __init__(self, spreadsheet: gspread.Spreadsheet, hoja_nombre: str = "Roles"):
        """
        Inicializa repositorio con conexión a hoja "Roles".

        IMPORTANT: Usa lazy loading para evitar llamadas API innecesarias.
        El worksheet solo se obtiene cuando se usa por primera vez.

        Args:
            spreadsheet: Instancia de Google Spreadsheet autenticada
            hoja_nombre: Nombre de la hoja (default: "Roles")
        """
        self.spreadsheet = spreadsheet
        self.hoja_nombre = hoja_nombre
        self._worksheet = None  # Lazy loading
        logger.info(f"✅ RoleRepository inicializado (lazy): hoja '{hoja_nombre}'")

    def _get_worksheet(self) -> gspread.Worksheet:
        """
        Obtiene el worksheet usando lazy loading (solo la primera vez).

        Returns:
            gspread.Worksheet de la hoja "Roles"

        Raises:
            SheetsConnectionError: Si la hoja no existe
        """
        if self._worksheet is None:
            try:
                self._worksheet = self.spreadsheet.worksheet(self.hoja_nombre)
                logger.debug(f"Worksheet '{self.hoja_nombre}' cargado (lazy)")
            except gspread.exceptions.WorksheetNotFound:
                raise SheetsConnectionError(
                    f"Hoja '{self.hoja_nombre}' no encontrada en Google Sheets",
                    details="Verificar que la hoja 'Roles' existe en el spreadsheet"
                )
        return self._worksheet

    def get_roles_by_worker_id(self, worker_id: int) -> List[WorkerRole]:
        """
        Obtiene todos los roles activos de un trabajador.

        Args:
            worker_id: ID del trabajador (columna A de Roles)

        Returns:
            Lista de WorkerRole (solo roles con activo=True)
            Lista vacía si el trabajador no tiene roles activos

        Examples:
            >>> repo.get_roles_by_worker_id(93)
            [
                WorkerRole(id=93, rol=RolTrabajador.ARMADOR, activo=True),
                WorkerRole(id=93, rol=RolTrabajador.SOLDADOR, activo=True)
            ]

            >>> repo.get_roles_by_worker_id(999)  # Worker sin roles
            []
        """
        try:
            # Obtener todas las filas (skip header row)
            all_rows = self._get_worksheet().get_all_values()[1:]
        except gspread.exceptions.APIError as e:
            logger.error(f"Error al leer hoja Roles: {str(e)}")
            raise SheetsConnectionError(
                "Error al acceder a hoja Roles",
                details=str(e)
            )

        roles = []
        for row_idx, row in enumerate(all_rows, start=2):  # start=2 porque row 1 es header
            if len(row) < 3:
                logger.debug(f"Fila {row_idx} incompleta, saltando: {row}")
                continue  # Skip filas incompletas

            # Parsear Id
            try:
                row_id = int(row[self.IDX_ID])
            except (ValueError, IndexError):
                logger.warning(f"Fila {row_idx} con Id inválido, saltando: {row}")
                continue

            # Solo procesar filas del worker_id solicitado
            if row_id != worker_id:
                continue

            # Parsear rol
            rol_str = row[self.IDX_ROL].strip()
            try:
                rol = RolTrabajador(rol_str)
            except ValueError:
                logger.warning(f"Rol inválido '{rol_str}' para worker {worker_id} (fila {row_idx}), saltando")
                continue

            # Parsear activo
            activo_str = row[self.IDX_ACTIVO].strip().upper()
            activo = activo_str == "TRUE"

            # Solo retornar roles activos
            if activo:
                roles.append(WorkerRole(
                    id=row_id,
                    rol=rol,
                    activo=activo
                ))

        logger.debug(f"Worker {worker_id}: {len(roles)} roles activos encontrados")
        return roles

    def get_worker_roles_as_enum(self, worker_id: int) -> List[RolTrabajador]:
        """
        Obtiene solo los enum RolTrabajador activos de un trabajador.

        Método helper conveniente para validaciones rápidas.

        Args:
            worker_id: ID del trabajador

        Returns:
            Lista de RolTrabajador (solo enums, sin metadata)

        Examples:
            >>> repo.get_worker_roles_as_enum(93)
            [RolTrabajador.ARMADOR, RolTrabajador.SOLDADOR]

            >>> repo.get_worker_roles_as_enum(999)  # Worker sin roles
            []
        """
        roles = self.get_roles_by_worker_id(worker_id)
        return [role.rol for role in roles]

    def worker_has_role(self, worker_id: int, rol: RolTrabajador) -> bool:
        """
        Verifica si un trabajador tiene un rol específico activo.

        Args:
            worker_id: ID del trabajador
            rol: Rol a verificar (enum RolTrabajador)

        Returns:
            bool: True si el trabajador tiene ese rol activo, False si no

        Examples:
            >>> repo.worker_has_role(93, RolTrabajador.ARMADOR)
            True
            >>> repo.worker_has_role(93, RolTrabajador.METROLOGIA)
            False
        """
        roles_enum = self.get_worker_roles_as_enum(worker_id)
        return rol in roles_enum

    def get_all_roles(self) -> List[WorkerRole]:
        """
        Obtiene TODOS los roles (activos e inactivos).

        Útil para panel de administración o reportes.

        Returns:
            Lista completa de WorkerRole (incluye roles inactivos)

        Examples:
            >>> repo.get_all_roles()
            [
                WorkerRole(id=93, rol=RolTrabajador.ARMADOR, activo=True),
                WorkerRole(id=93, rol=RolTrabajador.SOLDADOR, activo=True),
                WorkerRole(id=97, rol=RolTrabajador.REVESTIMIENTO, activo=False),  # Inactivo
                ...
            ]
        """
        try:
            all_rows = self._get_worksheet().get_all_values()[1:]  # Skip header
        except gspread.exceptions.APIError as e:
            logger.error(f"Error al leer hoja Roles: {str(e)}")
            raise SheetsConnectionError(
                "Error al acceder a hoja Roles",
                details=str(e)
            )

        roles = []
        for row_idx, row in enumerate(all_rows, start=2):
            if len(row) < 3:
                continue

            try:
                row_id = int(row[self.IDX_ID])
                rol = RolTrabajador(row[self.IDX_ROL].strip())
                activo = row[self.IDX_ACTIVO].strip().upper() == "TRUE"

                roles.append(WorkerRole(
                    id=row_id,
                    rol=rol,
                    activo=activo
                ))
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parseando fila {row_idx}: {str(e)}, saltando")
                continue

        logger.info(f"get_all_roles: {len(roles)} roles totales encontrados")
        return roles
