# -*- coding: utf-8 -*-
"""重画保护逻辑流程图 v3: 间距充分, 分支清晰"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
OUT = r"E:\23计科1+202308324143+沈炜丹\毕业设计-STM32智能充电监控显示系统\figures"

C_MCU, C_ACT, C_UI, C_OK = "#dbeafe", "#fee2e2", "#fef9c3", "#dcfce7"

fig, ax = plt.subplots(figsize=(9.5, 13))
ax.set_xlim(0, 14); ax.set_ylim(0, 17); ax.axis("off")

def box(cx, cy, w, h, text, fc="#ffffff", fs=10.5, bold=False):
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=0.02",
                                fc=fc, ec="#333", lw=1.2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")

def dia(cx, cy, w, h, text, fs=9.5):
    ax.add_patch(plt.Polygon([[cx, cy+h], [cx+w/2, cy], [cx, cy-h], [cx-w/2, cy]],
                             closed=True, fc="#fff7ed", ec="#333", lw=1.2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs)

def arr(p1, p2, color="#333"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=13,
                                 color=color, lw=1.3, shrinkA=2, shrinkB=2))
def line(pts, color="#333", lw=1.3):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=color, lw=lw)

CX = 7.0   # 主干
LX = 3.0   # 左支(报警级)
RX = 11.5  # 右支(毛刺返回)

# 主干
box(CX, 16.2, 4.6, 0.8, "输入: 滤波后 V / I / T", C_MCU)
dia(CX, 14.6, 6.4, 1.6, "T≥60℃ 或 V≥21V 或 I≥3.3A ?\n(危险级超限)")
dia(CX, 12.2, 5.2, 1.5, "连续 5 次采样均超限?\n(防抖确认)")
box(CX, 9.9, 5.2, 1.1, "切断级：继电器断开低压负载\n蜂鸣器长响，状态闭锁", C_ACT)
box(CX, 8.0, 5.2, 0.9, "等待温度回落 + 人工恢复\n(防热振荡反复通断)")

arr((CX, 15.8), (CX, 15.42))
arr((CX, 13.85), (CX, 12.97)); ax.text(CX+0.15, 13.35, "是", fontsize=10, color="#d62728")
arr((CX, 11.45), (CX, 10.47)); ax.text(CX+0.15, 11.0, "是", fontsize=10)
arr((CX, 9.35), (CX, 8.47))

# 右支: 防抖未确认(毛刺) → 不动作, 返回输入
line([(CX+2.6, 12.2), (RX, 12.2)]); ax.text(CX+2.75, 12.4, "否(毛刺)", fontsize=9.5)
line([(RX, 12.2), (RX, 16.2)])
arr((RX, 16.2), (CX+2.32, 16.2))
ax.text(RX+0.15, 14.2, "本周期\n不动作", fontsize=9, ha="left", color="#555")

# 左支: 非危险级 → 检查纯超温(报警级)
line([(CX-3.2, 14.6), (LX, 14.6)]); ax.text(CX-3.35, 14.8, "否", fontsize=10)
line([(LX, 14.6), (LX, 11.6)])
arr((LX, 11.6), (LX+0.1, 11.6), color="#ff7f0e")
dia(LX, 10.6, 4.6, 1.5, "T ≥ 45℃ ?\n(仅超温, 未达危险级)")
arr((LX, 9.85), (LX, 9.05)); ax.text(LX+0.15, 9.45, "是", fontsize=10)
box(LX, 8.5, 4.6, 1.0, "报警级：蜂鸣器响\n继电器保持吸合", C_UI)
dia(LX, 6.3, 3.6, 1.3, "超限解除?")
arr((LX, 8.0), (LX, 6.97)); ax.text(LX+0.15, 7.5, "", fontsize=10)
arr((LX, 5.65), (LX, 4.72)); ax.text(LX+0.15, 5.15, "是", fontsize=10)
box(LX, 4.2, 4.6, 0.9, "恢复 NORMAL：蜂鸣器停止", C_OK)

# 报警级"否" → 不动作并入右支毛刺线? 直接标注保持
line([(LX+1.8, 6.3), (RX, 6.3)]); ax.text(LX+2.0, 6.5, "否: 保持报警", fontsize=9.5)
line([(RX, 6.3), (RX, 12.2)], color="#333")
# 毛刺否→不动作(右支)汇到"本周期不动作"标注即可; 视觉上右支一条竖线贯穿

ax.set_title("图 4-2  保护逻辑流程图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_保护逻辑流程图.png", dpi=150); plt.close(fig)
print("保护逻辑流程图 v3 完成")
