# inkscape-plot

[日本語](./README.ja.md)

An Inkscape extension for drawing graphs and plots.

- **Copy-paste from Excel**: Data can be pasted directly from Excel spreadsheets.
- **Logarithmic scales supported**: Create both semi-log and log-log plots.
- **Easy to edit**: Since it runs in Inkscape, you can edit the graph directly after rendering. Adjusting axis labels, adding legends, and other customizations are simple.

<div style="text-align:center;">
   <img src="docs/assets/sample.png" alt="Sample Plot" style="max-width:480px;"/>
</div>

## Installation

Verified Inkscape version: 1.4.2

1. Download (or clone) this repository.
2. Open **Edit > Preferences > System** from the Inkscape menu and note the **User Extensions** folder path.
3. Move the downloaded folder into the folder noted in step 2.

   ```bash
   (User Extensions)/
      inkscape-plot/
         plot.inx
         src/
            main.py
            ...
         ...
   ```
4. Restart Inkscape.

## Usage

From the Inkscape menu, select **Extensions > Render > Plot**.

### Quick Start

1. Paste the following data into the **Data** tab (delimiter: space):

   ```text
   # x  y
   0   0
   1   2
   2   4
   3   6
   4   8
   ```

2. **X Axis** tab: min=0, max=4 (linear)
3. **Y Axis** tab: min=0, max=8 (linear)
4. **Plot** tab: x column=1, y column=2
5. Click **Apply**

### Basics

1. Enter numerical data in the **Data** tab, separated by tabs.
   - Lines starting with `#` are treated as comments and ignored.
   - You can paste directly from Excel.
   - Space-separated and comma-separated formats are also supported.
2. In the **X Axis** and **Y Axis** tabs, set the range and tick intervals.
   - You can choose between linear and logarithmic scales.
3. In the **Plot** tab, specify which columns to use for x and y values, and choose a marker shape.
4. In the **Title & Frame** tab, set the graph title and frame line style.
5. Use the **Render Items** section at the bottom of the dialog to select what to draw (all are enabled by default).
6. Click the **Apply** button to render the graph.

### Advanced: Overlaying Multiple Series

This extension renders only one data series per execution, but you can create multi-series graphs by running the extension multiple times to overlay plots.

**Data**:

```text
# Time  Temperature  Humidity
1      20           60
2      22           58
3      24           55
```

1. **Draw the temperature graph**
   - Data tab: Enter the data above
   - X Axis tab: min=1, max=3
   - Y Axis tab: min=0, max=30 (temperature range)
   - Plot tab: x column=1, y column=2
   - Render Items: Check all

2. **Add humidity**
   - Data tab: (same as above)
   - X Axis tab: (same as above)
   - Y Axis tab: min=0, max=100 (humidity range), Placement/Outside offset (px)=90
   - Plot tab: x column=1, y column=3
   - Render Items: Check only "Y Axis" and "Plot"

### Troubleshooting

#### "Plotter Output" does not appear in the menu

- Restart Inkscape
- Verify that the installation folder is directly under the "User Extensions" folder

#### Nothing is rendered

- Check that the page number is correct
- Verify that the target layer is not hidden

#### Data points are not plotted

- Ensure the data values are within the axis ranges
- Verify the column numbers referenced in the Plot tab. Column numbering starts at 1
- Set the marker shape to something other than "(none)"
- Check the "Plot" option in Render Items

#### Error with logarithmic axes

- Ensure the data does not contain values ≤ 0
- Verify that the axis minimum is not ≤ 0

## Contributing

Feel free to submit pull requests or issues if you have suggestions for improvements or find bugs.

### Development Environment

```bash
uv sync
uv run ruff check .  # Linting
uv run ruff format . # Formatting
```

> [!NOTE]
> The runtime environment created by uv differs from the actual runtime environment for running the extension.
> Therefore, external package dependencies cannot be added.
> Always test the extension in Inkscape to verify it works correctly.

---

© 2025 shiguri | [MIT License](LICENSE)
