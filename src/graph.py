import math
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Range:
    """
    正規化のための数値範囲。

    Attributes:
        min (float): 正規化結果が0.0になる値（始点）。
        max (float): 正規化結果が1.0になる値（終点）。

    Note:
        min > max の場合、スケールは反転する。
        (数値的に大きいminが0.0、小さいmaxが1.0となる)
    """

    min: float
    max: float


@dataclass
class Point:
    """2次元座標上の点。"""

    x: float
    y: float


@dataclass
class Series:
    """グラフのデータ系列。"""

    name: str
    points: list[Point]


class Normalizer(Protocol):
    """値を0.0〜1.0の範囲に正規化する"""

    def normalize(self, data_range: Range, value: float) -> float: ...


class LinearNormalizer:
    """線形"""

    def normalize(self, data_range: Range, value: float) -> float:
        if data_range.max == data_range.min:
            raise ValueError("max and min cannot be the same value")

        lower_bound = min(data_range.min, data_range.max)
        upper_bound = max(data_range.min, data_range.max)
        val = max(lower_bound, min(value, upper_bound))

        return (val - data_range.min) / (data_range.max - data_range.min)


class LogNormalizer:
    """対数"""

    def __init__(self, base: float = 10.0):
        self.base = base

    def normalize(self, data_range: Range, value: float) -> float:
        if data_range.min <= 0 or data_range.max <= 0:
            raise ValueError("min and max must be positive for LogNormalizer")
        if data_range.max == data_range.min:
            raise ValueError("max and min cannot be the same value")

        lower_bound = min(data_range.min, data_range.max)
        upper_bound = max(data_range.min, data_range.max)
        val = max(lower_bound, min(value, upper_bound))

        return (math.log(val, self.base) - math.log(data_range.min, self.base)) / (
            math.log(data_range.max, self.base) - math.log(data_range.min, self.base)
        )


@dataclass
class Tick:
    """軸上の目盛り位置。"""

    value: float


class Ticker(Protocol):
    """目盛りの位置決定ロジック。"""

    def get_ticks(self, data_range: Range) -> list[Tick]: ...


class StepTicker:
    """一定間隔で目盛りを生成。"""

    def __init__(self, step: float, offset: float = 0.0):
        self.step = step
        self.offset = offset

    def get_ticks(self, data_range: Range) -> list[Tick]:
        if self.step <= 0:
            return []

        ticks: list[Tick] = []
        lower = min(data_range.min, data_range.max)
        upper = max(data_range.min, data_range.max)

        # offsetを考慮した開始位置を計算
        start = lower + self.offset
        if start < lower:
            # offsetが負の場合、範囲内に入るまで進める
            n = math.ceil((lower - start) / self.step)
            start += n * self.step

        current = start
        while current <= upper:
            ticks.append(Tick(value=current))
            current += self.step

        return ticks


class LogMainTicker:
    """対数軸のメイン目盛り (1, 10, 100, ...)。"""

    def __init__(self, base: float = 10.0):
        self.base = base

    def get_ticks(self, data_range: Range) -> list[Tick]:
        if data_range.min <= 0 or data_range.max <= 0:
            return []

        ticks: list[Tick] = []
        lower = min(data_range.min, data_range.max)
        upper = max(data_range.min, data_range.max)

        # 最小の指数を見つける
        exp_min = math.floor(math.log(lower, self.base))
        exp_max = math.ceil(math.log(upper, self.base))

        for exp in range(exp_min, exp_max + 1):
            value = self.base**exp
            if lower <= value <= upper:
                ticks.append(Tick(value=value))

        return ticks


class LogSubTicker:
    """対数軸のサブ目盛り (2, 3, ..., 9, 20, 30, ...)。"""

    def __init__(self, base: float = 10.0):
        self.base = base

    def get_ticks(self, data_range: Range) -> list[Tick]:
        if data_range.min <= 0 or data_range.max <= 0:
            return []

        ticks: list[Tick] = []
        lower = min(data_range.min, data_range.max)
        upper = max(data_range.min, data_range.max)

        exp_min = math.floor(math.log(lower, self.base))
        exp_max = math.ceil(math.log(upper, self.base))

        for exp in range(exp_min, exp_max + 1):
            base_value = self.base**exp
            # 2, 3, ..., base-1 の位置にサブ目盛り
            for i in range(2, int(self.base)):
                value = base_value * i
                if lower <= value <= upper:
                    ticks.append(Tick(value=value))

        return ticks


class Formatter(Protocol):
    """数値の文字列表現変換ロジック。"""

    def format(self, value: float) -> str: ...


class BasicFormatter:
    """基本的な数値フォーマッター。"""

    def __init__(self, format_string: str = "{:.2f}"):
        self.format_string = format_string

    def format(self, value: float) -> str:
        return self.format_string.format(value)


class IntFormatter:
    """整数フォーマッター。"""

    def format(self, value: float) -> str:
        return str(int(round(value)))


class ScientificFormatter:
    """指数表記フォーマッター。"""

    def __init__(self, precision: int = 0):
        self.precision = precision

    def format(self, value: float) -> str:
        if value == 0:
            return "0"
        exp = math.floor(math.log10(abs(value)))
        mantissa = value / (10**exp)
        if self.precision == 0 and mantissa == 1:
            return f"10^{exp}"
        return f"{mantissa:.{self.precision}f}×10^{exp}"


@dataclass
class TickMark:
    """目盛線の定義。"""

    ticker: Ticker


@dataclass
class TickLabel:
    """目盛数字の定義。"""

    ticker: Ticker
    formatter: Formatter


@dataclass
class Axis:
    """
    グラフの軸定義。
    """

    label: str
    range: Range
    normalizer: Normalizer
    placement: str  # "bottom", "top", "left", "right"
    offset: float = 0.0  # 外枠からのオフセット
    visible: bool = True  # 軸を描画するか

    main_ticks: TickMark | None = None
    sub_ticks: TickMark | None = None
    tick_labels: TickLabel | None = None

    mirror_main_ticks: bool = False
    mirror_sub_ticks: bool = False

    def transform(self, value: float) -> float:
        """値を0.0から1.0の範囲（正規化座標）に変換する。"""
        return self.normalizer.normalize(self.range, value)


@dataclass
class Plot:
    """プロットの定義。"""

    series: Series
    marker: str = "circle"  # "circle", "square", "diamond", "triangle", "none"


@dataclass
class Frame:
    """外枠の定義。"""

    top: bool = True
    bottom: bool = True
    left: bool = True
    right: bool = True


@dataclass
class Title:
    """タイトルの定義。"""

    text: str
    placement: str = "top"  # "top", "bottom"
    offset: float = 30.0


@dataclass
class Graph:
    """グラフ全体の定義。"""

    x_axis: Axis
    y_axis: Axis
    plots: list[Plot] = field(default_factory=list)
    frame: Frame | None = None
    title: Title | None = None
