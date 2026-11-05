# -*- coding: utf-8 -*-
"""旧版 Matplotlib PNG 绘图脚本已停用。

旧脚本使用开发者电脑绝对路径，且生成图与当前固件接口/保护阈值不一致。
当前文档请使用仓库 figures/ 下的 SVG 矢量图：
- fig_架构图.svg
- fig_硬件连接图.svg
- fig_主程序流程图.svg
- fig_保护逻辑流程图.svg
- fig_OLED界面.svg

如需修改图纸，请直接编辑对应 SVG；不要运行旧版 PNG 生成脚本覆盖图纸。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
FILES = [
    "fig_架构图.svg",
    "fig_硬件连接图.svg",
    "fig_主程序流程图.svg",
    "fig_保护逻辑流程图.svg",
    "fig_OLED界面.svg",
]

if __name__ == "__main__":
    missing = [name for name in FILES if not (FIGURES / name).is_file()]
    if missing:
        raise SystemExit("缺少当前版矢量图：" + ", ".join(missing))
    print("当前版 SVG 图纸均存在。旧版 PNG 生成逻辑已停用。")
