from dataclasses import dataclass


@dataclass
class StrokeStyle:
    """線のスタイル。"""

    color: str = "black"
    width: float = 1.0
    opacity: float = 1.0


@dataclass
class TextStyle:
    """テキストのスタイル。"""

    font_family: str = "sans-serif"
    font_size: float = 12.0
    color: str = "black"
    opacity: float = 1.0


@dataclass
class MarkerStyle:
    """マーカーのスタイル。"""

    fill: str = "white"
    stroke: str = "black"
    stroke_width: float = 1.0
    size: float = 12.0
    opacity: float = 1.0


@dataclass
class TickStyle:
    """目盛りのスタイル。"""

    stroke: StrokeStyle
    length: float


@dataclass
class AxisStyle:
    """軸のスタイル。"""

    line: StrokeStyle
    main_tick: TickStyle
    sub_tick: TickStyle
    tick_label: TextStyle
    axis_label: TextStyle
    tick_label_offset: float = 8.0  # 目盛数字の軸からの距離
    axis_label_offset: float = 30.0  # 軸ラベルの軸からの距離


@dataclass
class GraphStyle:
    """グラフ全体のスタイル。"""

    frame: StrokeStyle
    x_axis: AxisStyle
    y_axis: AxisStyle
    marker: MarkerStyle
    title: TextStyle

    @classmethod
    def default(cls) -> "GraphStyle":
        """デフォルトスタイルを生成。"""
        default_stroke = StrokeStyle(color="black", width=2.0)
        default_text = TextStyle(
            font_family="sans-serif", font_size=14.0, color="black"
        )

        return cls(
            frame=StrokeStyle(color="black", width=2.0),
            x_axis=AxisStyle(
                line=default_stroke,
                main_tick=TickStyle(stroke=default_stroke, length=12.0),
                sub_tick=TickStyle(stroke=default_stroke, length=8.0),
                tick_label=TextStyle(font_size=12.0),
                axis_label=default_text,
            ),
            y_axis=AxisStyle(
                line=default_stroke,
                main_tick=TickStyle(stroke=default_stroke, length=12.0),
                sub_tick=TickStyle(stroke=default_stroke, length=8.0),
                tick_label=TextStyle(font_size=12.0),
                axis_label=default_text,
            ),
            marker=MarkerStyle(
                fill="white", stroke="black", stroke_width=1.0, size=10.0
            ),
            title=TextStyle(font_size=14.0),
        )
