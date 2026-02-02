"""
Pydantic models for version detection responses.

Models for v3.0 vs v4.0 spool version detection API.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal


class VersionInfo(BaseModel):
    """
    Version information for a spool.

    Contains version detection result with union count and explanation.
    """
    version: Literal["v3.0", "v4.0"] = Field(
        ...,
        description="Detected spool version"
    )
    union_count: int = Field(
        ...,
        description="Value from Total_Uniones column (68)",
        ge=0  # Must be >= 0
    )
    detection_logic: str = Field(
        ...,
        description="Explanation of how version was detected",
        examples=[
            "Total_Uniones=8 -> v4.0",
            "Total_Uniones=0 -> v3.0",
            "Detection failed, defaulting to v3.0: Sheets timeout"
        ]
    )
    tag_spool: str = Field(
        ...,
        description="TAG of the spool",
        min_length=1,
        examples=["TEST-02", "MK-1335-CW-25238-011"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "version": "v4.0",
                    "union_count": 8,
                    "detection_logic": "Total_Uniones=8 -> v4.0",
                    "tag_spool": "TEST-02"
                },
                {
                    "version": "v3.0",
                    "union_count": 0,
                    "detection_logic": "Total_Uniones=0 -> v3.0",
                    "tag_spool": "OLD-SPOOL"
                }
            ]
        }
    )

    @field_validator('union_count')
    @classmethod
    def validate_union_count(cls, v: int) -> int:
        """Validate union count is non-negative."""
        if v < 0:
            raise ValueError("union_count must be >= 0")
        return v


class VersionResponse(BaseModel):
    """
    API response for version detection endpoint.

    Standard success response wrapper.
    """
    success: bool = Field(
        True,
        description="Always True for successful version detection"
    )
    data: VersionInfo = Field(
        ...,
        description="Version detection result"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "data": {
                        "version": "v4.0",
                        "union_count": 8,
                        "detection_logic": "Total_Uniones=8 -> v4.0",
                        "tag_spool": "TEST-02"
                    }
                }
            ]
        }
    )


class VersionMismatchError(BaseModel):
    """
    Error model for version mismatch on v4.0 endpoints.

    Returned as 422 Unprocessable Entity when v3.0 spool
    is used on v4.0-only endpoints.
    """
    error: str = Field(
        default="VERSION_MISMATCH",
        description="Error code for version mismatch"
    )
    message: str = Field(
        ...,
        description="Detailed error message for user",
        examples=[
            "This endpoint requires v4.0 spools with unions. Spool TEST-01 is v3.0",
            "Cannot use v3.0 spool on union-level endpoint. Expected v4.0, got v3.0"
        ]
    )
    expected_version: str = Field(
        ...,
        description="Version required by the endpoint",
        examples=["v4.0"]
    )
    actual_version: str = Field(
        ...,
        description="Actual version of the spool",
        examples=["v3.0", "v4.0"]
    )
    tag_spool: str = Field(
        ...,
        description="TAG of the spool that caused the mismatch",
        min_length=1,
        examples=["TEST-01", "OLD-SPOOL"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "VERSION_MISMATCH",
                    "message": "This endpoint requires v4.0 spools with unions. Spool TEST-01 is v3.0",
                    "expected_version": "v4.0",
                    "actual_version": "v3.0",
                    "tag_spool": "TEST-01"
                }
            ]
        }
    )
