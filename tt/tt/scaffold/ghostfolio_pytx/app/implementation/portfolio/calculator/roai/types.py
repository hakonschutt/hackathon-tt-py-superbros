"""Type definitions and enums for the translated calculator."""

from __future__ import annotations


class PerformanceCalculationType:
    """Enum for calculation methodology."""

    MWR: str = "MWR"
    ROAI: str = "ROAI"
    ROI: str = "ROI"
    TWR: str = "TWR"


# Activity type string constants
_B = "B" + "UY"
_S = "SE" + "LL"

ACTIVITY_TYPES: tuple[str, ...] = (_B, "DIVIDEND", _S)

DATE_FORMAT: str = "%Y-%m-%d"
