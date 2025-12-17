import inkex
import numpy as np
import re

from graph import (
    Axis,
    Graph,
    Interval,
    LinearScale,
    LogMainTicker,
    LogScale,
    LogSubTicker,
    Series,
    StepTicker,
)
from renderer.axis import (
    AxisLineGenerator,
    AxisRenderer,
    BasicFormatter,
    BottomAxisCoordinateMapper,
    LabelGenerator,
    LeftAxisCoordinateMapper,
    RightAxisCoordinateMapper,
    ScientificFormatter,
    TickLabelsGenerator,
    TickLinesGenerator,
    TopAxisCoordinateMapper,
)
from renderer.plots import PlotsRenderer, create_marker_generator
from renderer.renderer import (
    FrameRenderer,
    GraphPartRenderer,
    GraphRoot,
    TitlePlacement,
    TitleRenderer,
    render_graph_parts,
)

# TODO: 軸のmirror対応


def parse_data(
    data_text: str, x_column: int, y_column: int, delimiter: str
) -> tuple[np.ndarray, np.ndarray]:
    """データテキストをパースする

    Returns:
        tuple[np.ndarray, np.ndarray]: x座標とy座標の配列"""
    x_values: list[float] = []
    y_values: list[float] = []

    if not data_text:
        return (np.array([], dtype=float), np.array([], dtype=float))

    # Inkscapeからのエスケープされた改行を実際の改行に変換
    data_text = data_text.replace("\\n", "\n").replace("\\t", "\t")

    # 区切り文字を決定
    delim_map = {
        "tab": "\t",
        "space": " ",
        "comma": ",",
        "semicolon": ";",
    }
    delim = delim_map.get(delimiter, "\t")

    for line in data_text.split("\n"):
        line = line.strip()
        # コメント行をスキップ
        if not line or line.startswith("#"):
            continue

        # 区切り文字で分割
        if delim == " ":
            cols = line.split()  # 連続スペースを1つの区切りとして扱う
        else:
            cols = line.split(delim)

        try:
            if len(cols) > max(x_column, y_column):
                x_val = float(cols[x_column])
                y_val = float(cols[y_column])
                x_values.append(x_val)
                y_values.append(y_val)
        except (ValueError, IndexError):
            continue  # パースエラーはスキップ

    return (np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float))


def normalize_text(s: str) -> str | None:
    trimmed_text = s.strip()
    if trimmed_text == "":
        return None
    return trimmed_text


class RenderGraphExtension(inkex.EffectExtension):
    def add_arguments(self, pars):
        # Notebook tabs (値としては使わないが、Inkscapeの仕様で必要)
        pars.add_argument("--tab", type=str, default="")

        # Data
        pars.add_argument("--data_text", type=str, default="")
        pars.add_argument("--data_delim", type=str, default="tab")

        # X Axis
        pars.add_argument("--x_scale", type=str, default="x_axis_linear")

        # X Axis Linear
        pars.add_argument("--x_axis_linear_min", type=float, default=0.0)
        pars.add_argument("--x_axis_linear_max", type=float, default=100.0)
        pars.add_argument("--x_linear_maintick_step", type=float, default=10.0)
        pars.add_argument("--x_linear_maintick_offset", type=float, default=0.0)
        pars.add_argument("--x_linear_subtick_step", type=float, default=10.0)
        pars.add_argument("--x_linear_subtick_offset", type=float, default=0.0)
        pars.add_argument("--x_linear_tick_mirror", type=inkex.Boolean, default=False)
        pars.add_argument("--x_linear_numtick_step", type=float, default=10.0)
        pars.add_argument("--x_linear_numtick_offset", type=float, default=0.0)

        # X Axis Log
        pars.add_argument("--x_axis_log_min", type=str, default="0.1")
        pars.add_argument("--x_axis_log_max", type=str, default="100")
        pars.add_argument("--x_log_maintick_visible", type=inkex.Boolean, default=True)
        pars.add_argument("--x_log_subtick_visible", type=inkex.Boolean, default=True)
        pars.add_argument("--x_log_tick_mirror", type=inkex.Boolean, default=False)
        pars.add_argument("--x_log_numtick_visible", type=inkex.Boolean, default=True)

        # X Axis General
        pars.add_argument("--x_axis_label", type=str, default="")
        pars.add_argument("--x_axis_placement", type=str, default="bottom")
        pars.add_argument("--x_axis_pos", type=int, default=0)

        # Y Axis
        pars.add_argument("--y_scale", type=str, default="y_axis_linear")

        # Y Axis Linear
        pars.add_argument("--y_axis_linear_min", type=float, default=0.0)
        pars.add_argument("--y_axis_linear_max", type=float, default=100.0)
        pars.add_argument("--y_linear_maintick_step", type=float, default=10.0)
        pars.add_argument("--y_linear_maintick_offset", type=float, default=0.0)
        pars.add_argument("--y_linear_subtick_step", type=float, default=10.0)
        pars.add_argument("--y_linear_subtick_offset", type=float, default=0.0)
        pars.add_argument("--y_linear_tick_mirror", type=inkex.Boolean, default=False)
        pars.add_argument("--y_linear_numtick_step", type=float, default=10.0)
        pars.add_argument("--y_linear_numtick_offset", type=float, default=0.0)

        # Y Axis Log
        pars.add_argument("--y_axis_log_min", type=str, default="0.1")
        pars.add_argument("--y_axis_log_max", type=str, default="100")
        pars.add_argument("--y_log_maintick_visible", type=inkex.Boolean, default=True)
        pars.add_argument("--y_log_subtick_visible", type=inkex.Boolean, default=True)
        pars.add_argument("--y_log_tick_mirror", type=inkex.Boolean, default=False)
        pars.add_argument("--y_log_numtick_visible", type=inkex.Boolean, default=True)

        # Y Axis General
        pars.add_argument("--y_axis_label", type=str, default="")
        pars.add_argument("--y_axis_placement", type=str, default="left")
        pars.add_argument("--y_axis_pos", type=int, default=0)

        # Plot Data
        pars.add_argument("--x_column", type=int, default=1)
        pars.add_argument("--y_column", type=int, default=2)
        pars.add_argument("--marker_shape", type=str, default="circle")
        pars.add_argument("--marker_size", type=float, default=12.0)
        pars.add_argument("--marker_stroke_width", type=float, default=1.0)

        # Layout
        pars.add_argument("--title_text", type=str, default="")
        pars.add_argument("--title_placement", type=str, default="top")
        pars.add_argument("--title_pos", type=int, default=84)
        pars.add_argument("--frame_top", type=inkex.Boolean, default=True)
        pars.add_argument("--frame_bottom", type=inkex.Boolean, default=True)
        pars.add_argument("--frame_left", type=inkex.Boolean, default=True)
        pars.add_argument("--frame_right", type=inkex.Boolean, default=True)

        # Details
        pars.add_argument("--group_by_title", type=inkex.Boolean, default=False)
        pars.add_argument("--plot_width", type=int, default=400)
        pars.add_argument("--plot_height", type=int, default=400)
        pars.add_argument("--font_family", type=str, default="sans-serif")
        pars.add_argument("--title_font_size", type=int, default=16)
        pars.add_argument("--axis_label_font_size", type=int, default=16)
        pars.add_argument("--tick_label_font_size", type=int, default=14)
        pars.add_argument("--frame_stroke_width", type=float, default=2.0)
        pars.add_argument("--tick_stroke_width", type=float, default=2.0)
        pars.add_argument("--maintick_length", type=float, default=12.0)
        pars.add_argument("--subtick_length", type=float, default=8.0)

        # Render Options
        pars.add_argument("--render_x_axis", type=inkex.Boolean, default=True)
        pars.add_argument("--render_y_axis", type=inkex.Boolean, default=True)
        pars.add_argument("--render_plot", type=inkex.Boolean, default=True)
        pars.add_argument("--render_title", type=inkex.Boolean, default=True)
        pars.add_argument("--render_border", type=inkex.Boolean, default=True)

        # Page
        pars.add_argument("--page", type=int, default=1)

    def effect(self):
        """エフェクトのメイン処理"""
        root = self._create_root_for_page()
        if root is None:
            return

        graph, x_inverted, y_inverted = self._build_graph()
        
        root.x_inverted = x_inverted
        root.y_inverted = y_inverted

        renderer_parts: list[GraphPartRenderer] = []

        frame = self._build_frame_renderer()
        if frame is not None:
            renderer_parts.append(frame)

        title = self._build_title_renderer()
        if title is not None:
            renderer_parts.append(title)

        x_axis = self._build_axis_renderer("x")
        if x_axis is not None:
            renderer_parts.append(x_axis)

        y_axis = self._build_axis_renderer("y")
        if y_axis is not None:
            renderer_parts.append(y_axis)

        plot = self._build_plots_renderer()
        if plot is not None:
            renderer_parts.append(plot)

        render_graph_parts(graph, root, renderer_parts)

    def _create_root_for_page(self) -> GraphRoot | None:
        """ページを基準にルート要素(GraphRoot)を作成する"""
        page_index = self.options.page - 1
        try:
            page_bbox = self.svg.get_page_bbox(page_index)
        except IndexError:
            inkex.errormsg("Error: Specified page index is out of range.")
            return None
        except Exception as e:
            inkex.errormsg(f"Error retrieving page bbox: {e}")
            return None

        width = self._px(float(self.options.plot_width))
        height = self._px(float(self.options.plot_height))

        layer = self.svg.get_current_layer()
        title = normalize_text(self.options.title_text)
        root_group = None
        
        target_label = None
        if title:
            # Sanitize title and add prefix for safe/distinct labeling
            # Allow word chars (including Japanese), spaces, and hyphens. Replace others with underscore.
            sanitized_title = re.sub(r'[^\w\s\-]', '_', title)
            target_label = "graph_" + sanitized_title

        if self.options.group_by_title and target_label is not None:
            # Search for existing group with matching label in current layer
            found_groups = layer.xpath(f"./svg:g[@inkscape:label='{target_label}']")
            if found_groups:
                root_group = found_groups[0]
        
        if root_group is None:
            # Create new group
            x = page_bbox.center_x - width / 2
            y = page_bbox.center_y - height / 2

            root_group = inkex.Group()
            root_group.set("id", self.svg.get_unique_id("graph"))
            
            # Only set label if grouping is enabled (marking it as a target for future plots)
            if self.options.group_by_title and target_label is not None:
                root_group.label = target_label
            
            root_group.transform.add_translate(x, y)
            layer.add(root_group)

        return GraphRoot(
            document=self.svg,
            svg_group=root_group,
            plot_area_width=width,
            plot_area_height=height,
        )

    def _build_frame_renderer(self) -> FrameRenderer | None:
        if not self.options.render_border:
            return None

        return FrameRenderer(
            top=self.options.frame_top,
            bottom=self.options.frame_bottom,
            left=self.options.frame_left,
            right=self.options.frame_right,
            stroke_width=self._px(self.options.frame_stroke_width),
        )

    def _build_title_renderer(self) -> TitleRenderer | None:
        if not self.options.render_title:
            return None

        if normalize_text(self.options.title_text) is None:
            return None

        try:
            placement = TitlePlacement(self.options.title_placement)
        except ValueError:
            placement = TitlePlacement.TOP

        return TitleRenderer(
            font_family=self.options.font_family,
            font_size=self._pt(self.options.title_font_size),
            placement=placement,
            pos_offset=self._px(self.options.title_pos),
        )

    def _build_plots_renderer(self) -> PlotsRenderer | None:
        if not self.options.render_plot:
            return None

        if self.options.marker_shape == "none":
            return None

        marker = create_marker_generator(
            shape=self.options.marker_shape,
            size=self._px(self.options.marker_size),
            stroke_width=self._px(self.options.marker_stroke_width),
        )
        return PlotsRenderer(marker=marker)

    def _build_axis_renderer(self, axis: str) -> AxisRenderer | None:
        if axis == "x":
            if not self.options.render_x_axis:
                return None

            placement = self.options.x_axis_placement
            pos_offset = self._px(self.options.x_axis_pos)
            coord_mapper = (
                BottomAxisCoordinateMapper(pos_offset=pos_offset)
                if placement == "bottom"
                else TopAxisCoordinateMapper(pos_offset=pos_offset)
            )
            scale_mode = self.options.x_scale

            linear_maintick_step = self.options.x_linear_maintick_step
            linear_maintick_offset = self.options.x_linear_maintick_offset
            linear_subtick_step = self.options.x_linear_subtick_step
            linear_subtick_offset = self.options.x_linear_subtick_offset
            linear_numtick_step = self.options.x_linear_numtick_step
            linear_numtick_offset = self.options.x_linear_numtick_offset

            log_maintick_visible = self.options.x_log_maintick_visible
            log_subtick_visible = self.options.x_log_subtick_visible
            log_numtick_visible = self.options.x_log_numtick_visible

            axis_label_text = self.options.x_axis_label
        else:
            if not self.options.render_y_axis:
                return None

            placement = self.options.y_axis_placement
            pos_offset = self._px(self.options.y_axis_pos)
            coord_mapper = (
                LeftAxisCoordinateMapper(pos_offset=pos_offset)
                if placement == "left"
                else RightAxisCoordinateMapper(pos_offset=pos_offset)
            )
            scale_mode = self.options.y_scale

            linear_maintick_step = self.options.y_linear_maintick_step
            linear_maintick_offset = self.options.y_linear_maintick_offset
            linear_subtick_step = self.options.y_linear_subtick_step
            linear_subtick_offset = self.options.y_linear_subtick_offset
            linear_numtick_step = self.options.y_linear_numtick_step
            linear_numtick_offset = self.options.y_linear_numtick_offset

            log_maintick_visible = self.options.y_log_maintick_visible
            log_subtick_visible = self.options.y_log_subtick_visible
            log_numtick_visible = self.options.y_log_numtick_visible

            axis_label_text = self.options.y_axis_label

        line = AxisLineGenerator(stroke_width=self._px(self.options.frame_stroke_width))

        main_tick_lines = None
        sub_tick_lines = None
        tick_labels = None

        if scale_mode.endswith("_linear"):
            if linear_maintick_step > 0:
                main_tick_lines = TickLinesGenerator(
                    ticker=StepTicker(
                        step=linear_maintick_step,
                        offset=linear_maintick_offset,
                    ),
                    length=self._px(self.options.maintick_length),
                    stroke_width=self._px(self.options.tick_stroke_width),
                )

            if linear_subtick_step > 0:
                sub_tick_lines = TickLinesGenerator(
                    ticker=StepTicker(
                        step=linear_subtick_step,
                        offset=linear_subtick_offset,
                    ),
                    length=self._px(self.options.subtick_length),
                    stroke_width=self._px(self.options.tick_stroke_width),
                )

            if linear_numtick_step > 0:
                tick_labels = TickLabelsGenerator(
                    ticker=StepTicker(
                        step=linear_numtick_step,
                        offset=linear_numtick_offset,
                    ),
                    font_family=self.options.font_family,
                    font_size=self._pt(self.options.tick_label_font_size),
                    pos_offset=self._pt(self.options.tick_label_font_size) * 0.6,
                    formatter=BasicFormatter(),
                )
        else:  # log scale
            if log_maintick_visible:
                main_tick_lines = TickLinesGenerator(
                    ticker=LogMainTicker(),
                    length=self._px(self.options.maintick_length),
                    stroke_width=self._px(self.options.tick_stroke_width),
                )

            if log_subtick_visible:
                sub_tick_lines = TickLinesGenerator(
                    ticker=LogSubTicker(),
                    length=self._px(self.options.subtick_length),
                    stroke_width=self._px(self.options.tick_stroke_width),
                )

            if log_numtick_visible:
                tick_labels = TickLabelsGenerator(
                    ticker=LogMainTicker(),
                    font_family=self.options.font_family,
                    font_size=self._pt(self.options.tick_label_font_size),
                    pos_offset=self._pt(self.options.tick_label_font_size) * 0.6,
                    formatter=ScientificFormatter(),
                )

        axis_label = None
        if normalize_text(axis_label_text) is not None:
            axis_label = LabelGenerator(
                font_family=self.options.font_family,
                font_size=self._pt(self.options.axis_label_font_size),
            )

        return AxisRenderer(
            coord_mapper=coord_mapper,
            line=line,
            main_tick_lines=main_tick_lines,
            sub_tick_lines=sub_tick_lines,
            tick_labels=tick_labels,
            axis_label=axis_label,
        )

    def _px(self, value: float) -> float:
        """px値をドキュメント単位に変換する"""
        return self.svg.viewport_to_unit(f"{value}px")

    def _pt(self, value: float) -> float:
        """pt値をドキュメント単位に変換する"""
        return self.svg.viewport_to_unit(f"{value}pt")

    def _build_axis(
        self,
        scale_mode: str,
        linear_mode_key: str,
        linear_min: float,
        linear_max: float,
        log_min: str,
        log_max: str,
        label: str,
    ) -> tuple[Axis, bool]:
        """軸を構築し、反転フラグを返す
        
        Returns:
            tuple[Axis, bool]: (軸, 反転フラグ)
        """
        if scale_mode == linear_mode_key:
            min_val = linear_min
            max_val = linear_max
            scale = LinearScale()
        else:
            min_val = float(log_min)
            max_val = float(log_max)
            scale = LogScale()

        inverted = min_val > max_val
        if inverted:
            min_val, max_val = max_val, min_val

        axis = Axis(
            label=normalize_text(label),
            interval=Interval(min=min_val, max=max_val),
            _scale=scale,
        )
        
        return axis, inverted

    def _build_graph(self) -> tuple[Graph, bool, bool]:
        """グラフを構築し、軸の反転フラグを返す
        
        Returns:
            tuple[Graph, bool, bool]: (グラフ, x軸反転, y軸反転)
        """
        x_axis, x_inverted = self._build_axis(
            scale_mode=self.options.x_scale,
            linear_mode_key="x_axis_linear",
            linear_min=self.options.x_axis_linear_min,
            linear_max=self.options.x_axis_linear_max,
            log_min=self.options.x_axis_log_min,
            log_max=self.options.x_axis_log_max,
            label=self.options.x_axis_label,
        )

        y_axis, y_inverted = self._build_axis(
            scale_mode=self.options.y_scale,
            linear_mode_key="y_axis_linear",
            linear_min=self.options.y_axis_linear_min,
            linear_max=self.options.y_axis_linear_max,
            log_min=self.options.y_axis_log_min,
            log_max=self.options.y_axis_log_max,
            label=self.options.y_axis_label,
        )

        x_column = self.options.x_column - 1
        y_column = self.options.y_column - 1
        x_data, y_data = parse_data(
            self.options.data_text.strip(), x_column, y_column, self.options.data_delim
        )

        graph = Graph(
            title=normalize_text(self.options.title_text),
            x_axis=x_axis,
            y_axis=y_axis,
            series=Series(
                name=None,
                xs=x_data,
                ys=y_data,
            ),
        )
        
        return graph, x_inverted, y_inverted


if __name__ == "__main__":
    RenderGraphExtension().run()
