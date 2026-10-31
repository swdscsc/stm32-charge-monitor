# -*- coding: utf-8 -*-
"""重画论文示意图 v2: 架构图 / 硬件连接图 / 主程序流程图 / 保护逻辑流程图"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
OUT = r"E:\23计科1+202308324143+沈炜丹\毕业设计-STM32智能充电监控显示系统\figures"

C_MCU, C_SENSOR, C_ACT, C_UI, C_IO = "#dbeafe", "#dcfce7", "#fee2e2", "#fef9c3", "#f3e8ff"

def box(ax, cx, cy, w, h, text, fc="#ffffff", fs=11, bold=False):
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=0.02",
                                fc=fc, ec="#333333", lw=1.2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")
    return (cx, cy, w, h)

def edge(b, side):
    """返回盒子指定边中点: side in L R T B"""
    cx, cy, w, h = b
    return {"L": (cx-w/2, cy), "R": (cx+w/2, cy), "T": (cx, cy+h/2), "B": (cx, cy-h/2)}[side]

def arrow(ax, p1, p2, text="", color="#333333", fs=9, toff=(0, 0.12), color_text=None):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=13,
                                 color=color, lw=1.2, shrinkA=2, shrinkB=2))
    if text:
        ax.text((p1[0]+p2[0])/2 + toff[0], (p1[1]+p2[1])/2 + toff[1], text,
                ha="center", fontsize=fs, color=color_text or color)

# ================================================================
# 图2-1 系统总体架构框图 (MCU居中, 左传感器 右输出 上电源链)
# ================================================================
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

mcu = box(ax, 5, 5.0, 2.6, 2.2, "STM32F103C8T6\n主控 MCU", C_MCU, fs=12, bold=True)
ina = box(ax, 1.7, 7.6, 2.0, 1.0, "INA219\n电压/电流采集", C_SENSOR)
ntc = box(ax, 1.7, 5.0, 2.0, 1.0, "NTC 热敏电阻\n外壳测温", C_SENSOR)
oled = box(ax, 8.3, 7.6, 2.0, 1.0, "0.96寸 OLED\nSSD1306", C_UI)
buzz = box(ax, 8.3, 5.6, 2.0, 0.85, "蜂鸣器", C_ACT)
relay = box(ax, 8.3, 3.9, 2.0, 0.85, "继电器", C_ACT)
esp = box(ax, 8.3, 2.0, 2.0, 1.0, "ESP8266\n(预留)", C_IO)
psu = box(ax, 1.7, 9.0, 2.0, 0.9, "60W PD 快充头", C_SENSOR, bold=True)
load = box(ax, 5, 9.0, 2.0, 0.9, "受控负载", "#ffffff", bold=True)

# 电源链: 快充头 -> INA219 -> 继电器?  实际链路: 快充头 -> INA219 -> 继电器 -> 负载
arrow(ax, edge(psu, "R"), (3.6, 8.6), "", color="#666666")
ax.plot([3.6, 3.6], [8.6, 5.0], color="#666", lw=1.2)
arrow(ax, (3.6, 5.0), edge(ntc, "L") if False else (2.7, 5.0), "", color="#ffffff00")
# 重画清晰链路
ax.clear(); ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
psu = box(ax, 1.7, 9.0, 2.0, 0.9, "60W PD 快充头", C_SENSOR, bold=True)
ina = box(ax, 5.0, 9.0, 2.2, 0.9, "INA219 采集", C_SENSOR)
relay = box(ax, 8.3, 9.0, 1.8, 0.9, "继电器", C_ACT)
load = box(ax, 8.3, 7.4, 1.8, 0.8, "受控负载", "#ffffff")
mcu = box(ax, 5.0, 5.0, 2.6, 2.0, "STM32F103C8T6\n主控 MCU", C_MCU, fs=12, bold=True)
ntc = box(ax, 1.7, 4.2, 2.0, 0.9, "NTC 外壳测温", C_SENSOR)
oled = box(ax, 8.3, 5.6, 2.0, 0.9, "0.96寸 OLED", C_UI)
buzz = box(ax, 8.3, 4.0, 2.0, 0.8, "蜂鸣器", C_ACT)
esp = box(ax, 8.3, 2.2, 2.0, 0.9, "ESP8266 (预留)", C_IO)

arrow(ax, edge(psu, "R"), edge(ina, "L"), "20V/3A", color="#666", toff=(0, 0.15))
arrow(ax, edge(ina, "R"), edge(relay, "L"), "", color="#666")
arrow(ax, edge(relay, "B"), edge(load, "T"), "", color="#666")
arrow(ax, (5.0, 8.55), edge(mcu, "T"), "I2C1", fs=9)
arrow(ax, edge(ntc, "R"), edge(mcu, "L"), "ADC1_IN0", fs=9, toff=(0, 0.12))
arrow(ax, edge(mcu, "R"), (7.3, 5.6), "I2C1", fs=9, toff=(0, 0.12))
arrow(ax, (7.3, 4.6), (7.3, 4.0), "", color="#333")
ax.plot([6.3, 7.3], [4.4, 4.6], color="#333", lw=0)
arrow(ax, edge(mcu, "R"), (7.3, 4.0), "GPIO", fs=9, toff=(0, -0.3))
arrow(ax, edge(mcu, "B"), (7.3, 2.2), "USART1", fs=9, toff=(0, 0.1))
ax.plot([7.3, 8.3-0.99], [2.2, 2.2], color="#333", lw=1.2)
ax.add_patch(FancyArrowPatch((7.32, 2.2), (7.3, 2.2), arrowstyle="-|>", mutation_scale=13, color="#333", lw=1.2))
# 继电器控制线
arrow(ax, (6.3, 5.6), (7.3, 9.0-0.5), "GPIO(保护)", fs=8, color="#b91c1c", toff=(0.4, 0))
ax.set_title("图 2-1  系统总体架构框图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_架构图.png", dpi=150); plt.close(fig)

# ================================================================
# 图3-1 硬件连接图 (引脚级)
# ================================================================
fig, ax = plt.subplots(figsize=(10, 7))
ax.set_xlim(0, 12); ax.set_ylim(0, 10); ax.axis("off")

mcu = box(ax, 6, 5.0, 2.6, 3.4, "STM32F103C8T6\n\nPB6 SCL\nPB7 SDA\nPA0 ADC\nPA1/PA2\nPA9/PA10",
          C_MCU, fs=10, bold=False)
ax.texts[-1].set_text("STM32F103C8T6")
ax.texts[-1].set_position((6, 6.15))
for i, t in enumerate(["PB6/PB7 → I2C1", "PA0 → ADC1_IN0", "PA1 → 蜂鸣器",
                        "PA2 → 继电器IN", "PA9/PA10 → USART1"]):
    ax.text(6, 5.55 - i*0.42, t, ha="center", fontsize=9)

oled = box(ax, 2.2, 8.4, 2.4, 0.9, "OLED SSD1306", C_UI)
ina = box(ax, 2.2, 7.0, 2.4, 0.9, "INA219 (0.1Ω)", C_SENSOR)
ntc = box(ax, 2.2, 5.6, 2.4, 0.9, "NTC 10k + 上拉10k", C_SENSOR)
buzz = box(ax, 2.2, 4.2, 2.4, 0.9, "有源蜂鸣器", C_ACT)
relay = box(ax, 2.2, 2.8, 2.4, 0.9, "继电器模块", C_ACT)
esp = box(ax, 10.0, 2.8, 2.2, 0.9, "ESP8266-01S", C_IO)
psu = box(ax, 10.0, 7.0, 2.2, 1.0, "60W PD 快充头\n20V/3A", C_SENSOR, bold=True)
load = box(ax, 10.0, 5.0, 2.2, 0.9, "低压负载", "#ffffff")

arrow(ax, edge(oled, "R"), (4.7, 6.3), "I2C", fs=8, toff=(0.2, 0.25))
arrow(ax, edge(ina, "R"), (4.7, 5.9), "I2C", fs=8, toff=(0.2, -0.05))
arrow(ax, edge(ntc, "R"), (4.7, 5.3), "模拟", fs=8, toff=(0.25, 0))
arrow(ax, edge(buzz, "R"), (4.7, 4.7), "PA1", fs=8, toff=(0.25, 0))
arrow(ax, edge(relay, "R"), (4.7, 4.2), "PA2", fs=8, toff=(0.3, -0.15))
arrow(ax, (7.3, 4.2), edge(esp, "L"), "串口", fs=8, toff=(0, 0.2))
# 功率链路: 快充头 -> INA219 串接 -> 继电器 -> 负载
ax.plot([11.0, 11.0], [6.5, 5.45], color="#b91c1c", lw=1.6)
arrow(ax, (11.0, 5.45), (10.0+0.0, 5.45), "", color="#b91c1c")
ax.plot([3.4, 3.4], [7.0, 2.8], color="#b91c1c", lw=0)
ax.annotate("", xy=(10.0, 7.0-0.5), xytext=(11.0, 6.5),
            arrowprops=dict(arrowstyle="-", color="#b91c1c", lw=1.2))
ax.text(11.15, 6.0, "输出回路", fontsize=8, color="#b91c1c")
ax.text(6, 0.6, "注：INA219 串接于快充输出与继电器之间；继电器切断低压负载回路，不改动市电输入。",
        fontsize=9, ha="center", color="#555555")
ax.set_title("图 3-1  系统硬件连接图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_硬件连接图.png", dpi=150); plt.close(fig)

# ================================================================
# 图4-1 主程序流程图 (严格上下居中, 循环回边右侧)
# ================================================================
fig, ax = plt.subplots(figsize=(7, 12))
ax.set_xlim(0, 10); ax.set_ylim(0, 16); ax.axis("off")
CX = 4.2

def fbox3(y, text, fc="#ffffff", fs=10.5, w=5.0, h=0.85):
    box(ax, CX, y, w, h, text, fc, fs)
def diamond3(y, text, w=4.2, h=1.25, fs=10):
    ax.add_patch(plt.Polygon([[CX, y+h], [CX+w/2, y], [CX, y-h], [CX-w/2, y]],
                             closed=True, fc="#fff7ed", ec="#333", lw=1.2))
    ax.text(CX, y, text, ha="center", va="center", fontsize=fs)
def varrow(y1, y2, x=CX):
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle="-|>",
                                 mutation_scale=12, color="#333", lw=1.2))
def line(pts, color="#333", lw=1.2):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw)

fbox3(15.3, "上电复位，系统时钟 72MHz", C_MCU); varrow(14.87, 14.68)
fbox3(14.25, "初始化 GPIO/I2C1/ADC1/USART1"); varrow(13.82, 13.63)
fbox3(13.2, "INA219 标定 / OLED 自检 / 保护初值"); varrow(12.77, 12.58)

diamond3(11.7, "主循环"); line([(CX, 12.58), (CX, 12.33)])
varrow(11.7-1.25, 10.9)
diamond3(10.25, "100ms 采样周期到?")
varrow(10.25-1.25, 9.75)
fbox3(9.3, "读 INA219 (V/I/P)；NTC ADC 采样\n→ B 参数方程 → 温度")
varrow(8.87, 8.68)
fbox3(8.25, "滑动窗口均值滤波 (N=8)")
varrow(7.82, 7.63)
fbox3(7.2, "保护逻辑判定(阈值+防抖)\n驱动蜂鸣器 / 继电器", C_ACT)
varrow(6.77, 6.58)
diamond3(5.9, "500ms 显示周期到?")
line([(CX+2.1, 5.9), (7.6, 5.9)], color="#333")
ax.text(CX+2.25, 6.05, "是", fontsize=9)
fbox3(4.7, "OLED 界面刷新\n电压/电流/功率/温度/状态", C_UI, w=4.4, h=1.0)
line([(7.6, 5.9), (7.6, 4.7), (6.45, 4.7)], color="#333")
ax.add_patch(FancyArrowPatch((6.45, 4.7), (6.42, 4.7), arrowstyle="-|>",
                             mutation_scale=12, color="#333", lw=1.2))
line([(CX, 4.2), (CX, 4.0)])
varrow(4.7-0.5, 4.0)
diamond3(3.3, "1000ms 上传周期到?")
line([(CX+2.1, 3.3), (8.6, 3.3)], color="#333")
ax.text(CX+2.25, 3.45, "是", fontsize=9)
fbox3(2.1, "ESP8266 MQTT 遥测上传\n(编译开关可裁剪)", C_IO, w=4.4, h=1.0)
line([(8.6, 3.3), (8.6, 2.1), (6.45, 2.1)], color="#333")
ax.add_patch(FancyArrowPatch((6.45, 2.1), (6.42, 2.1), arrowstyle="-|>",
                             mutation_scale=12, color="#333", lw=1.2))
# 循环回边: 右侧大回环
line([(8.6, 1.6), (8.6, 0.7), (9.4, 0.7)], color="#333")
ax.text(8.35, 1.85, "否", fontsize=9)
line([(9.4, 0.7), (9.4, 10.25)], color="#333")
line([(9.4, 10.25), (6.32, 10.25)], color="#333")
ax.add_patch(FancyArrowPatch((6.32, 10.25), (6.3, 10.25), arrowstyle="-|>",
                             mutation_scale=12, color="#333", lw=1.2))
ax.text(9.55, 5.5, "循 环", rotation=90, fontsize=10, va="center")
ax.set_title("图 4-1  主程序流程图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_主程序流程图.png", dpi=150); plt.close(fig)

# ================================================================
# 图4-2 保护逻辑流程图 (两级: 报警级/切断级)
# ================================================================
fig, ax = plt.subplots(figsize=(8, 10.5))
ax.set_xlim(0, 12); ax.set_ylim(0, 14); ax.axis("off")
CX = 5.0

def fbox4(y, text, fc="#ffffff", fs=10.5, w=5.4, h=0.85, cx=CX):
    box(ax, cx, y, w, h, text, fc, fs)
def diamond4(y, text, w=5.6, h=1.3, fs=9.5, cx=CX):
    ax.add_patch(plt.Polygon([[cx, y+h], [cx+w/2, y], [cx, y-h], [cx-w/2, y]],
                             closed=True, fc="#fff7ed", ec="#333", lw=1.2))
    ax.text(cx, y, text, ha="center", va="center", fontsize=fs)
def varrow4(y1, y2, x=CX, color="#333"):
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle="-|>",
                                 mutation_scale=12, color=color, lw=1.2))
def line4(pts, color="#333", lw=1.2):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=color, lw=lw)

fbox4(13.3, "输入: 滤波后 V / I / T", C_MCU); varrow4(12.87, 12.7)
diamond4(11.9, "T≥60℃ 或 V≥21V 或 I≥3.3A ?\n(危险级超限)")
line4([(CX, 13.3-0.85-1.3+0.85), (CX, 13.2)])  # 顶端进
varrow4(11.9-1.3, 10.9)
ax.text(CX+0.2, 10.75, "是", fontsize=9, color="#d62728")
diamond4(10.2, "连续 5 次采样均超限? (防抖)")
varrow4(10.2-1.3, 8.6)
ax.text(CX+0.2, 8.45, "是", fontsize=9)
fbox4(8.1, "切断级：继电器断开低压负载\n蜂鸣器长响，状态闭锁", C_ACT)
varrow4(7.67, 7.5)
fbox4(7.0, "等待温度回落且人工恢复\n(防热振荡反复通断)")
line4([(CX, 6.57), (CX, 6.3)]); varrow4(6.3, 6.1, color="#ffffff00")
# 左侧: 否 → 报警级
ax.text(1.7, 11.9, "否", fontsize=9)
line4([(5-2.8, 11.9), (1.5, 11.9), (1.5, 6.0)], color="#ff7f0e")
diamond4(6.0, "T ≥ 45℃ (仅超温)?", w=4.6, h=1.1, fs=9, cx=4.6)
ax.add_patch(FancyArrowPatch((1.5, 6.0), (2.3, 6.0), arrowstyle="-|>",
                             mutation_scale=12, color="#ff7f0e", lw=1.2))
varrow4(5.45, 5.2, x=4.6, color="#333")
ax.text(4.75, 5.3, "是", fontsize=9)
fbox4(4.7, "报警级：蜂鸣器响\n继电器保持吸合", C_UI, w=4.6, cx=4.6)
varrow4(4.27, 4.0, x=4.6)
diamond4(3.3, "超限解除?", w=3.4, h=1.0, fs=9, cx=4.6)
ax.text(2.7, 3.45, "是", fontsize=9)
fbox4(1.9, "恢复 NORMAL：蜂鸣器停止", "#dcfce7", w=4.6, cx=4.6)
varrow4(2.8, 2.35, x=4.6)
ax.text(6.6, 3.3, "否: 保持报警状态", fontsize=9)
line4([(6.3, 3.3), (7.2, 3.3), (7.2, 1.9), (6.95, 1.9)], color="#333")
ax.add_patch(FancyArrowPatch((6.95, 1.9), (6.93, 1.9), arrowstyle="-|>",
                             mutation_scale=12, color="#333", lw=1.2))
# 右侧否(防抖不足): 回 NORMAL
ax.text(8.3, 10.2, "否(毛刺)", fontsize=9)
line4([(7.8, 10.2), (9.6, 10.2), (9.6, 1.9), (7.35, 1.9)], color="#333")
ax.text(9.75, 6.0, "防抖未确认→不动作", rotation=90, fontsize=8.5, va="center", color="#555")
ax.set_title("图 4-2  保护逻辑流程图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_保护逻辑流程图.png", dpi=150); plt.close(fig)

print("v2 示意图已生成")
