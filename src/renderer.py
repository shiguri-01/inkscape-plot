import inkex

from graph import Axis, Frame, Graph, Plot, TickLabel, TickMark, Title
from style import AxisStyle, GraphStyle, MarkerStyle, StrokeStyle, TextStyle, TickStyle
from utils import make_id, sanitize_id


def find_existing_graph(parent: inkex.BaseElement, title: str) -> inkex.Group | None:
    """
    親要素内に同じタイトルを持つグラフグループが既に存在するかチェック。

    Args:
        parent: 検索対象の親要素
        title: グラフのタイトル文字列

    Returns:
        既存のグループが見つかればそれを返す。なければNone。
    """
    graph_id_base = f"graph-{sanitize_id(title)}"

    for child in parent:
        if isinstance(child, inkex.Group):
            child_id = child.get("id", "")
            # IDがgraph_id_baseで始まる場合、既存のグラフとみなす
            # make_id関数は "base_XXXX" という形式でIDを生成するため、
            # "graph-title_" で始まるIDをチェック
            if child_id.startswith(f"{graph_id_base}_"):
                return child
    return None


class InkscapeRenderer:
    """Graph を受け取り、Style を適用して SVG を生成するレンダラー。"""

    def __init__(self, style: GraphStyle):
        self.style = style

    def render(
        self,
        graph: Graph,
        destination: inkex.Group | tuple[inkex.BaseElement, float, float],
        width: float,
        height: float,
    ) -> inkex.Group:
        """
        グラフ全体を描画する。

        Args:
            graph: 描画するグラフの定義
            destination: 描画先。既存のGroupまたは(parent, x, y)のタプル
            width: プロットエリアの幅
            height: プロットエリアの高さ

        Returns:
            使用または作成されたルートグループ
        """
        if isinstance(destination, inkex.Group):
            # 既存のグループに描画
            root = destination
        else:
            # 新しいルートグループを作成
            parent, x, y = destination

            graph_id_base = "graph"
            if graph.group_title:
                graph_id_base = f"graph-{sanitize_id(graph.group_title)}"

            root = parent.add(inkex.Group())
            root.set("id", make_id(graph_id_base))
            root.transform.add_translate(x, y)

        # 外枠
        if graph.frame:
            self._render_frame(root, graph.frame, width, height)

        # X軸
        if graph.x_axis.visible:
            self._render_axis(
                root, graph.x_axis, self.style.x_axis, width, height, "horizontal"
            )

        # Y軸
        if graph.y_axis.visible:
            self._render_axis(
                root, graph.y_axis, self.style.y_axis, width, height, "vertical"
            )

        # プロット
        for plot in graph.plots:
            self._render_plot(root, plot, graph.x_axis, graph.y_axis, width, height)

        # タイトル
        if graph.title:
            self._render_title(root, graph.title, width, height)

        return root

    # =========================================================================
    # 外枠
    # =========================================================================

    def _render_frame(
        self, parent: inkex.Group, frame: Frame, width: float, height: float
    ) -> inkex.Group:
        """外枠を描画。"""
        group = parent.add(inkex.Group())
        group.set("id", make_id("frame"))

        style_str = self._stroke_to_style(self.style.frame)

        # 線の太さの半分（線は中心から描画されるため、角を揃えるために延長が必要）
        half_width = self.style.frame.width / 2

        if frame.top:
            self._draw_line(group, -half_width, 0, width + half_width, 0, style_str)
        if frame.bottom:
            self._draw_line(
                group, -half_width, height, width + half_width, height, style_str
            )
        if frame.left:
            self._draw_line(group, 0, -half_width, 0, height + half_width, style_str)
        if frame.right:
            self._draw_line(
                group, width, -half_width, width, height + half_width, style_str
            )

        return group

    # =========================================================================
    # 軸
    # =========================================================================

    def _render_axis(
        self,
        parent: inkex.Group,
        axis: Axis,
        axis_style: AxisStyle,
        width: float,
        height: float,
        orientation: str,  # "horizontal" or "vertical"
    ) -> inkex.Group:
        """軸を描画。"""
        group = parent.add(inkex.Group())
        axis_id = f"{axis.placement}-axis"
        if axis.label:
            axis_id = f"{axis.placement}-axis-{sanitize_id(axis.label)}"
        group.set("id", make_id(axis_id))

        # 軸の位置を計算
        axis_pos = self._calc_axis_position(axis, width, height)
        opposite_pos = self._calc_opposite_position(axis, width, height)

        # 軸線を描画
        self._draw_axis_line(group, axis, axis_style.line, axis_pos, width, height)

        # メイン目盛線
        if axis.main_ticks:
            self._draw_tick_marks(
                group,
                axis.main_ticks,
                axis,
                axis_style.main_tick,
                axis_pos,
                width,
                height,
                inward=True,
            )
            # ミラー（反対側から内側に向ける）
            if axis.mirror_main_ticks:
                self._draw_tick_marks(
                    group,
                    axis.main_ticks,
                    axis,
                    axis_style.main_tick,
                    opposite_pos,
                    width,
                    height,
                    inward=False,
                )

        # サブ目盛線
        if axis.sub_ticks:
            self._draw_tick_marks(
                group,
                axis.sub_ticks,
                axis,
                axis_style.sub_tick,
                axis_pos,
                width,
                height,
                inward=True,
            )
            # ミラー（反対側から内側に向ける）
            if axis.mirror_sub_ticks:
                self._draw_tick_marks(
                    group,
                    axis.sub_ticks,
                    axis,
                    axis_style.sub_tick,
                    opposite_pos,
                    width,
                    height,
                    inward=False,
                )

        # 目盛数字（軸側のみ）
        if axis.tick_labels:
            self._draw_tick_labels(
                group,
                axis.tick_labels,
                axis,
                axis_style.tick_label,
                axis_style.tick_label_offset,
                axis_pos,
                width,
                height,
            )

        # 軸ラベル
        if axis.label:
            self._draw_axis_label(
                group,
                axis.label,
                axis,
                axis_style.axis_label,
                axis_style.axis_label_offset,
                axis_pos,
                width,
                height,
            )

        return group

    def _calc_axis_position(self, axis: Axis, width: float, height: float) -> float:
        """軸の位置を計算（オフセット込み）。"""
        if axis.placement == "bottom":
            return height + axis.offset
        elif axis.placement == "top":
            return -axis.offset
        elif axis.placement == "left":
            return -axis.offset
        elif axis.placement == "right":
            return width + axis.offset
        return 0

    def _calc_opposite_position(self, axis: Axis, width: float, height: float) -> float:
        """反対側の位置を計算（常に外枠）。"""
        if axis.placement == "bottom":
            return 0  # top edge
        elif axis.placement == "top":
            return height  # bottom edge
        elif axis.placement == "left":
            return width  # right edge
        elif axis.placement == "right":
            return 0  # left edge
        return 0

    def _draw_axis_line(
        self,
        parent: inkex.Group,
        axis: Axis,
        stroke_style: StrokeStyle,
        axis_pos: float,
        width: float,
        height: float,
    ) -> None:
        """軸線を描画。"""
        style_str = self._stroke_to_style(stroke_style)

        if axis.placement in ("bottom", "top"):
            self._draw_line(parent, 0, axis_pos, width, axis_pos, style_str)
        else:  # left, right
            self._draw_line(parent, axis_pos, 0, axis_pos, height, style_str)

    def _draw_tick_marks(
        self,
        parent: inkex.Group,
        tick_mark: TickMark,
        axis: Axis,
        tick_style: TickStyle,
        position: float,
        width: float,
        height: float,
        inward: bool = True,
    ) -> None:
        """目盛線を描画。"""
        ticks = tick_mark.ticker.get_ticks(axis.range)
        style_str = self._stroke_to_style(tick_style.stroke)
        length = tick_style.length

        for tick in ticks:
            norm = axis.transform(tick.value)

            if axis.placement in ("bottom", "top"):
                # 水平軸：X方向に目盛りを配置
                x = norm * width
                if axis.placement == "bottom":
                    # 下軸：上向きに目盛り
                    y1 = position
                    y2 = position - length if inward else position + length
                else:
                    # 上軸：下向きに目盛り
                    y1 = position
                    y2 = position + length if inward else position - length
                self._draw_line(parent, x, y1, x, y2, style_str)
            else:
                # 垂直軸：Y方向に目盛りを配置（Y軸反転）
                y = height - (norm * height)
                if axis.placement == "left":
                    # 左軸：右向きに目盛り
                    x1 = position
                    x2 = position + length if inward else position - length
                else:
                    # 右軸：左向きに目盛り
                    x1 = position
                    x2 = position - length if inward else position + length
                self._draw_line(parent, x1, y, x2, y, style_str)

    def _draw_tick_labels(
        self,
        parent: inkex.Group,
        tick_label: TickLabel,
        axis: Axis,
        text_style: TextStyle,
        label_offset: float,
        axis_pos: float,
        width: float,
        height: float,
    ) -> None:
        """目盛数字を描画。"""
        ticks = tick_label.ticker.get_ticks(axis.range)

        for tick in ticks:
            norm = axis.transform(tick.value)
            text = tick_label.formatter.format(tick.value)

            if axis.placement in ("bottom", "top"):
                x = norm * width
                if axis.placement == "bottom":
                    y = axis_pos + label_offset + text_style.font_size
                    anchor = "middle"
                else:
                    y = axis_pos - label_offset
                    anchor = "middle"
                self._draw_text(parent, x, y, text, text_style, anchor)
            else:
                y = height - (norm * height)
                if axis.placement == "left":
                    x = axis_pos - label_offset
                    anchor = "end"
                else:
                    x = axis_pos + label_offset
                    anchor = "start"
                self._draw_text(
                    parent, x, y + text_style.font_size / 3, text, text_style, anchor
                )

    def _draw_axis_label(
        self,
        parent: inkex.Group,
        label: str,
        axis: Axis,
        text_style: TextStyle,
        label_offset: float,
        axis_pos: float,
        width: float,
        height: float,
    ) -> None:
        """軸ラベルを描画。"""

        if axis.placement == "bottom":
            x = width / 2
            y = axis_pos + label_offset
            self._draw_text(parent, x, y, label, text_style, "middle")
        elif axis.placement == "top":
            x = width / 2
            y = axis_pos - label_offset
            self._draw_text(parent, x, y, label, text_style, "middle")
        elif axis.placement == "left":
            x = axis_pos - label_offset
            y = height / 2
            self._draw_text(parent, x, y, label, text_style, "middle", rotate=-90)
        elif axis.placement == "right":
            x = axis_pos + label_offset
            y = height / 2
            self._draw_text(parent, x, y, label, text_style, "middle", rotate=90)

    # =========================================================================
    # プロット
    # =========================================================================

    def _render_plot(
        self,
        parent: inkex.Group,
        plot: Plot,
        x_axis: Axis,
        y_axis: Axis,
        width: float,
        height: float,
    ) -> inkex.Group:
        """プロットを描画。"""
        group = parent.add(inkex.Group())
        group.set("id", make_id(f"plot-{plot.series.name}"))

        for point in plot.series.points:
            # 正規化
            norm_x = x_axis.transform(point.x)
            norm_y = y_axis.transform(point.y)

            # SVG座標に変換（Y軸反転）
            svg_x = norm_x * width
            svg_y = height - (norm_y * height)

            self._draw_marker(group, svg_x, svg_y, plot.marker, self.style.marker)

        return group

    def _draw_marker(
        self,
        parent: inkex.Group,
        x: float,
        y: float,
        marker_type: str,
        marker_style: MarkerStyle,
    ) -> None:
        """マーカーを描画。"""
        style_str = self._marker_to_style(marker_style)
        size = marker_style.size

        if marker_type == "circle":
            elem = parent.add(inkex.Circle())
            elem.set("cx", str(x))
            elem.set("cy", str(y))
            elem.set("r", str(size / 2))
            elem.set("style", style_str)

        elif marker_type == "square":
            elem = parent.add(inkex.Rectangle())
            elem.set("x", str(x - size / 2))
            elem.set("y", str(y - size / 2))
            elem.set("width", str(size))
            elem.set("height", str(size))
            elem.set("style", style_str)

        elif marker_type == "diamond":
            half = size / 2
            d = f"M {x},{y - half} L {x + half},{y} L {x},{y + half} L {x - half},{y} Z"
            elem = parent.add(inkex.PathElement())
            elem.set("d", d)
            elem.set("style", style_str)

        elif marker_type == "triangle":
            half = size / 2
            h = size * 0.866  # sqrt(3)/2
            d = f"M {x},{y - half} L {x + half},{y + h / 2} L {x - half},{y + h / 2} Z"
            elem = parent.add(inkex.PathElement())
            elem.set("d", d)
            elem.set("style", style_str)

        elif marker_type == "inverted_triangle":
            half = size / 2
            h = size * 0.866
            d = f"M {x},{y + half} L {x + half},{y - h / 2} L {x - half},{y - h / 2} Z"
            elem = parent.add(inkex.PathElement())
            elem.set("d", d)
            elem.set("style", style_str)

        # "none" の場合は何も描画しない

    # =========================================================================
    # タイトル
    # =========================================================================

    def _render_title(
        self, parent: inkex.Group, title: Title, width: float, height: float
    ) -> inkex.Group:
        """タイトルを描画。"""
        group = parent.add(inkex.Group())
        group.set("id", make_id("title"))

        x = width / 2
        if title.placement == "top":
            y = -title.offset
        else:
            y = height + title.offset

        self._draw_text(group, x, y, title.text, self.style.title, "middle")

        return group

    # =========================================================================
    # ヘルパーメソッド
    # =========================================================================

    def _draw_line(
        self,
        parent: inkex.Group,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        style: str,
    ) -> inkex.PathElement:
        """線を描画。"""
        elem = parent.add(inkex.PathElement())
        elem.set("d", f"M {x1},{y1} L {x2},{y2}")
        elem.set("style", style)
        return elem

    def _draw_text(
        self,
        parent: inkex.Group,
        x: float,
        y: float,
        text: str,
        text_style: TextStyle,
        anchor: str = "start",
        rotate: float = 0,
    ) -> inkex.TextElement:
        """テキストを描画。"""
        elem = parent.add(inkex.TextElement())
        elem.set("x", str(x))
        elem.set("y", str(y))
        elem.text = text

        style_parts = [
            f"font-family:{text_style.font_family}",
            f"font-size:{text_style.font_size}",
            f"fill:{text_style.color}",
            f"text-anchor:{anchor}",
        ]
        if text_style.opacity < 1.0:
            style_parts.append(f"opacity:{text_style.opacity}")

        elem.set("style", ";".join(style_parts))

        if rotate != 0:
            elem.transform.add_rotate(rotate, x, y)

        return elem

    def _stroke_to_style(self, stroke: StrokeStyle) -> str:
        """StrokeStyle を CSS 文字列に変換。"""
        parts = [
            f"stroke:{stroke.color}",
            f"stroke-width:{stroke.width}",
            "fill:none",
        ]
        if stroke.opacity < 1.0:
            parts.append(f"opacity:{stroke.opacity}")
        return ";".join(parts)

    def _marker_to_style(self, marker: MarkerStyle) -> str:
        """MarkerStyle を CSS 文字列に変換。"""
        parts = [
            f"fill:{marker.fill}",
            f"stroke:{marker.stroke}",
            f"stroke-width:{marker.stroke_width}",
        ]
        if marker.opacity < 1.0:
            parts.append(f"opacity:{marker.opacity}")
        return ";".join(parts)
