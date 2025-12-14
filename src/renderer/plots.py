from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import inkex

from graph import Graph
from inkscape import PathStyle, StrokeStyle
from renderer.renderer import GraphPartRenderer, GraphRoot


class MarkerShape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"
    TRIANGLE = "triangle"
    INVERTED_TRIANGLE = "inverted_triangle"


@dataclass(frozen=True)
class MarkerGenerator(Protocol):
    size: float
    stroke_width: float
    fill_color: str = "#FFFFFF"
    stroke_color: str = "#000000"

    def generate(self, x: float, y: float) -> inkex.BaseElement: ...

    @property
    def _style(self) -> str:
        style = PathStyle(
            fill=self.fill_color,
            stroke=StrokeStyle(color=self.stroke_color, width=self.stroke_width),
        )
        return str(style)


@dataclass(frozen=True)
class CircleMarker(MarkerGenerator):
    def generate(self, x: float, y: float) -> inkex.BaseElement:
        circle = inkex.Circle()
        circle.set("cx", str(x))
        circle.set("cy", str(y))
        circle.set("r", str(self.size / 2))
        circle.set("style", self._style)
        return circle


@dataclass(frozen=True)
class SquareMarker(MarkerGenerator):
    def generate(self, x: float, y: float) -> inkex.BaseElement:
        half = self.size / 2
        rect = inkex.Rectangle()
        rect.set("x", str(x - half))
        rect.set("y", str(y - half))
        rect.set("width", str(self.size))
        rect.set("height", str(self.size))
        rect.set("style", self._style)
        return rect


def _polygon_points(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{px},{py}" for px, py in points)


@dataclass(frozen=True)
class DiamondMarker(MarkerGenerator):
    def generate(self, x: float, y: float) -> inkex.BaseElement:
        half = self.size / 2
        poly = inkex.Polygon()
        poly.set(
            "points",
            _polygon_points(
                [
                    (x, y - half),
                    (x + half, y),
                    (x, y + half),
                    (x - half, y),
                ]
            ),
        )
        poly.set("style", self._style)
        return poly


@dataclass(frozen=True)
class TriangleMarker(MarkerGenerator):
    def generate(self, x: float, y: float) -> inkex.BaseElement:
        half = self.size / 2
        poly = inkex.Polygon()
        poly.set(
            "points",
            _polygon_points(
                [
                    (x, y - half),
                    (x - half, y + half),
                    (x + half, y + half),
                ]
            ),
        )
        poly.set("style", self._style)
        return poly


@dataclass(frozen=True)
class InvertedTriangleMarker(MarkerGenerator):
    def generate(self, x: float, y: float) -> inkex.BaseElement:
        half = self.size / 2
        poly = inkex.Polygon()
        poly.set(
            "points",
            _polygon_points(
                [
                    (x - half, y - half),
                    (x + half, y - half),
                    (x, y + half),
                ]
            ),
        )
        poly.set("style", self._style)
        return poly


_MARKER_CLASS_BY_SHAPE: dict[str, type[MarkerGenerator]] = {
    MarkerShape.CIRCLE.value: CircleMarker,
    MarkerShape.SQUARE.value: SquareMarker,
    MarkerShape.DIAMOND.value: DiamondMarker,
    MarkerShape.TRIANGLE.value: TriangleMarker,
    MarkerShape.INVERTED_TRIANGLE.value: InvertedTriangleMarker,
}


def create_marker_generator(
    shape: MarkerShape | str,
    *,
    size: float,
    stroke_width: float,
    fill_color: str = "#FFFFFF",
    stroke_color: str = "#000000",
) -> MarkerGenerator:
    if isinstance(shape, MarkerShape):
        key = shape.value
    elif isinstance(shape, str):
        key = shape
    else:
        raise TypeError(f"shape must be MarkerShape or str, got: {type(shape)!r}")

    marker_cls = _MARKER_CLASS_BY_SHAPE.get(key)
    if marker_cls is None:
        raise ValueError(
            f"unknown marker shape: {shape!r}. "
            f"supported: {', '.join(s.value for s in MarkerShape)}"
        )

    return marker_cls(
        size=size,
        stroke_width=stroke_width,
        fill_color=fill_color,
        stroke_color=stroke_color,
    )


@dataclass(frozen=True)
class PlotsRenderer(GraphPartRenderer):
    marker: MarkerGenerator

    def render(self, graph: Graph, root: GraphRoot) -> None:
        plots = inkex.Group()
        plots.set("id", root.document.get_unique_id("plots"))

        xs = graph.series.xs
        ys = graph.series.ys

        for x_val, y_val in zip(xs, ys):
            x_val_f = float(x_val)
            y_val_f = float(y_val)

            if not graph.x_axis.interval.contains(x_val_f):
                continue
            if not graph.y_axis.interval.contains(y_val_f):
                continue

            x_norm = graph.x_axis.normalize(x_val_f)
            y_norm = graph.y_axis.normalize(y_val_f)

            x = root.map_x(x_norm)
            y = root.map_y(y_norm)

            marker = self.marker.generate(x, y)
            plots.add(marker)

        root.svg_group.add(plots)
