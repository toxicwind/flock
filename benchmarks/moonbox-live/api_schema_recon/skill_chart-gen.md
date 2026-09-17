---
name: chart-gen
version: 2.5.1
description: "从JSON数据生成高质量PNG/SVG图表图片，支持折线图、柱状图、面积图、散点图、K线图、饼图/环形图、热力图、多系列图和堆叠图等多种类型。适用于快速可视化数据、生成报告图表、绘制趋势变化等场景。当用户请求“生成图表”、“画个趋势图”、“做个柱状图”、“可视化这些数据”，或提供具体数据并要求“做成图表图片”、“导出为PNG”时触发。"
provides:
  - capability: chart-generation
    methods: [lineChart, barChart, areaChart, pieChart, candlestickChart, heatmap]
---

<!-- Localized from: chart-image -->

# 图表图片生成器

使用 Vega-Lite 从数据生成 PNG 图表图片，非常适合无界面的服务器环境。

## 为什么选择这个 Skill？

**专为 Fly.io / VPS / Docker 部署而设计：**
- ✅ **无需原生编译** - 使用 Sharp 预编译二进制文件（不像 `canvas` 需要构建工具）
- ✅ **无需 Puppeteer/浏览器** - 纯 Node.js 实现，无需下载 Chrome，无需无头浏览器开销
- ✅ **轻量级** - 总依赖约 15MB，而基于 Puppeteer 的方案需要 400MB+
- ✅ **冷启动快** - 无需等待浏览器启动，图表生成耗时 <500ms
- ✅ **支持离线** - 无需任何外部 API 调用（不像 QuickChart.io）

## 安装（仅需一次）

```bash
cd /data/clawd/skills/chart-image/scripts && npm install
```

## 快速上手

```bash
node /data/clawd/skills/chart-image/scripts/chart.mjs \
  --type line \
  --data '[{"x":"10:00","y":25},{"x":"10:30","y":27},{"x":"11:00","y":31}]' \
  --title "Price Over Time" \
  --output chart.png
```

## 图表类型

### 折线图（默认）
```bash
node chart.mjs --type line --data '[{"x":"A","y":10},{"x":"B","y":15}]' --output line.png
```

### 柱状图
```bash
node chart.mjs --type bar --data '[{"x":"A","y":10},{"x":"B","y":15}]' --output bar.png
```

### 面积图
```bash
node chart.mjs --type area --data '[{"x":"A","y":10},{"x":"B","y":15}]' --output area.png
```

### 饼图 / 环形图
```bash
# 饼图
node chart.mjs --type pie --data '[{"category":"A","value":30},{"category":"B","value":70}]' \
  --category-field category --y-field value --output pie.png

# 环形图（中间有空洞）
node chart.mjs --type donut --data '[{"category":"A","value":30},{"category":"B","value":70}]' \
  --category-field category --y-field value --output donut.png
```

### K 线图（OHLC）
```bash
node chart.mjs --type candlestick \
  --data '[{"x":"Mon","open":100,"high":110,"low":95,"close":105}]' \
  --open-field open --high-field high --low-field low --close-field close \
  --title "Stock Price" --output candle.png
```

### 热力图
```bash
node chart.mjs --type heatmap \
  --data '[{"x":"Mon","y":"Week1","value":5},{"x":"Tue","y":"Week1","value":8}]' \
  --color-value-field value --color-scheme viridis \
  --title "Activity Heatmap" --output heatmap.png
```

### 多系列折线图
在同一张图表上对比多条趋势线：
```bash
node chart.mjs --type line --series-field "market" \
  --data '[{"x":"Jan","y":10,"market":"A"},{"x":"Jan","y":15,"market":"B"}]' \
  --title "Comparison" --output multi.png
```

### 堆叠柱状图
```bash
node chart.mjs --type bar --stacked --color-field "category" \
  --data '[{"x":"Mon","y":10,"category":"Work"},{"x":"Mon","y":5,"category":"Personal"}]' \
  --title "Hours by Category" --output stacked.png
```

### 成交量叠加（双 Y 轴）
价格折线与成交量柱状图叠加显示：
```bash
node chart.mjs --type line --volume-field volume \
  --data '[{"x":"10:00","y":100,"volume":5000},{"x":"11:00","y":105,"volume":3000}]' \
  --title "Price + Volume" --output volume.png
```

### 迷你图（内联小图表）
```bash
node chart.mjs --sparkline --data '[{"x":"1","y":10},{"x":"2","y":15}]' --output spark.png
```
迷你图默认尺寸为 80x20，透明背景，无坐标轴。

## 选项参考

### 基础选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--type` | 图表类型：line, bar, area, point, pie, donut, candlestick, heatmap | line |
| `--data` | JSON 数据数组 | - |
| `--output` | 输出文件路径 | chart.png |
| `--title` | 图表标题 | - |
| `--width` | 宽度（像素） | 600 |
| `--height` | 高度（像素） | 300 |

### 坐标轴选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--x-field` | X 轴字段名 | x |
| `--y-field` | Y 轴字段名 | y |
| `--x-title` | X 轴标签 | 字段名 |
| `--y-title` | Y 轴标签 | 字段名 |
| `--x-type` | X 轴类型：ordinal（分类）, temporal（时间）, quantitative（数值） | ordinal |
| `--y-domain` | Y 轴范围，格式为 "最小值,最大值" | 自动 |

### 视觉选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--color` | 线条/柱状图颜色 | #e63946 |
| `--dark` | 暗色主题 | false |
| `--svg` | 输出 SVG 格式（而非 PNG） | false |
| `--color-scheme` | Vega 配色方案（category10, viridis 等） | - |

### 警报/监控选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--show-change` | 在最后一个数据点显示涨跌百分比标注 | false |
| `--focus-change` | 将 Y 轴缩放至数据范围的 2 倍，突出变化 | false |
| `--focus-recent N` | 只显示最近 N 个数据点 | 全部 |
| `--show-values` | 标注最大值/最小值 | false |

### 多系列/堆叠选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--series-field` | 多系列折线图的分组字段 | - |
| `--stacked` | 启用堆叠柱状图模式 | false |
| `--color-field` | 堆叠/颜色分类字段 | - |

### K 线图选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--open-field` | OHLC 开盘价字段 | open |
| `--high-field` | OHLC 最高价字段 | high |
| `--low-field` | OHLC 最低价字段 | low |
| `--close-field` | OHLC 收盘价字段 | close |

### 饼图/环形图选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--category-field` | 饼图扇区分类字段 | x |
| `--donut` | 渲染为环形图（中间有空洞） | false |

### 热力图选项
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--color-value-field` | 热力图色彩强度字段 | value |
| `--y-category-field` | Y 轴分类字段 | y |

### 双 Y 轴选项（通用）
| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--y2-field` | 第二 Y 轴字段（独立的右侧坐标轴） | - |
| `--y2-title` | 第二 Y 轴标题 | 字段名 |
| 