"""
Modelos Pydantic para Uniones (welds individuales en spools).

v4.0: Union-level tracking para métricas de pulgadas-diámetro.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
import uuid


class Union(BaseModel):
    """
    Modelo para una union individual (weld) dentro de un spool.

    Representa una unión con sus timestamps de operaciones ARM/SOLD,
    datos de NDT, y metadata de auditoría.

    Composite PK: {TAG_SPOOL}+{N_UNION}
    Foreign Key: TAG_SPOOL → Operaciones.TAG_SPOOL (columna 7)
    """

    # Identity fields
    id: str = Field(
        ...,
        description="Composite PK: {TAG_SPOOL}+{N_UNION}",
        examples=["OT-123+5", "MK-1335-CW-25238-011+12"]
    )
    ot: str = Field(
        ...,
        description="Work order number - primary foreign key to Operaciones.OT (Column B in Uniones)",
        min_length=1,
        examples=["001", "123", "MK-1335"]
    )
    tag_spool: str = Field(
        ...,
        description="Spool tag - legacy foreign key to Operaciones.TAG_SPOOL (Column O in Uniones)",
        min_length=1,
        examples=["OT-123", "MK-1335-CW-25238-011"]
    )
    n_union: int = Field(
        ...,
        description="Union number within spool (1-20)",
        ge=1,
        le=20
    )
    dn_union: float = Field(
        ...,
        description="Diameter in inches (business metric for pulgadas-diámetro)",
        gt=0
    )
    tipo_union: str = Field(
        ...,
        description="Union type classification",
        min_length=1,
        examples=["Tipo A", "Tipo B", "Tipo C"]
    )

    # ARM operation timestamps
    arm_fecha_inicio: Optional[datetime] = Field(
        None,
        description="ARM start timestamp (when work began on this union)"
    )
    arm_fecha_fin: Optional[datetime] = Field(
        None,
        description="ARM end timestamp (when work completed on this union)"
    )
    arm_worker: Optional[str] = Field(
        None,
        description="Worker who completed ARM in format 'INICIALES(ID)'",
        examples=["MR(93)", "JP(94)"]
    )

    # SOLD operation timestamps
    sol_fecha_inicio: Optional[datetime] = Field(
        None,
        description="SOLD start timestamp (when welding began)"
    )
    sol_fecha_fin: Optional[datetime] = Field(
        None,
        description="SOLD end timestamp (when welding completed)"
    )
    sol_worker: Optional[str] = Field(
        None,
        description="Worker who completed SOLD in format 'INICIALES(ID)'",
        examples=["MG(95)", "CP(96)"]
    )

    # NDT (Non-Destructive Testing) fields
    ndt_fecha: Optional[datetime] = Field(
        None,
        description="NDT inspection date"
    )
    ndt_status: Optional[str] = Field(
        None,
        description="NDT inspection result",
        examples=["APROBADO", "RECHAZADO", "PENDIENTE"]
    )

    # Audit fields (optimistic locking)
    version: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID4 for optimistic locking (prevents concurrent modifications)"
    )

    model_config = ConfigDict(
        frozen=True,  # Immutable - all changes create new versions
        str_strip_whitespace=True,
    )

    @field_validator('arm_worker', 'sol_worker')
    @classmethod
    def validate_worker_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate worker format is 'INICIALES(ID)'.

        Examples: MR(93), JP(94), MG(95)

        Args:
            v: Worker string to validate

        Returns:
            Validated worker string or None

        Raises:
            ValueError: If format is invalid
        """
        if v is None:
            return v

        # Pattern: INICIALES(ID) - e.g., MR(93)
        if not v or '(' not in v or ')' not in v:
            raise ValueError(
                f"Worker format must be 'INICIALES(ID)', got: {v}"
            )

        return v

    @property
    def arm_completada(self) -> bool:
        """
        Check if ARM operation is complete for this union.

        Returns:
            bool: True if arm_fecha_fin is not None
        """
        return self.arm_fecha_fin is not None

    @property
    def sol_completada(self) -> bool:
        """
        Check if SOLD operation is complete for this union.

        Returns:
            bool: True if sol_fecha_fin is not None
        """
        return self.sol_fecha_fin is not None

    @property
    def pulgadas_arm(self) -> float:
        """
        Get pulgadas-diámetro contribution for ARM (if completed).

        Returns:
            float: dn_union if ARM complete, else 0
        """
        return self.dn_union if self.arm_completada else 0

    @property
    def pulgadas_sold(self) -> float:
        """
        Get pulgadas-diámetro contribution for SOLD (if completed).

        Returns:
            float: dn_union if SOLD complete, else 0
        """
        return self.dn_union if self.sol_completada else 0
