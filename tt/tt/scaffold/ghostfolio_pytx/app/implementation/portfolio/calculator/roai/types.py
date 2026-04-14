"""Type definitions and enums for the translated calculator."""
from __future__ import annotations


class PerformanceCalculationType:
    """Enum for performance calculation methodology."""

    MWR = "MWR"
    ROAI = "ROAI"
    ROI = "ROI"
    TWR = "TWR"


INVESTMENT_ACTIVITY_TYPES = ("BUY", "DIVIDEND", "SELL")

DATE_FORMAT = "%Y-%m-%d"
