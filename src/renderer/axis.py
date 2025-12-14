import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import inkex

from graph import Axis, Graph, Ticker
from inkscape import Line, StrokeStyle, TextElement, TextStyle
from renderer.renderer import GraphPartRenderer, GraphRoot


class NumberFormatter(Protocol):
    def format(self, value: float) -> str: ...


class BasicFormatter:
    def __init__(self, format_string: str = "{:.2f}"):
        self.format_string = format_string

    def format(self, value: float) -> str:
        return self.format_string.format(value)


class ScientificFormatter:
    """指数表記フォーマッター"""

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


class AxisPlacement(Enum):
    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class AxisCoordinateMapper(ABC):
    pos_offset: float = 0.0

    @abstractmethod
    def _get_axis(self, graph: Graph) -> Axis:
        pass

    @abstractmethod
    def _get_parallel_pos(self, root: GraphRoot, norm_val: float) -> float:
        """軸に沿った座標を返す"""
        pass

    @abstractmethod
    def _perpendicular_pos(self, root: GraphRoot) -> float:
        """軸の向きと直交する方向の座標"""
        pass

    @abstractmethod
    def _perpendicular_offset(self, base: float, offset: float) -> float:
        """垂直方向にoffsetだけ外側にずらした座標を返す"""
        pass

    @abstractmethod
    def _combine_coords(
        self, parallel: float, perpendicular: float
    ) -> tuple[float, float]:
        """parallel, perpendicularを(x, y)に並び替える"""
        pass

    @abstractmethod
    def _tick_label_anchor(self) -> str:
        """tick label用のtext-anchorを返す (start|middle|end)"""
        pass

    @abstractmethod
    def _tick_label_dy(self) -> str:
        """tick label用のbaseline補正(dy)を返す"""
        pass


@dataclass(frozen=True)
class TopAxisCoordinateMapper(AxisCoordinateMapper):
    def _get_axis(self, graph: Graph) -> Axis:
        return graph.x_axis

    def _get_parallel_pos(self, root: GraphRoot, value: float) -> float:
        return root.map_x(value)

    def _perpendicular_pos(self, root: GraphRoot) -> float:
        return -self.pos_offset

    def _perpendicular_offset(self, base: float, offset: float) -> float:
        return base - offset

    def _combine_coords(
        self, parallel: float, perpendicular: float
    ) -> tuple[float, float]:
        return (parallel, perpendicular)

    def _tick_label_anchor(self) -> str:
        return "middle"

    def _tick_label_dy(self) -> str:
        # Top軸はラベルが上側に配置されるため、baseline基準のままだと
        # 見た目が他より離れて見えやすい。少し下へ寄せて軸に近づける。
        return "0.0em"


@dataclass(frozen=True)
class BottomAxisCoordinateMapper(AxisCoordinateMapper):
    def _get_axis(self, graph: Graph) -> Axis:
        return graph.x_axis

    def _get_parallel_pos(self, root: GraphRoot, value: float) -> float:
        return root.map_x(value)

    def _perpendicular_pos(self, root: GraphRoot) -> float:
        return root.plot_area_height + self.pos_offset

    def _perpendicular_offset(self, base: float, offset: float) -> float:
        return base + offset

    def _combine_coords(
        self, parallel: float, perpendicular: float
    ) -> tuple[float, float]:
        return (parallel, perpendicular)

    def _tick_label_anchor(self) -> str:
        return "middle"

    def _tick_label_dy(self) -> str:
        # pos_offset を「軸線から文字の外形(上端)までの距離」として扱うため、
        # baselineを下にずらして外形位置が意図に近づくよう補正する。
        return "0.8em"


@dataclass(frozen=True)
class LeftAxisCoordinateMapper(AxisCoordinateMapper):
    def _get_axis(self, graph: Graph) -> Axis:
        return graph.y_axis

    def _get_parallel_pos(self, root: GraphRoot, value: float) -> float:
        return root.map_y(value)

    def _perpendicular_pos(self, root: GraphRoot) -> float:
        return -self.pos_offset

    def _perpendicular_offset(self, base: float, offset: float) -> float:
        return base - offset

    def _combine_coords(
        self, parallel: float, perpendicular: float
    ) -> tuple[float, float]:
        return (perpendicular, parallel)

    def _tick_label_anchor(self) -> str:
        return "end"

    def _tick_label_dy(self) -> str:
        # y座標はbaseline基準なので、tickの位置と文字の見た目中心が揃うように下へ補正。
        return "0.35em"


@dataclass(frozen=True)
class RightAxisCoordinateMapper(AxisCoordinateMapper):
    def _get_axis(self, graph: Graph) -> Axis:
        return graph.y_axis

    def _get_parallel_pos(self, root: GraphRoot, value: float) -> float:
        return root.map_y(value)

    def _perpendicular_pos(self, root: GraphRoot) -> float:
        return root.plot_area_width + self.pos_offset

    def _perpendicular_offset(self, base: float, offset: float) -> float:
        return base + offset

    def _combine_coords(
        self, parallel: float, perpendicular: float
    ) -> tuple[float, float]:
        return (perpendicular, parallel)

    def _tick_label_anchor(self) -> str:
        return "start"

    def _tick_label_dy(self) -> str:
        # y座標はbaseline基準なので、tickの位置と文字の見た目中心が揃うように下へ補正。
        return "0.35em"


def _get_tick_positions(
    graph: Graph,
    root: GraphRoot,
    coord_mapper: AxisCoordinateMapper,
    ticker: Ticker,
) -> list[tuple[float, float]]:
    """軸方向の目盛り位置を取得する

    Returns:
        list[tuple[float, float]]: (値, 位置)のリスト
    """
    axis = coord_mapper._get_axis(graph)

    raw_values = ticker.get_ticks(axis.interval)
    norm_values = [axis.normalize(v) for v in raw_values]
    positions = [coord_mapper._get_parallel_pos(root, nv) for nv in norm_values]

    return list(zip(raw_values, positions))


@dataclass(frozen=True)
class AxisPartGenerator(Protocol):
    def generate(
        self, graph: Graph, root: GraphRoot, coord_mapper: AxisCoordinateMapper
    ) -> inkex.BaseElement: ...


@dataclass(frozen=True)
class AxisLineGenerator(AxisPartGenerator):
    stroke_width: float

    def generate(
        self, graph: Graph, root: GraphRoot, coord_mapper: AxisCoordinateMapper
    ) -> inkex.BaseElement:
        prep = coord_mapper._perpendicular_pos(root)
        start = coord_mapper._combine_coords(
            parallel=coord_mapper._get_parallel_pos(root, 0.0),
            perpendicular=prep,
        )
        end = coord_mapper._combine_coords(
            parallel=coord_mapper._get_parallel_pos(root, 1.0),
            perpendicular=prep,
        )
        axis_line = Line(start, end)

        style = StrokeStyle(width=self.stroke_width)
        axis_line.set_style(style)

        return axis_line


@dataclass(frozen=True)
class TickLinesGenerator(AxisPartGenerator):
    ticker: Ticker

    length: float
    stroke_width: float

    def generate(
        self, graph: Graph, root: GraphRoot, coord_mapper: AxisCoordinateMapper
    ) -> inkex.BaseElement:
        group = inkex.Group()
        group.set("id", root.document.get_unique_id("ticklines"))

        positions = _get_tick_positions(graph, root, coord_mapper, self.ticker)
        prep_start = coord_mapper._perpendicular_pos(root)
        prep_end = coord_mapper._perpendicular_offset(prep_start, -self.length)

        style = StrokeStyle(width=self.stroke_width)

        for _, pos in positions:
            start = coord_mapper._combine_coords(parallel=pos, perpendicular=prep_start)
            end = coord_mapper._combine_coords(parallel=pos, perpendicular=prep_end)
            line = Line(start, end)
            line.set_style(style)

            group.add(line)

        return group


@dataclass(frozen=True)
class TickLabelsGenerator(AxisPartGenerator):
    ticker: Ticker

    pos_offset: float

    font_family: str
    font_size: float
    formatter: NumberFormatter

    def generate(
        self, graph: Graph, root: GraphRoot, coord_mapper: AxisCoordinateMapper
    ) -> inkex.BaseElement:
        group = inkex.Group()
        group.set("id", root.document.get_unique_id("ticklabels"))

        positions = _get_tick_positions(graph, root, coord_mapper, self.ticker)
        base = coord_mapper._perpendicular_pos(root)
        prep = coord_mapper._perpendicular_offset(base, self.pos_offset)

        style = TextStyle(
            font_family=self.font_family,
            font_size=self.font_size,
            anchor=coord_mapper._tick_label_anchor(),
        )

        for raw_value, pos in positions:
            text = TextElement()
            text.text = self.formatter.format(float(raw_value))

            x, y = coord_mapper._combine_coords(parallel=pos, perpendicular=prep)
            text.set_position(x, y)
            text.set_dy(coord_mapper._tick_label_dy())
            text.set_style(style)

            group.add(text)

        return group


@dataclass(frozen=True)
class LabelGenerator(AxisPartGenerator):
    font_family: str
    font_size: float

    def generate(
        self, graph: Graph, root: GraphRoot, coord_mapper: AxisCoordinateMapper
    ) -> inkex.BaseElement:
        axis = coord_mapper._get_axis(graph)
        if not axis.label:
            empty = inkex.Group()
            empty.set("id", root.document.get_unique_id("axislabel"))
            return empty

        label = TextElement()
        label.set("id", root.document.get_unique_id("axislabel"))
        label.text = axis.label

        parallel = coord_mapper._get_parallel_pos(root, 0.5)  # 軸方向の中央
        axis_line_perp = coord_mapper._perpendicular_pos(root)

        offset = self.font_size * (3.2 if axis is graph.y_axis else 1.5)
        perpendicular = coord_mapper._perpendicular_offset(axis_line_perp, offset)

        x, y = coord_mapper._combine_coords(
            parallel=parallel, perpendicular=perpendicular
        )

        label.set_position(x, y)
        label.set_style(
            TextStyle(
                font_family=self.font_family,
                font_size=self.font_size,
                anchor="middle",
            )
        )

        if axis is graph.x_axis:
            label.set_dy(coord_mapper._tick_label_dy())

        # y軸ラベルは下→上に読めるように倒す
        if axis is graph.y_axis:
            label.transform.add_rotate(-90, x, y)

        return label


@dataclass(frozen=True)
class AxisRenderer(GraphPartRenderer):
    coord_mapper: AxisCoordinateMapper

    line: AxisLineGenerator | None = None
    main_tick_lines: TickLinesGenerator | None = None
    sub_tick_lines: TickLinesGenerator | None = None
    tick_labels: TickLabelsGenerator | None = None
    axis_label: LabelGenerator | None = None

    def render(self, graph: Graph, root: GraphRoot) -> None:
        axis_group = inkex.Group()
        axis_group.set("id", root.document.get_unique_id("axis"))

        # 軸線
        if self.line is not None:
            axis_line = self.line.generate(graph, root, self.coord_mapper)
            axis_group.add(axis_line)

        # メイン目盛り線
        if self.main_tick_lines is not None:
            main_ticks = self.main_tick_lines.generate(graph, root, self.coord_mapper)
            axis_group.add(main_ticks)

        # サブ目盛り線
        if self.sub_tick_lines is not None:
            sub_ticks = self.sub_tick_lines.generate(graph, root, self.coord_mapper)
            axis_group.add(sub_ticks)

        # 目盛り数字
        if self.tick_labels is not None:
            labels = self.tick_labels.generate(graph, root, self.coord_mapper)
            axis_group.add(labels)

        # 軸ラベル
        if self.axis_label is not None:
            axis_label = self.axis_label.generate(graph, root, self.coord_mapper)
            axis_group.add(axis_label)

        root.svg_group.add(axis_group)
