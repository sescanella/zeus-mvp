"""
Modelos Pydantic para Roles Operativos (v2.0).

Implementa sistema de multi-rol donde un trabajador puede tener N roles activos.
Datos persistidos en hoja "Roles" de Google Sheets (3 columnas: Id, Rol, Activo).
"""
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class RolTrabajador(str, Enum):
    """
    Roles operativos disponibles en el sistema (v2.0).

    Relación operación → rol requerido:
    - ARM (Armado) → requiere rol ARMADOR
    - SOLD (Soldado) → requiere rol SOLDADOR
    - METROLOGIA (Inspección) → requiere rol METROLOGIA

    Roles operativos:
    - ARMADOR → puede realizar operación ARM
    - SOLDADOR → puede realizar operación SOLD
    - METROLOGIA → puede realizar operación METROLOGIA
    - AYUDANTE → puede asistir en cualquier operación
    - REVESTIMIENTO → operaciones futuras
    - PINTURA → operaciones futuras
    - DESPACHO → operaciones futuras
    """
    ARMADOR = "Armador"
    SOLDADOR = "Soldador"
    AYUDANTE = "Ayudante"
    METROLOGIA = "Metrologia"
    REVESTIMIENTO = "Revestimiento"
    PINTURA = "Pintura"
    DESPACHO = "Despacho"


class WorkerRole(BaseModel):
    """
    Modelo de un rol asignado a un trabajador.

    Representa una fila en la hoja "Roles" de Google Sheets (columnas A-C).
    Relación 1:N con Worker (un trabajador puede tener múltiples roles).

    Estructura Sheets:
    - Columna A: Id (numérico, FK a Trabajadores.Id, permite duplicados)
    - Columna B: Rol (string, uno de 7 valores RolTrabajador)
    - Columna C: Activo (TRUE | FALSE)

    Ejemplos:
    - Worker ID 93 puede tener rol "Armador" Y rol "Soldador" (2 filas)
    - Worker ID 95 puede tener solo rol "Soldador" (1 fila)
    - Worker ID 97 puede tener rol "Revestimiento" desactivado (Activo=FALSE)
    """
    id: int = Field(
        ...,
        description="ID del trabajador (FK a hoja Trabajadores columna A)",
        gt=0,
        examples=[93, 94, 95]
    )
    rol: RolTrabajador = Field(
        ...,
        description="Rol operativo del trabajador",
        examples=[RolTrabajador.ARMADOR, RolTrabajador.SOLDADOR]
    )
    activo: bool = Field(
        True,
        description="Si el rol está activo para el trabajador"
    )

    model_config = ConfigDict(
        frozen=True,  # Inmutable
        str_strip_whitespace=True,
    )


class WorkerWithRoles(BaseModel):
    """
    Modelo de trabajador con sus roles asignados.

    Combina datos de hojas Trabajadores + Roles.
    Usado para validar permisos de operación en ValidationService y frontend P2.
    """
    id: int = Field(
        ...,
        description="ID único del trabajador",
        gt=0,
        examples=[93, 94, 95]
    )
    nombre: str = Field(
        ...,
        description="Nombre del trabajador",
        min_length=1,
        examples=["Mauricio"]
    )
    apellido: str = Field(
        ...,
        description="Apellido del trabajador",
        min_length=1,
        examples=["Rodriguez"]
    )
    activo: bool = Field(
        True,
        description="Si el trabajador está activo en el sistema"
    )
    roles: list[RolTrabajador] = Field(
        default_factory=list,
        description="Lista de roles activos del trabajador"
    )

    model_config = ConfigDict(
        frozen=True,  # Inmutable
        str_strip_whitespace=True,
    )

    @property
    def nombre_completo(self) -> str:
        """
        Retorna nombre completo del trabajador.

        Returns:
            str: "Nombre Apellido"

        Examples:
            >>> worker = WorkerWithRoles(id=93, nombre="Mauricio", apellido="Rodriguez", activo=True, roles=[RolTrabajador.ARMADOR])
            >>> worker.nombre_completo
            'Mauricio Rodriguez'
        """
        return f"{self.nombre} {self.apellido}"

    def tiene_rol(self, rol: RolTrabajador) -> bool:
        """
        Verifica si el trabajador tiene un rol específico activo.

        Args:
            rol: Rol a verificar (enum RolTrabajador)

        Returns:
            bool: True si el trabajador tiene el rol activo

        Examples:
            >>> worker = WorkerWithRoles(id=93, nombre="Mauricio", apellido="Rodriguez", activo=True, roles=[RolTrabajador.ARMADOR, RolTrabajador.SOLDADOR])
            >>> worker.tiene_rol(RolTrabajador.ARMADOR)
            True
            >>> worker.tiene_rol(RolTrabajador.METROLOGIA)
            False
        """
        return rol in self.roles

    def puede_hacer_operacion(self, operacion: str) -> bool:
        """
        Verifica si el trabajador puede realizar una operación.

        Mapeo operacion → roles requeridos:
        - "ARM" → requiere rol ARMADOR
        - "SOLD" → requiere rol SOLDADOR
        - "METROLOGIA" → requiere rol METROLOGIA

        Args:
            operacion: Código de operación ("ARM", "SOLD", "METROLOGIA")

        Returns:
            bool: True si el trabajador tiene el rol necesario

        Examples:
            >>> worker = WorkerWithRoles(id=93, nombre="Mauricio", apellido="Rodriguez", activo=True, roles=[RolTrabajador.ARMADOR])
            >>> worker.puede_hacer_operacion("ARM")
            True
            >>> worker.puede_hacer_operacion("SOLD")
            False
            >>> worker.puede_hacer_operacion("METROLOGIA")
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

        return self.tiene_rol(rol_requerido)


# Tipo alias para uso en type hints
RolesList = list[RolTrabajador]
