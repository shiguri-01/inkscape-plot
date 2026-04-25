from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import inkex

from graph import Graph
from inkscape import Line, StrokeStyle, TextElement, TextStyle


@dataclass
class GraphRoot:
    """Root element of graph"""

    document: inkex.SvgDocumentElement  # Mainly for get_unique_id()
    svg_group: inkex.Group

    plot_area_width: float
    """Width of plot area (px)

    Plot area: the area where data points are drawn, excluding axis labels and title
    """

    plot_area_height: float
    """Height of plot area (px)

    Plot area: the area where data points are drawn, excluding axis labels and title
    """

    x_inverted: bool = False
    y_inverted: bool = False

    def map_x(self, normalized_x: float) -> float:
        if self.x_inverted:
            normalized_x = 1.0 - normalized_x
        return normalized_x * self.plot_area_width

    def map_y(self, normalized_y: float) -> float:
        if not self.y_inverted:
            normalized_y = 1.0 - normalized_y
        return normalized_y * self.plot_area_height


class GraphPartRenderer(Protocol):
    def render(self, graph: Graph, root: GraphRoot) -> None: ...


def render_graph_parts(
    graph: Graph,
    root: GraphRoot,
    parts: list[GraphPartRenderer],
) -> None:
    for part in parts:
        part.render(graph, root)


@dataclass(frozen=True)
class FrameRenderer(GraphPartRenderer):
    top: bool
    bottom: bool
    left: bool
    right: bool

    stroke_width: float

    def render(self, graph: Graph, root: GraphRoot) -> None:
        if not (self.top or self.bottom or self.left or self.right):
            return

        frame = inkex.Group()
        frame.set("id", root.document.get_unique_id("frame"))

        parts: list[inkex.BaseElement] = []

        # Draw lines with length considering frame line thickness
        if self.top:
            parts.append(
                Line(
                    start=(-self.stroke_width / 2, 0),
                    end=(root.plot_area_width + self.stroke_width / 2, 0),
                )
            )
        if self.bottom:
            parts.append(
                Line(
                    start=(-self.stroke_width / 2, root.plot_area_height),
                    end=(
                        root.plot_area_width + self.stroke_width / 2,
                        root.plot_area_height,
                    ),
                )
            )
        if self.left:
            parts.append(
                Line(
                    start=(0, -self.stroke_width / 2),
                    end=(0, root.plot_area_height + self.stroke_width / 2),
                )
            )
        if self.right:
            parts.append(
                Line(
                    start=(root.plot_area_width, -self.stroke_width / 2),
                    end=(
                        root.plot_area_width,
                        root.plot_area_height + self.stroke_width / 2,
                    ),
                )
            )

        stroke_style = StrokeStyle(width=self.stroke_width)
        for part in parts:
            part.set_style(stroke_style)
            frame.add(part)
        root.svg_group.add(frame)


class TitlePlacement(Enum):
    TOP = "top"
    BOTTOM = "bottom"


@dataclass(frozen=True)
class TitleRenderer(GraphPartRenderer):
    placement: TitlePlacement
    pos_offset: float

    font_family: str
    font_size: float

    def render(self, graph: Graph, root: GraphRoot) -> None:
        if not graph.title:
            return

        title_text = TextElement()
        title_text.text = graph.title
        title_text.set("id", root.document.get_unique_id("title"))

        x = root.plot_area_width / 2
        if self.placement == TitlePlacement.TOP:
            y = -self.pos_offset
        else:  # BOTTOM
            y = root.plot_area_height + self.pos_offset
        title_text.set_position(x, y)

        style = TextStyle(
            font_family=self.font_family,
            font_size=self.font_size,
            anchor="middle",
        )
        title_text.set_style(style)

        root.svg_group.add(title_text)
