from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, TypeAlias

Point: TypeAlias = tuple[float, float]


class SolverError(RuntimeError):
    """Base class for controlled run termination."""


class BudgetExceeded(SolverError):
    pass


class CommunicationFailure(SolverError):
    pass


class ProtocolFailure(SolverError):
    pass


class ModelContradiction(SolverError):
    pass


class RegionType(str, Enum):
    EMPTY = "EMPTY"
    UNBOUNDED = "UNBOUNDED"
    POINT = "POINT"
    SEGMENT = "SEGMENT"
    POLYGON = "POLYGON"
    NUMERIC_UNCERTAIN = "NUMERIC_UNCERTAIN"


class ChannelStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    CLEARED = "CLEARED"
    EXCLUDED = "EXCLUDED"
    ERROR = "ERROR"


class Termination(str, Enum):
    COMPLETED = "COMPLETED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    COMMUNICATION_ERROR = "COMMUNICATION_ERROR"
    MODEL_CONTRADICTION = "MODEL_CONTRADICTION"


@dataclass(frozen=True)
class MeasureObservation:
    result: str
    svd_deg: float | None
    virtual_time_s: float


@dataclass(frozen=True)
class ClearObservation:
    result: str
    virtual_time_s: float


class ObservationClient(Protocol):
    position: Point
    current_channel: int
    virtual_time_s: float
    time_breakdown: dict[str, float]
    action_log: list[dict[str, Any]]

    def enter(self) -> dict[str, Any]: ...
    def measure(self, position: Point, channel: int) -> MeasureObservation: ...
    def clear(self, position: Point, channel: int) -> ClearObservation: ...
    def exit(self) -> dict[str, Any]: ...
    @property
    def has_pending_action(self) -> bool: ...


@dataclass
class ChannelRecord:
    channel: int
    status: ChannelStatus = ChannelStatus.UNKNOWN
    no_signal_site_ids: set[int] = field(default_factory=set)
    first_bearing: tuple[Point, float] | None = None
    bearing_history: list[tuple[Point, float]] = field(default_factory=list)
    polygon: list[Point] = field(default_factory=list)
    failed_clear_centers: list[Point] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "status": self.status.value,
            "no_signal_site_ids": sorted(self.no_signal_site_ids),
            "first_bearing": self.first_bearing,
            "bearing_history": self.bearing_history,
            "polygon": self.polygon,
            "failed_clear_centers": self.failed_clear_centers,
        }


@dataclass
class RunResult:
    termination: Termination
    cleared_count: int
    excluded_count: int
    virtual_time_s: float
    actions: int
    message: str
    channels: list[ChannelRecord]
    time_breakdown: dict[str, float]
    program_runtime_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "termination": self.termination.value,
            "cleared_count": self.cleared_count,
            "excluded_count": self.excluded_count,
            "virtual_time_s": self.virtual_time_s,
            "actions": self.actions,
            "message": self.message,
            "time_breakdown": self.time_breakdown,
            "program_runtime_s": self.program_runtime_s,
            "channels": [c.public_dict() for c in self.channels],
        }
