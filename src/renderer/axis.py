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
    """Scientific notation formatter."""

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
        """Return coordinate along the axis."""
        pass

    @abstractmethod
    def _perpendicular_pos(self, root: GraphRoot) -> float:
        """Coordinate perpendicular to the axis direction."""
        pass

    @abstractmethod
    def _perpendicular_offset(self, base: float, offset: float) -> float:
        """Return coordinate offset outward in perpendicular direction."""
        pass

    @abstractmethod
    def _combine_coords(
        self, parallel: float, perpendicular: float
    ) -> tuple[float, float]:
        """Rearrange parallel and perpendicular into (x, y)."""
        pass

    @abstractmethod
    def _tick_label_anchor(self) -> str:
        """Return text-anchor for tick label (start|middle|end)."""
        pass

    @abstractmethod
    def _tick_label_dy(self) -> str:
        """Return baseline correction (dy) for tick label."""
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
        # For top axis, labels are positioned above. If baseline remains unchanged,
        # it may appear farther apart than others. Adjust slightly downward to bring closer to axis.
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
        # Treat pos_offset as "distance from axis line to character outline (top)",
        # adjust baseline downward to bring outline position closer to intent.
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
        # Y-coordinate is baseline-based, so adjust downward to align tick position with visual center of text.
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
        # Y-coordinate is baseline-based, so adjust downward to align tick position with visual center of text.
        return "0.35em"


def _get_tick_positions(
    graph: Graph,
    root: GraphRoot,
    coord_mapper: AxisCoordinateMapper,
    ticker: Ticker,
) -> list[tuple[float, float]]:
    """Get tick positions along the axis direction.

    Returns:
        list[tuple[float, float]]: list of (value, position)
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

        parallel = coord_mapper._get_parallel_pos(root, 0.5)  # Center along axis direction
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

        # Rotate y-axis label so it reads from bottom to top
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

        # Axis line
        if self.line is not None:
            axis_line = self.line.generate(graph, root, self.coord_mapper)
            axis_group.add(axis_line)

        # Major tick lines
        if self.main_tick_lines is not None:
            main_ticks = self.main_tick_lines.generate(graph, root, self.coord_mapper)
            axis_group.add(main_ticks)

        # Minor tick lines
        if self.sub_tick_lines is not None:
            sub_ticks = self.sub_tick_lines.generate(graph, root, self.coord_mapper)
            axis_group.add(sub_ticks)

        # Tick labels
        if self.tick_labels is not None:
            labels = self.tick_labels.generate(graph, root, self.coord_mapper)
            axis_group.add(labels)

        # Axis label
        if self.axis_label is not None:
            axis_label = self.axis_label.generate(graph, root, self.coord_mapper)
            axis_group.add(axis_label)

        root.svg_group.add(axis_group)
