import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Interval:
    """A closed interval on the number line."""

    min: float
    max: float

    def __post_init__(self):
        if self.min > self.max:
            raise ValueError("Interval min cannot be greater than max.")

    @property
    def length(self) -> float:
        return self.max - self.min

    def contains(self, value: float) -> bool:
        return self.min <= value <= self.max


class Scale(Protocol):
    """Normalizes values to the range 0.0-1.0."""

    def normalize(self, value: float, interval: Interval) -> float: ...


class LinearScale:
    """Linear scale."""

    def normalize(self, value: float, interval: Interval) -> float:
        if interval.length == 0:
            return 0.0
        return (value - interval.min) / interval.length


class LogScale:
    """Logarithmic scale."""

    def __init__(self, base: float = 10.0):
        self.base = base

    def normalize(self, value: float, interval: Interval) -> float:
        if value <= 0 or interval.min <= 0 or interval.max <= 0:
            raise ValueError("LogScale requires positive values.")
        log_min = math.log(interval.min, self.base)
        log_max = math.log(interval.max, self.base)
        log_value = math.log(value, self.base)
        if log_max - log_min == 0:
            return 0.0
        return (log_value - log_min) / (log_max - log_min)


@dataclass(frozen=True)
class Series:
    """Data series."""

    name: str | None

    xs: np.ndarray
    ys: np.ndarray

    def __post_init__(self):
        if len(self.xs) != len(self.ys):
            raise ValueError("Length of independents and dependents must be the same.")


@dataclass
class Axis:
    """Axis of a graph."""

    label: str | None
    interval: Interval
    _scale: Scale

    def normalize(self, value: float) -> float:
        return self._scale.normalize(value, self.interval)


@dataclass(frozen=True)
class Graph:
    """A graph."""

    title: str | None
    x_axis: Axis
    y_axis: Axis
    series: Series


class Ticker(Protocol):
    """Calculates tick mark values."""

    def get_ticks(self, interval: Interval) -> np.ndarray: ...


@dataclass(frozen=True)
class StepTicker:
    """Regular interval ticks."""

    step: float
    offset: float = 0.0

    def get_ticks(self, interval: Interval) -> np.ndarray:
        # Calculate the first value
        start_n = np.ceil((interval.min - self.offset) / self.step)
        start_value = self.offset + start_n * self.step

        arr = np.arange(start_value, interval.max + self.step, self.step)
        return arr[arr <= interval.max]


class LogMainTicker:
    """Main ticks for common logarithmic axis (1, 10, 100, ...)."""

    def get_ticks(self, interval: Interval) -> np.ndarray:
        if interval.min <= 0:
            return np.array([])

        start_exp = np.ceil(np.log10(interval.min))
        end_exp = np.floor(np.log10(interval.max))

        if start_exp > end_exp:
            return np.array([])

        exps = np.arange(start_exp, end_exp + 1)
        return np.power(10.0, exps)


class LogSubTicker:
    """Sub ticks for common logarithmic axis (2, 3, ..., 9, 20, 30, ...)."""

    def get_ticks(self, interval: Interval) -> np.ndarray:
        if interval.min <= 0:
            return np.array([])

        start_exp = np.floor(np.log10(interval.min))
        end_exp = np.floor(np.log10(interval.max))

        if start_exp > end_exp:
            return np.array([])

        exps = np.arange(start_exp, end_exp + 1)
        bases = np.power(10.0, exps)

        coeffs = np.array([2, 3, 4, 5, 6, 7, 8, 9], dtype=float)

        # Calculate all combinations of (bases × coeffs)
        ticks = np.outer(bases, coeffs).flatten()
        ticks = ticks[(ticks >= interval.min) & (ticks <= interval.max)]
        return np.sort(ticks)
