# -*- coding: utf-8 -*-
"""生成论文示意图: 系统架构图 / 硬件连接图 / 主程序流程图 / 保护逻辑流程图 / OLED界面"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
OUT = r"E:\23计科1+202308324143+沈炜丹\毕业设计-STM32智能充电监控显示系统\figures"

C_MCU, C_SENSOR, C_ACT, C_UI, C_IO = "#dbeafe", "#dcfce7", "#fee2e2", "#fef9c3", "#f3e8ff"

def box(ax, x, y, w, h, text, fc="#ffffff", fs=11, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                fc=fc, ec="#333333", lw=1.2))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")

def arrow(ax, x1, y1, x2, y2, text="", color="#333333", fs=9):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=14, color=color, lw=1.3))
    if text:
        ax.text((x1+x2)/2, (y1+y2)/2 + 0.06, text, ha="center", fontsize=fs, color=color)

# ================================================================
# 图1: 系统总体架构框图
# ================================================================
fig, ax = plt.subplots(figsize=(10, 6.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

box(ax, 0.3, 7.6, 1.8, 1.3, "60W PD\n快充头", C_SENSOR, bold=True)
box(ax, 0.3, 5.2, 1.8, 1.3, "受控负载\n(充电设备)", C_SENSOR, bold=True)
box(ax, 3.2, 5.4, 2.0, 1.0, "继电器模块\n(低压回路)", C_ACT)
box(ax, 3.2, 7.7, 2.0, 1.0, "INA219\n电流/电压采集", C_SENSOR)
box(ax, 6.1, 6.0, 2.2, 2.6, "STM32F103C8T6\n主控\n(采集/滤波/判定)", C_MCU, fs=12, bold=True)
box(ax, 3.2, 2.9, 2.0, 1.0, "NTC 热敏电阻\n(外壳测温)", C_SENSOR)
box(ax, 6.1, 2.9, 2.2, 1.0, "0.96寸 OLED\n(SSD1306)", C_UI)
box(ax, 6.1, 1.2, 2.2, 1.0, "蜂鸣器", C_ACT)
box(ax, 3.2, 0.8, 2.0, 1.0, "ESP8266\n(可选/预留)", C_IO)

arrow(ax, 2.1, 8.25, 3.2, 8.2, "输出")
arrow(ax, 5.2, 8.0, 6.1, 7.6, "I2C1")
arrow(ax, 5.2, 5.9, 6.1, 6.6, "I2C1")
arrow(ax, 5.2, 8.6, 2.4, 8.6, "")
arrow(ax, 2.4, 8.6, 2.4, 6.5, "")
ax.text(2.3, 7.4, "供电\n(20V/3A)", fontsize=9, ha="right")
arrow(ax, 4.2, 6.4, 4.2, 6.2, "")
arrow(ax, 4.2, 5.4, 2.1, 5.85, "通/断")
arrow(ax, 4.2, 3.9, 5.4, 6.0, "ADC1_IN0")
arrow(ax, 6.1, 3.4, 5.2, 3.4, "I2C1")
arrow(ax, 6.1, 1.7, 5.2, 3.1, "GPIO")
arrow(ax, 6.1, 1.4, 4.4, 1.3, "USART1")
ax.text(4.55, 4.4, "温度换算", fontsize=9, color="#555555")
ax.set_title("图 2-1  系统总体架构框图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_架构图.png", dpi=150); plt.close(fig)

# ================================================================
# 图2: 硬件连接图
# ================================================================
fig, ax = plt.subplots(figsize=(10, 6.8))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

box(ax, 3.8, 3.9, 2.4, 2.4, "STM32F103C8T6\n(Blue Pill)", C_MCU, fs=12, bold=True)
# 左侧引脚标注
for i, (pin, tgt) in enumerate([("PB6/PB7 (I2C1)", "OLED+INA219"),
                                ("PA0 (ADC1)", "NTC分压"),
                                ("PA1", "蜂鸣器"),
                                ("PA2", "继电器IN"),
                                ("PA9/PA10", "ESP8266")]):
    ax.text(3.7, 5.9 - i*0.52, pin, fontsize=9, ha="right", color="#1d4ed8")
box(ax, 0.4, 6.9, 2.2, 0.9, "OLED 0.96\"\nSSD1306", C_UI)
box(ax, 0.4, 5.4, 2.2, 0.9, "INA219\n(0.1Ω分流)", C_SENSOR)
box(ax, 0.4, 3.9, 2.2, 0.9, "NTC 10k\n+10k上拉", C_SENSOR)
box(ax, 0.4, 2.4, 2.2, 0.9, "有源蜂鸣器\n(S8050驱动)", C_ACT)
box(ax, 0.4, 0.9, 2.2, 0.9, "继电器模块\n5V单路", C_ACT)
box(ax, 7.6, 0.9, 2.0, 0.9, "ESP8266-01S", C_IO)
box(ax, 7.6, 5.4, 2.0, 1.2, "60W PD快充头\n输出 20V/3A", C_SENSOR, bold=True)
box(ax, 7.6, 3.2, 2.0, 1.2, "低压负载\n(被充电设备)", "#ffffff")

arrow(ax, 2.6, 7.35, 4.2, 6.3, "SCL/SDA")
arrow(ax, 2.6, 5.85, 3.9, 6.0, "SCL/SDA")
arrow(ax, 2.6, 4.35, 3.8, 4.6, "采样点")
arrow(ax, 2.6, 2.85, 3.8, 4.0, "PA1")
arrow(ax, 2.6, 1.35, 3.8, 3.9, "PA2")
arrow(ax, 5.9, 4.1, 7.6, 1.5, "TX/RX")
arrow(ax, 8.6, 2.1, 8.6, 3.2, "20V输出")
arrow(ax, 8.6, 4.4, 8.6, 5.4, "")
# INA219 串接于快充输出与负载之间
arrow(ax, 7.6, 5.7, 2.4, 5.7, "输出串接")
arrow(ax, 2.6, 6.2, 7.6, 3.6, "负载串接")
ax.text(5.0, 6.0, "INA219 串接于快充输出与负载之间", fontsize=9, color="#555555")
ax.set_title("图 3-1  系统硬件连接图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_硬件连接图.png", dpi=150); plt.close(fig)

# ================================================================
# 图3: 主程序流程图
# ================================================================
fig, ax = plt.subplots(figsize=(7.2, 11))
ax.set_xlim(0, 10); ax.set_ylim(0, 16); ax.axis("off")

def fbox(y, text, fc="#ffffff", fs=10.5):
    box(ax, 2.6, y, 4.8, 0.9, text, fc, fs)

def diamond(y, text, w=4.4, h=1.3, fs=10):
    ax.add_patch(plt.Polygon([[5, y+h], [5+w/2, y], [5, y-h], [5-w/2, y]],
                             closed=True, fc="#fff7ed", ec="#333333", lw=1.2))
    ax.text(5, y, text, ha="center", va="center", fontsize=fs)

fbox(14.6, "上电复位 / 系统时钟 72MHz", C_MCU)
fbox(13.4, "初始化 GPIO / I2C1 / ADC1 / USART1")
fbox(12.2, "INA219 标定、OLED 自检、保护初值")
arrow(ax, 5, 14.6, 5, 14.3); arrow(ax, 5, 13.4, 5, 13.1); arrow(ax, 5, 12.2, 5, 11.6)
fbox(10.7, "开启 INA219 连续转换模式")
arrow(ax, 5, 10.7, 5, 10.1)

# 主循环
box(ax, 1.0, 8.3, 0.02, 0.02, "")  # dummy
ax.plot([5, 5], [10.1, 9.9], color="#333", lw=1.3)
diamond(9.2, "100ms 到?")
arrow(ax, 5, 8.5, 5, 8.2)
fbox(7.3, "读取 INA219: V / I / P\nNTC: ADC 采样→B方程→温度")
arrow(ax, 5, 7.3, 5, 7.0)
fbox(6.1, "滑动窗口均值滤波 (窗口=8)")
arrow(ax, 5, 6.1, 5, 5.8)
fbox(4.9, "保护逻辑判定 (阈值+防抖)\n控制蜂鸣器 / 继电器", C_ACT)
arrow(ax, 5, 4.9, 5, 4.6)
diamond(3.7, "500ms 到?")
arrow(ax, 5, 3.05, 5, 2.8)
fbox(1.9, "OLED 界面刷新\n(电压/电流/功率/温度/状态)", C_UI)
arrow(ax, 5, 1.9, 5, 1.6)
diamond(0.9, "1000ms 到?")

# 循环回边
ax.annotate("", xy=(9.6, 9.2), xytext=(7.4, 0.9),
            arrowprops=dict(arrowstyle="-", color="#333", lw=1.2))
ax.annotate("", xy=(9.6, 0.9), xytext=(7.4, 0.9),
            arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.2))
ax.plot([7.4, 9.6], [0.9, 0.9], color="#333", lw=1.2)
ax.plot([9.6, 9.6], [0.9, 9.2], color="#333", lw=1.2)
ax.plot([9.6, 6.6], [9.2, 9.2], color="#333", lw=1.2)
ax.add_patch(FancyArrowPatch((6.6, 9.2), (6.35, 9.2), arrowstyle="-|>",
                             mutation_scale=14, color="#333", lw=1.2))
ax.text(9.85, 5.0, "循环", rotation=90, fontsize=10, va="center")
ax.text(6.55, 3.7, "是→刷新", fontsize=9)
ax.text(6.55, 0.55, "是→上传ESP8266", fontsize=9)

ax.set_title("图 4-1  主程序流程图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_主程序流程图.png", dpi=150); plt.close(fig)

# ================================================================
# 图4: 保护逻辑流程图
# ================================================================
fig, ax = plt.subplots(figsize=(7.5, 10))
ax.set_xlim(0, 10); ax.set_ylim(0, 14); ax.axis("off")

def fbox2(y, text, fc="#ffffff", fs=10.5, w=5.2):
    box(ax, (10-w)/2, y, w, 0.85, text, fc, fs)

def diamond2(y, text, w=5.4, h=1.25, fs=9.5):
    ax.add_patch(plt.Polygon([[5, y+h], [5+w/2, y], [5, y-h], [5-w/2, y]],
                             closed=True, fc="#fff7ed", ec="#333", lw=1.2))
    ax.text(5, y, text, ha="center", va="center", fontsize=fs)

fbox2(12.8, "输入: V / I / T (滤波后)", C_MCU)
arrow(ax, 5, 12.8, 5, 12.5)
diamond2(11.6, "T ≥ 60℃ 或 V ≥ 21V\n或 I ≥ 3.3A ?")
ax.text(7.8, 11.6, "是", fontsize=10, color="#d62728")
arrow(ax, 7.7, 11.6, 8.4, 11.6)
box(ax, 8.4, 8.6, 1.4, 6.0, "", "#ffffff", 1)  # 右侧占位(白)
ax.plot([8.4, 8.4], [11.6, 10.9], color="#d62728", lw=1.3)
diamond2(9.8, "连续 5 次超限? (防抖)", w=5.4)
arrow(ax, 5, 10.35, 5, 10.55)
ax.text(2.6, 10.95, "是", fontsize=10)
ax.plot([5, 5], [11.6-1.25, 10.55], color="#333", lw=1.3)
arrow(ax, 5, 9.15, 5, 8.9)
fbox2(8.0, "危险级: 继电器切断负载\n蜂鸣器长响, 进入闭锁", C_ACT)
arrow(ax, 5, 8.0, 5, 7.7)
fbox2(6.8, "状态=CUTOFF, 等待人工恢复")
ax.plot([8.4, 8.4], [9.8, 5.2], color="#333", lw=0)  # skip

# 左支: 否 → 仅温度报警级
ax.text(2.2, 11.9, "否(仅超温≥45℃)", fontsize=9)
ax.plot([2.3, 2.3], [11.6, 10.0], color="#333", lw=1.2)
ax.plot([2.3, 5-2.7], [10.0, 10.0], color="#333", lw=1.2)
diamond2(9.0, "T ≥ 45℃ ? (且未超危险级)", w=4.6, h=1.1, fs=9)
arrow(ax, 5, 10.55, 5, 10.1)
ax.plot([5, 5], [10.55, 10.1], color="#333", lw=1.3)
arrow(ax, 5, 7.9, 5, 7.9)
ax.plot([2.3, 2.3], [10.0, 6.6], color="#333", lw=1.2)
ax.plot([2.3, 2.4], [6.6, 6.6], color="#333", lw=1.2)
fbox2(5.0, "警告级: 蜂鸣器响, 继电器保持", C_UI, w=4.6)
ax.plot([2.3, 2.7], [5.4, 5.4], color="#333", lw=1.2)
ax.plot([2.3, 2.3], [6.6, 5.4], color="#333", lw=1.2)
diamond2(3.4, "超限解除?", w=3.6, h=1.0, fs=9)
arrow(ax, 4.4, 4.95, 4.4, 4.4)
ax.plot([3.2, 3.2], [5.0, 4.4], color="#333", lw=1.2)
fbox2(1.9, "恢复: 蜂鸣器停, 返回 NORMAL", "#dcfce7", w=4.6)
ax.plot([3.2, 3.2], [2.75, 2.4], color="#333", lw=1.2)
arrow(ax, 3.2, 2.4, 3.2, 2.3)
ax.text(1.0, 3.4, "是", fontsize=9)
ax.text(5.6, 3.4, "否:保持报警", fontsize=9)
ax.plot([5.2, 5.6], [3.4, 3.4], color="#333", lw=1.2)
ax.plot([5.6, 5.6], [3.4, 1.0], color="#333", lw=1.2)
ax.plot([5.6, 7.9], [1.0, 1.0], color="#333", lw=1.2)
ax.set_title("图 4-2  保护逻辑流程图", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_保护逻辑流程图.png", dpi=150); plt.close(fig)

# ================================================================
# 图5: OLED 显示界面布局示意 (1:1 像素放大)
# ================================================================
# 用 matplotlib 直接渲染界面示意
fig, ax = plt.subplots(figsize=(8.5, 5.2))
ax.set_xlim(0, 128); ax.set_ylim(0, 64); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 128, 64, fc="#000000", ec="#333333", lw=2))

def oled_text(x, y, s, size=7, color="white", weight="normal", ha="left"):
    ax.text(x, y, s, fontsize=size, color=color, family="Consolas",
            weight=weight, ha=ha, va="center")

oled_text(4, 60, "CHARGE MONITOR", 7, weight="bold")
oled_text(124, 60, "P:60.0W", 7, ha="right")
oled_text(4, 48, "20.00", 15, weight="bold")     # 电压大字
oled_text(52, 48, "V", 10)
oled_text(64, 48, "3.000", 15, weight="bold")    # 电流大字
oled_text(124, 48, "A", 10, ha="right")
ax.plot([0, 128], [41, 41], color="#444444", lw=0.8)
oled_text(4, 34, "TEMP: 38.5 C", 9)
oled_text(4, 25, "ST   : NORMAL", 9)
ax.plot([0, 128], [20, 20], color="#444444", lw=0.8)
oled_text(4, 14, "[RELAY ON ] [INA OK]", 8, color="#7dd3fc")
oled_text(4, 5, "2000-01-01 12:00  UPLOAD:OK", 6.5, color="#86efac")
ax.set_title("图 4-3  OLED 显示界面布局（128×64）", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_OLED界面.png", dpi=150); plt.close(fig)

print("示意图已全部生成 ->", OUT)
