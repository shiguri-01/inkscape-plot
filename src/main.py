import inkex

from graph import (
    Axis,
    BasicFormatter,
    Frame,
    Graph,
    LinearNormalizer,
    LogMainTicker,
    LogNormalizer,
    LogSubTicker,
    Plot,
    Point,
    Range,
    ScientificFormatter,
    Series,
    StepTicker,
    TickLabel,
    TickMark,
    Title,
)
from renderer import InkscapeRenderer, find_existing_graph
from style import (
    AxisStyle,
    GraphStyle,
    MarkerStyle,
    StrokeStyle,
    TextStyle,
    TickStyle,
)


def parse_data(
    data_text: str, x_column: int, y_column: int, delimiter: str
) -> list[Point]:
    """データテキストをパースしてPointのリストを返す。"""
    points: list[Point] = []

    if not data_text:
        return points

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
                points.append(Point(x=x_val, y=y_val))
        except (ValueError, IndexError):
            continue  # パースエラーはスキップ

    return points


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
        pars.add_argument(
            "--append_to_existing_title", type=inkex.Boolean, default=True
        )

        # Details
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
        """エフェクトのメイン処理。"""
        # インデックス調整
        x_column = self.options.x_column - 1
        y_column = self.options.y_column - 1
        page_index = self.options.page - 1

        # ページのバウンディングボックスを取得
        try:
            page_bbox = self.svg.get_page_bbox(page_index)
        except IndexError:
            inkex.errormsg("Error: Specified page index is out of range.")
            return
        except Exception as e:
            inkex.errormsg(f"Error retrieving page bbox: {e}")
            return

        # プロットエリアのサイズと位置
        width = self.svg.viewport_to_unit(f"{self.options.plot_width}px")
        height = self.svg.viewport_to_unit(f"{self.options.plot_height}px")
        x = page_bbox.center_x - width / 2
        y = page_bbox.center_y - height / 2

        points = parse_data(
            self.options.data_text.strip(), x_column, y_column, self.options.data_delim
        )
        series = Series(name="data", points=points)

        # 軸を構築（プロットの座標変換に必要なため、描画しない場合も構築する）
        x_axis = self._build_x_axis()
        x_axis.visible = self.options.render_x_axis
        y_axis = self._build_y_axis()
        y_axis.visible = self.options.render_y_axis

        # プロット
        plots = []
        if self.options.render_plot and points:
            plots.append(Plot(series=series, marker=self.options.marker_shape))

        # 外枠
        frame = None
        if self.options.render_border:
            frame = Frame(
                top=self.options.frame_top,
                bottom=self.options.frame_bottom,
                left=self.options.frame_left,
                right=self.options.frame_right,
            )

        # タイトル
        title = None
        if self.options.render_title and self.options.title_text:
            title = Title(
                text=self.options.title_text,
                placement=self.options.title_placement,
                offset=self._px(self.options.title_pos),
            )

        # グラフ
        graph = Graph(
            x_axis=x_axis,
            y_axis=y_axis,
            plots=plots,
            frame=frame,
            title=title,
            group_title=self.options.title_text or None,
        )

        style = self._build_style()

        # レンダリング
        renderer = InkscapeRenderer(style)
        layer = self.svg.get_current_layer()

        # タイトルがあれば同じタイトルの既存グラフを探す
        existing_group = None
        if self.options.append_to_existing_title and self.options.title_text:
            existing_group = find_existing_graph(layer, self.options.title_text)

        # 既存のグラフがあればその中に追加で描画、なければ新規に位置指定して描画
        destination = (layer, x, y) if existing_group is None else existing_group
        renderer.render(graph, destination, width, height)

    def _build_x_axis(self) -> Axis:
        """X軸を構築する"""
        is_log = self.options.x_scale == "x_axis_log"

        if is_log:
            data_range = Range(
                min=float(self.options.x_axis_log_min),
                max=float(self.options.x_axis_log_max),
            )
            normalizer = LogNormalizer(base=10)

            main_ticks = None
            if self.options.x_log_maintick_visible:
                main_ticks = TickMark(ticker=LogMainTicker(base=10))

            sub_ticks = None
            if self.options.x_log_subtick_visible:
                sub_ticks = TickMark(ticker=LogSubTicker(base=10))

            tick_labels = None
            if self.options.x_log_numtick_visible:
                tick_labels = TickLabel(
                    ticker=LogMainTicker(base=10),
                    formatter=ScientificFormatter(),
                )

            mirror = self.options.x_log_tick_mirror
        else:
            data_range = Range(
                min=self.options.x_axis_linear_min,
                max=self.options.x_axis_linear_max,
            )
            normalizer = LinearNormalizer()

            main_ticks = None
            if self.options.x_linear_maintick_step > 0:
                main_ticks = TickMark(
                    ticker=StepTicker(
                        step=self.options.x_linear_maintick_step,
                        offset=self.options.x_linear_maintick_offset,
                    )
                )

            sub_ticks = None
            if self.options.x_linear_subtick_step > 0:
                sub_ticks = TickMark(
                    ticker=StepTicker(
                        step=self.options.x_linear_subtick_step,
                        offset=self.options.x_linear_subtick_offset,
                    )
                )

            tick_labels = None
            if self.options.x_linear_numtick_step > 0:
                tick_labels = TickLabel(
                    ticker=StepTicker(
                        step=self.options.x_linear_numtick_step,
                        offset=self.options.x_linear_numtick_offset,
                    ),
                    formatter=BasicFormatter("{:.1f}"),
                )

            mirror = self.options.x_linear_tick_mirror

        return Axis(
            label=self.options.x_axis_label,
            range=data_range,
            normalizer=normalizer,
            placement=self.options.x_axis_placement,
            offset=self._px(self.options.x_axis_pos),
            main_ticks=main_ticks,
            sub_ticks=sub_ticks,
            tick_labels=tick_labels,
            mirror_main_ticks=mirror,
            mirror_sub_ticks=mirror,
        )

    def _build_y_axis(self) -> Axis:
        """Y軸を構築する"""
        is_log = self.options.y_scale == "y_axis_log"

        if is_log:
            data_range = Range(
                min=float(self.options.y_axis_log_min),
                max=float(self.options.y_axis_log_max),
            )
            normalizer = LogNormalizer(base=10)

            main_ticks = None
            if self.options.y_log_maintick_visible:
                main_ticks = TickMark(ticker=LogMainTicker(base=10))

            sub_ticks = None
            if self.options.y_log_subtick_visible:
                sub_ticks = TickMark(ticker=LogSubTicker(base=10))

            tick_labels = None
            if self.options.y_log_numtick_visible:
                tick_labels = TickLabel(
                    ticker=LogMainTicker(base=10),
                    formatter=ScientificFormatter(),
                )

            mirror = self.options.y_log_tick_mirror
        else:
            data_range = Range(
                min=self.options.y_axis_linear_min,
                max=self.options.y_axis_linear_max,
            )
            normalizer = LinearNormalizer()

            main_ticks = None
            if self.options.y_linear_maintick_step > 0:
                main_ticks = TickMark(
                    ticker=StepTicker(
                        step=self.options.y_linear_maintick_step,
                        offset=self.options.y_linear_maintick_offset,
                    )
                )

            sub_ticks = None
            if self.options.y_linear_subtick_step > 0:
                sub_ticks = TickMark(
                    ticker=StepTicker(
                        step=self.options.y_linear_subtick_step,
                        offset=self.options.y_linear_subtick_offset,
                    )
                )

            tick_labels = None
            if self.options.y_linear_numtick_step > 0:
                tick_labels = TickLabel(
                    ticker=StepTicker(
                        step=self.options.y_linear_numtick_step,
                        offset=self.options.y_linear_numtick_offset,
                    ),
                    formatter=BasicFormatter("{:.1f}"),
                )

            mirror = self.options.y_linear_tick_mirror

        return Axis(
            label=self.options.y_axis_label,
            range=data_range,
            normalizer=normalizer,
            placement=self.options.y_axis_placement,
            offset=self._px(self.options.y_axis_pos),
            main_ticks=main_ticks,
            sub_ticks=sub_ticks,
            tick_labels=tick_labels,
            mirror_main_ticks=mirror,
            mirror_sub_ticks=mirror,
        )

    def _px(self, value: float) -> float:
        """px値をドキュメント単位に変換する"""
        return self.svg.viewport_to_unit(f"{value}px")

    def _pt(self, value: float) -> float:
        """pt値をドキュメント単位に変換する"""
        return self.svg.viewport_to_unit(f"{value}pt")

    def _build_style(self) -> GraphStyle:
        """スタイルを構築する"""
        font_family = self.options.font_family

        frame_stroke = StrokeStyle(
            color="black",
            width=self._px(self.options.frame_stroke_width),
        )

        tick_stroke = StrokeStyle(
            color="black",
            width=self._px(self.options.tick_stroke_width),
        )

        tick_label_font_size = self._pt(self.options.tick_label_font_size)
        axis_label_font_size = self._pt(self.options.axis_label_font_size)

        x_axis_style = AxisStyle(
            line=frame_stroke,
            main_tick=TickStyle(
                stroke=tick_stroke, length=self._px(self.options.maintick_length)
            ),
            sub_tick=TickStyle(
                stroke=tick_stroke, length=self._px(self.options.subtick_length)
            ),
            tick_label=TextStyle(
                font_family=font_family,
                font_size=tick_label_font_size,
            ),
            axis_label=TextStyle(
                font_family=font_family,
                font_size=axis_label_font_size,
            ),
            tick_label_offset=tick_label_font_size * 0.4,
            axis_label_offset=tick_label_font_size * 1.5 + axis_label_font_size,
        )

        y_axis_style = AxisStyle(
            line=frame_stroke,
            main_tick=TickStyle(
                stroke=tick_stroke, length=self._px(self.options.maintick_length)
            ),
            sub_tick=TickStyle(
                stroke=tick_stroke, length=self._px(self.options.subtick_length)
            ),
            tick_label=TextStyle(
                font_family=font_family,
                font_size=tick_label_font_size,
            ),
            axis_label=TextStyle(
                font_family=font_family,
                font_size=axis_label_font_size,
            ),
            # Y軸: 目盛り数字の幅があるので大きめのオフセット
            tick_label_offset=tick_label_font_size * 0.5,
            axis_label_offset=tick_label_font_size * 2 + axis_label_font_size,
        )

        return GraphStyle(
            frame=frame_stroke,
            x_axis=x_axis_style,
            y_axis=y_axis_style,
            marker=MarkerStyle(
                fill="white",
                stroke="black",
                stroke_width=self._px(self.options.marker_stroke_width),
                size=self._px(self.options.marker_size),
            ),
            title=TextStyle(
                font_family=font_family,
                font_size=self._pt(self.options.title_font_size),
            ),
        )


if __name__ == "__main__":
    RenderGraphExtension().run()
