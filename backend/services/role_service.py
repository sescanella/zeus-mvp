"""
Servicio de gestión de roles operativos (v2.0).

Responsabilidades:
- Validar que trabajador tenga rol necesario para operación
- Obtener roles de trabajador
- Combinar Worker con sus roles
- Verificar permisos operacionales
"""
from typing import List
import logging

from backend.models.role import WorkerRole, RolTrabajador, WorkerWithRoles
from backend.models.worker import Worker
from backend.repositories.role_repository import RoleRepository
from backend.exceptions import RolNoAutorizadoError

logger = logging.getLogger(__name__)


class RoleService:
    """
    Servicio de gestión de roles operativos.

    Integra con RoleRepository para validar permisos de trabajadores.
    Usado por ValidationService antes de permitir INICIAR operaciones.

    Mapeo operacion → rol requerido:
    - "ARM" → requiere RolTrabajador.ARMADOR
    - "SOLD" → requiere RolTrabajador.SOLDADOR
    - "METROLOGIA" → requiere RolTrabajador.METROLOGIA
    """

    def __init__(self, role_repository: RoleRepository):
        """
        Inicializa servicio con repositorio de roles.

        Args:
            role_repository: Repositorio para acceso a hoja "Roles"
        """
        self.role_repository = role_repository
        logger.info("✅ RoleService inicializado")

    def validar_worker_tiene_rol_para_operacion(
        self,
        worker_id: int,
        operacion: str
    ) -> None:
        """
        Valida que un trabajador tenga el rol necesario para realizar una operación.

        Este método se llama ANTES de permitir INICIAR una operación.
        Si el trabajador no tiene el rol requerido, lanza RolNoAutorizadoError.

        Mapeo operacion → rol requerido:
        - "ARM" → requiere RolTrabajador.ARMADOR
        - "SOLD" → requiere RolTrabajador.SOLDADOR
        - "METROLOGIA" → requiere RolTrabajador.METROLOGIA

        Args:
            worker_id: ID del trabajador
            operacion: Código de operación ("ARM", "SOLD", "METROLOGIA")

        Raises:
            ValueError: Si operación no reconocida
            RolNoAutorizadoError: Si trabajador no tiene el rol necesario

        Examples:
            >>> # Worker 93 tiene roles [ARMADOR, SOLDADOR]
            >>> service.validar_worker_tiene_rol_para_operacion(93, "ARM")
            # OK - no lanza excepción

            >>> # Worker 95 tiene roles [SOLDADOR, METROLOGIA]
            >>> service.validar_worker_tiene_rol_para_operacion(95, "ARM")
            # Lanza RolNoAutorizadoError: "Trabajador 95 no tiene rol 'Armador'..."
        """
        # Mapeo operacion → rol requerido
        operacion_to_rol = {
            "ARM": RolTrabajador.ARMADOR,
            "SOLD": RolTrabajador.SOLDADOR,
            "METROLOGIA": RolTrabajador.METROLOGIA,
        }

        operacion_upper = operacion.upper()
        rol_requerido = operacion_to_rol.get(operacion_upper)

        if not rol_requerido:
            raise ValueError(
                f"Operación '{operacion}' no reconocida. "
                f"Operaciones válidas: {list(operacion_to_rol.keys())}"
            )

        # Verificar si trabajador tiene el rol requerido
        tiene_rol = self.role_repository.worker_has_role(worker_id, rol_requerido)

        if not tiene_rol:
            # Obtener roles actuales para mensaje más informativo
            roles_actuales = self.obtener_roles_worker(worker_id)
            roles_str = [rol.value for rol in roles_actuales]

            raise RolNoAutorizadoError(
                worker_id=worker_id,
                operacion=operacion,
                rol_requerido=rol_requerido.value,
                roles_actuales=roles_str if roles_str else None
            )

        logger.info(
            f"✅ Worker {worker_id} autorizado para {operacion} "
            f"(rol: {rol_requerido.value})"
        )

    def obtener_roles_worker(self, worker_id: int) -> List[RolTrabajador]:
        """
        Obtiene lista de roles activos de un trabajador.

        Retorna solo los enum RolTrabajador, sin metadata adicional.

        Args:
            worker_id: ID del trabajador

        Returns:
            Lista de RolTrabajador (enums)
            Lista vacía si trabajador no tiene roles activos

        Examples:
            >>> service.obtener_roles_worker(93)
            [RolTrabajador.ARMADOR, RolTrabajador.SOLDADOR]

            >>> service.obtener_roles_worker(999)  # Worker sin roles
            []
        """
        return self.role_repository.get_worker_roles_as_enum(worker_id)

    def obtener_worker_con_roles(
        self,
        worker: Worker
    ) -> WorkerWithRoles:
        """
        Combina datos de Worker con sus roles activos.

        Útil para frontend P2 (mostrar operaciones permitidas según roles).

        Args:
            worker: Objeto Worker (de hoja Trabajadores)

        Returns:
            WorkerWithRoles: Worker + lista de roles activos

        Examples:
            >>> worker = Worker(id=93, nombre="Mauricio", apellido="Rodriguez", activo=True)
            >>> worker_con_roles = service.obtener_worker_con_roles(worker)
            >>> worker_con_roles.roles
            [RolTrabajador.ARMADOR, RolTrabajador.SOLDADOR]
            >>> worker_con_roles.puede_hacer_operacion("ARM")
            True
            >>> worker_con_roles.puede_hacer_operacion("METROLOGIA")
            False
        """
        roles = self.obtener_roles_worker(worker.id)

        worker_con_roles = WorkerWithRoles(
            id=worker.id,
            nombre=worker.nombre,
            apellido=worker.apellido,
            activo=worker.activo,
            roles=roles
        )

        logger.debug(
            f"Worker {worker.id} ({worker.nombre_completo}): "
            f"{len(roles)} roles activos"
        )

        return worker_con_roles

    def worker_puede_hacer_operacion(
        self,
        worker_id: int,
        operacion: str
    ) -> bool:
        """
        Verifica si un trabajador PUEDE hacer una operación (sin lanzar excepción).

        Método helper para frontend: validar antes de mostrar botones.

        Args:
            worker_id: ID del trabajador
            operacion: Código de operación ("ARM", "SOLD", "METROLOGIA")

        Returns:
            bool: True si tiene el rol necesario, False si no

        Examples:
            >>> service.worker_puede_hacer_operacion(93, "ARM")  # Tiene rol ARMADOR
            True
            >>> service.worker_puede_hacer_operacion(93, "METROLOGIA")  # No tiene rol METROLOGIA
            False
        """
        operacion_to_rol = {
            "ARM": RolTrabajador.ARMADOR,
            "SOLD": RolTrabajador.SOLDADOR,
            "METROLOGIA": RolTrabajador.METROLOGIA,
        }

        rol_requerido = operacion_to_rol.get(operacion.upper())
        if not rol_requerido:
            return False

        return self.role_repository.worker_has_role(worker_id, rol_requerido)
