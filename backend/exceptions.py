"""
Jerarquía de excepciones custom para ZEUES.

Todas las excepciones del sistema heredan de ZEUSException.
"""
from typing import Optional, Any


class ZEUSException(Exception):
    """
    Excepción base para todo el sistema ZEUES.

    Todas las excepciones custom heredan de esta clase.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        data: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.data = data or {}
        super().__init__(self.message)


# ==================== EXCEPCIONES 404 (NOT FOUND) ====================

class SpoolNoEncontradoError(ZEUSException):
    """Spool no existe en la hoja Operaciones (columna G)."""

    def __init__(self, tag_spool: str):
        super().__init__(
            message=f"Spool '{tag_spool}' no encontrado en hoja Operaciones",
            error_code="SPOOL_NO_ENCONTRADO",
            data={"tag_spool": tag_spool}
        )


class WorkerNoEncontradoError(ZEUSException):
    """Trabajador no existe o está inactivo en la hoja Trabajadores."""

    def __init__(self, worker_nombre: str):
        super().__init__(
            message=f"Trabajador '{worker_nombre}' no encontrado o inactivo",
            error_code="WORKER_NO_ENCONTRADO",
            data={"worker_nombre": worker_nombre}
        )


# ==================== EXCEPCIONES 400 (BAD REQUEST) - REGLAS DE NEGOCIO ====================

class OperacionYaIniciadaError(ZEUSException):
    """Operación ya fue iniciada (V/W = 0.1)."""

    def __init__(self, tag_spool: str, operacion: str, trabajador: Optional[str] = None):
        mensaje = f"La operación {operacion} del spool '{tag_spool}' ya está iniciada"
        if trabajador:
            mensaje += f" por {trabajador}"

        super().__init__(
            message=mensaje,
            error_code="OPERACION_YA_INICIADA",
            data={
                "tag_spool": tag_spool,
                "operacion": operacion,
                "trabajador": trabajador
            }
        )


class OperacionYaCompletadaError(ZEUSException):
    """Operación ya fue completada (V/W = 1.0)."""

    def __init__(self, tag_spool: str, operacion: str):
        super().__init__(
            message=(
                f"La operación {operacion} del spool '{tag_spool}' ya fue completada. "
                "Contacta al administrador si necesitas hacer correcciones."
            ),
            error_code="OPERACION_YA_COMPLETADA",
            data={
                "tag_spool": tag_spool,
                "operacion": operacion
            }
        )


class DependenciasNoSatisfechasError(ZEUSException):
    """Dependencias previas no están listas (BA/BB/BD vacías)."""

    def __init__(
        self,
        tag_spool: str,
        operacion: str,
        dependencia_faltante: str,
        detalle: Optional[str] = None
    ):
        mensaje = f"No se puede iniciar {operacion} en spool '{tag_spool}': falta {dependencia_faltante}"
        if detalle:
            mensaje += f" ({detalle})"

        super().__init__(
            message=mensaje,
            error_code="DEPENDENCIAS_NO_SATISFECHAS",
            data={
                "tag_spool": tag_spool,
                "operacion": operacion,
                "dependencia_faltante": dependencia_faltante
            }
        )


class OperacionNoPendienteError(ZEUSException):
    """Operación no está en estado pendiente (V/W != 0)."""

    def __init__(self, tag_spool: str, operacion: str, estado_actual: str):
        super().__init__(
            message=(
                f"No se puede iniciar {operacion} en spool '{tag_spool}': "
                f"la operación no está en estado pendiente (estado actual: {estado_actual})"
            ),
            error_code="OPERACION_NO_PENDIENTE",
            data={
                "tag_spool": tag_spool,
                "operacion": operacion,
                "estado_actual": estado_actual
            }
        )


class OperacionNoIniciadaError(ZEUSException):
    """Operación no está iniciada (V/W != 0.1), no se puede completar."""

    def __init__(self, tag_spool: str, operacion: str):
        super().__init__(
            message=(
                f"No se puede completar {operacion} en spool '{tag_spool}': "
                "la operación no ha sido iniciada"
            ),
            error_code="OPERACION_NO_INICIADA",
            data={
                "tag_spool": tag_spool,
                "operacion": operacion
            }
        )


# ==================== EXCEPCIONES 403 (FORBIDDEN) - AUTORIZACIÓN ====================

class NoAutorizadoError(ZEUSException):
    """
    Solo el trabajador que inició la acción puede completarla.

    CRÍTICA: Implementa la restricción de propiedad (BC/BE).
    """

    def __init__(
        self,
        tag_spool: str,
        trabajador_esperado: str,
        trabajador_solicitante: str,
        operacion: str
    ):
        super().__init__(
            message=(
                f"Solo {trabajador_esperado} puede completar {operacion} en '{tag_spool}' "
                f"(él/ella la inició). Tú eres {trabajador_solicitante}."
            ),
            error_code="NO_AUTORIZADO",
            data={
                "tag_spool": tag_spool,
                "trabajador_esperado": trabajador_esperado,
                "trabajador_solicitante": trabajador_solicitante,
                "operacion": operacion
            }
        )


class RolNoAutorizadoError(ZEUSException):
    """
    Trabajador no tiene el rol necesario para realizar la operación (v2.0).

    Ejemplo: Worker con rol SOLDADOR intenta hacer ARM (requiere ARMADOR).
    """

    def __init__(
        self,
        worker_id: int,
        operacion: str,
        rol_requerido: str,
        roles_actuales: Optional[list[str]] = None
    ):
        mensaje = (
            f"Trabajador {worker_id} no tiene el rol '{rol_requerido}' "
            f"necesario para realizar la operación '{operacion}'"
        )
        if roles_actuales:
            mensaje += f". Roles actuales: {', '.join(roles_actuales)}"

        # Store as instance attributes for easier access
        self.worker_id = worker_id
        self.operacion = operacion
        self.rol_requerido = rol_requerido
        self.roles_actuales = roles_actuales or []

        super().__init__(
            message=mensaje,
            error_code="ROL_NO_AUTORIZADO",
            data={
                "worker_id": worker_id,
                "operacion": operacion,
                "rol_requerido": rol_requerido,
                "roles_actuales": roles_actuales or []
            }
        )


# ==================== EXCEPCIONES 503 (SERVICE UNAVAILABLE) - SERVICIOS EXTERNOS ====================

class SheetsConnectionError(ZEUSException):
    """Error al conectar con Google Sheets API."""

    def __init__(self, message: str, details: Optional[str] = None):
        full_message = f"Error al conectar con Google Sheets: {message}"
        if details:
            full_message += f" | Detalles: {details}"

        super().__init__(
            message=full_message,
            error_code="SHEETS_CONNECTION_ERROR",
            data={"details": details} if details else {}
        )


class SheetsUpdateError(ZEUSException):
    """Error al actualizar datos en Google Sheets."""

    def __init__(self, message: str, updates: Optional[dict] = None):
        super().__init__(
            message=f"Error al actualizar Google Sheets: {message}",
            error_code="SHEETS_UPDATE_ERROR",
            data={"updates": updates} if updates else {}
        )


class SheetsRateLimitError(ZEUSException):
    """Límite de rate de API de Google Sheets excedido."""

    def __init__(self):
        super().__init__(
            message=(
                "Límite de solicitudes a Google Sheets excedido. "
                "Por favor, intenta nuevamente en 1 minuto."
            ),
            error_code="SHEETS_RATE_LIMIT",
            data={"retry_after_seconds": 60}
        )


# ==================== EXCEPCIONES 409 (CONFLICT) - CONCURRENCIA ====================

class SpoolOccupiedError(ZEUSException):
    """
    Spool ya está ocupado por otro trabajador (v3.0).

    Previene race conditions en operaciones TOMAR.
    """

    def __init__(self, tag_spool: str, owner_id: int, owner_name: str):
        super().__init__(
            message=(
                f"El spool '{tag_spool}' ya está ocupado por {owner_name} "
                f"(ID: {owner_id}). Espera a que termine o elige otro spool."
            ),
            error_code="SPOOL_OCCUPIED",
            data={
                "tag_spool": tag_spool,
                "owner_id": owner_id,
                "owner_name": owner_name
            }
        )


class VersionConflictError(ZEUSException):
    """
    Conflicto de versión en operación concurrente (v3.0 optimistic locking).

    Indica que el spool fue modificado por otro proceso entre read y write.
    """

    def __init__(self, expected: str, actual: str, message: str):
        super().__init__(
            message=(
                f"Conflicto de versión: {message}. "
                f"Esperado: {expected}, actual: {actual}. "
                "El spool fue modificado por otro proceso. Intenta nuevamente."
            ),
            error_code="VERSION_CONFLICT",
            data={
                "expected_version": expected,
                "actual_version": actual
            }
        )


class LockExpiredError(ZEUSException):
    """
    Occupation lock expired during operation.

    Note: In single-user mode (v4.0), this exception is rarely triggered
    since there are no distributed locks. Kept for backward compatibility.
    """

    def __init__(self, tag_spool: str):
        super().__init__(
            message=(
                f"El lock del spool '{tag_spool}' expiró durante la operación. "
                "La operación tardó demasiado. Intenta nuevamente."
            ),
            error_code="LOCK_EXPIRED",
            data={"tag_spool": tag_spool}
        )


class SpoolBloqueadoError(ZEUSException):
    """
    Spool bloqueado después de 3 rechazos consecutivos (v3.0 Phase 6).

    Requiere intervención manual del supervisor.
    """

    def __init__(self, tag_spool: str, mensaje: Optional[str] = None):
        default_mensaje = (
            f"El spool '{tag_spool}' está bloqueado después de 3 rechazos consecutivos. "
            "Contactar supervisor para intervención manual."
        )
        super().__init__(
            message=mensaje or default_mensaje,
            error_code="SPOOL_BLOQUEADO",
            data={"tag_spool": tag_spool}
        )


class OperacionNoDisponibleError(ZEUSException):
    """
    Operación no está disponible para este spool (v3.0 Phase 6).

    Ejemplo: Intentar TOMAR reparación pero el spool no está RECHAZADO.
    """

    def __init__(self, tag_spool: str, operacion: str, mensaje: Optional[str] = None):
        default_mensaje = (
            f"La operación {operacion} no está disponible para el spool '{tag_spool}'. "
            f"Verifica el estado actual del spool."
        )
        super().__init__(
            message=mensaje or default_mensaje,
            error_code="OPERACION_NO_DISPONIBLE",
            data={
                "tag_spool": tag_spool,
                "operacion": operacion
            }
        )


class InvalidStateTransitionError(ZEUSException):
    """
    Raised when attempting an invalid state machine transition (v3.0 PAUSAR fix).

    Examples:
    - PAUSAR from pendiente state (nothing to pause)
    - REANUDAR from en_progreso state (already in progress)
    - COMPLETAR from pausado state (need to resume first)
    - TOMAR ARM when already completado (cannot restart)
    """

    def __init__(
        self,
        message: str,
        tag_spool: Optional[str] = None,
        current_state: Optional[str] = None,
        attempted_transition: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="INVALID_STATE_TRANSITION",
            data={
                "tag_spool": tag_spool,
                "current_state": current_state,
                "attempted_transition": attempted_transition
            }
        )


class ArmPrerequisiteError(ZEUSException):
    """
    Raised when SOLD operation is attempted without ARM completion (v4.0 validation).

    Enforces business rule: SOLD operations require at least one union with
    ARM_FECHA_FIN != NULL before starting.

    Args:
        tag_spool: Spool identifier
        message: Custom error message (optional)
        unions_sin_armar: Count of unions without ARM completion
    """

    def __init__(self, tag_spool: str, message: str = None, unions_sin_armar: int = 0):
        default_message = f"Cannot start SOLD: No ARM unions completed for spool '{tag_spool}'"
        super().__init__(
            message=message or default_message,
            error_code="ARM_PREREQUISITE_REQUIRED",
            data={
                "tag_spool": tag_spool,
                "unions_sin_armar": unions_sin_armar
            }
        )
