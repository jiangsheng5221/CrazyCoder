#!/usr/bin/env python3
"""生成 App 图标（1024x1024，无圆角、无透明 —— iOS 会自己裁圆角）。

用法：
    python scripts/make_icon.py

设计：靛蓝→天蓝的对角渐变底 + 白色 </>  代号图形。
纯 Pillow + numpy 绘制，不依赖任何字体文件，换机器也能一键重画。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

SIZE = 1024
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "App", "Assets.xcassets", "AppIcon.appiconset", "icon-1024.png",
)

# 渐变端点（sRGB）
TOP_LEFT = np.array([88, 71, 235], dtype=np.float64)      # 靛蓝
BOTTOM_RIGHT = np.array([16, 185, 214], dtype=np.float64)  # 青蓝


def gradient() -> Image.Image:
    """按对角线做平滑渐变，并叠一层右上角的柔光。"""
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    t = (x + y) / (2.0 * (SIZE - 1))  # 0 → 1 沿左上到右下
    t = t[..., None]
    rgb = TOP_LEFT * (1 - t) + BOTTOM_RIGHT * t

    # 柔光：距离右上角越近越亮
    dist = np.sqrt((x - SIZE * 0.82) ** 2 + (y - SIZE * 0.16) ** 2) / SIZE
    glow = np.clip(1.0 - dist * 1.9, 0.0, 1.0)[..., None] * 0.22
    rgb = rgb * (1 - glow) + np.array([255.0, 255.0, 255.0]) * glow

    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def draw_glyph(img: Image.Image) -> Image.Image:
    """画白色的 </> ，线端做圆角。"""
    draw = ImageDraw.Draw(img)
    width = 62
    white = (255, 255, 255)

    def polyline(points):
        draw.line(points, fill=white, width=width, joint="curve")
        for point in points:  # 圆头
            r = width / 2
            draw.ellipse([point[0] - r, point[1] - r, point[0] + r, point[1] + r], fill=white)

    polyline([(386, 300), (238, 512), (386, 724)])   # <
    polyline([(660, 300), (778, 512), (660, 724)])   # >  （开口朝左）
    polyline([(566, 262), (444, 762)])               # /
    return img


def main() -> int:
    icon = draw_glyph(gradient())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    icon.save(OUT, "PNG", optimize=True)
    print(f"写入 {OUT} ({os.path.getsize(OUT)} 字节, {icon.size[0]}x{icon.size[1]})")

    if icon.size != (SIZE, SIZE):
        print("尺寸不对，App Store 要求 1024x1024", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
