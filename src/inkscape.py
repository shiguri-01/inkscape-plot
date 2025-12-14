from dataclasses import dataclass

import inkex


@dataclass(frozen=True)
class TextStyle:
    font_family: str = "sans-serif"
    font_size: float = 12.0
    color: str = "black"
    anchor: str = "middle"  # "start", "middle", "end"

    def __str__(self) -> str:
        parts: list[str] = [
            f"font-family:{self.font_family}",
            f"font-size:{self.font_size}pt",
            f"fill:{self.color}",
            f"text-anchor:{self.anchor}",
        ]
        return ";".join(parts)


class TextElement(inkex.TextElement):
    def __init__(self):
        super().__init__()

    def set_position(self, x: float, y: float):
        self.set("x", str(x))
        self.set("y", str(y))

    def set_style(self, style: TextStyle):
        self.set("style", str(style))

    def set_dy(self, dy: str):
        self.set("dy", dy)


@dataclass(frozen=True)
class StrokeStyle:
    color: str = "black"
    width: float = 1.0

    def __str__(self) -> str:
        parts: list[str] = [
            f"stroke:{self.color}",
            f"stroke-width:{self.width}pt",
        ]
        return ";".join(parts)


class Line(inkex.Line):
    def __init__(self, start: tuple[float, float], end: tuple[float, float]):
        super().__init__()
        self.set("x1", str(start[0]))
        self.set("y1", str(start[1]))
        self.set("x2", str(end[0]))
        self.set("y2", str(end[1]))

    def set_style(self, style: StrokeStyle):
        self.set("style", str(style))


@dataclass(frozen=True)
class PathStyle:
    stroke: StrokeStyle
    fill: str = "none"

    def __str__(self) -> str:
        parts: list[str] = [
            str(self.stroke),
            f"fill:{self.fill}",
        ]
        return ";".join(parts)
