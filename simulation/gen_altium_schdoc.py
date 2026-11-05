"""生成 STM32 充电监控系统的 Altium 原生原理图（.SchDoc, Protel ASCII v5.0）

设计依据（与固件严格一致）：
  firmware/Core/Inc/main.h      引脚宏、阈值
  firmware/Core/Inc/ina219.h    分流 0.1R / Cal=4096 / LSB=0.8mA
  DESIGN.md                     电源树与保护逻辑

输出：hardware/charge_monitor.SchDoc
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from altium_schdoc import Sch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "hardware", "charge_monitor.SchDoc")

STUB = 8.0
PINLEN = 6.0
CHW = 2.0          # 字符宽近似 (mm) @ 10pt

s = Sch(width_mm=594, height_mm=420,
        title="STM32 Charge Monitor", rev="A",
        sheetname="ChargeMonitor", xzones=10, yzones=7)

pins = {}           # (ref, pin) -> (x, y, side)
bodies = []         # (ref, x0, y0, x1, y1)
texts = []          # (label, x0, y0, x1, y1)


def place(ref, libref, x, y, w, h, spec, value="", footprint="", vpos=None):
    """放置元件：位号在体上方，值在体右侧（窄）或体中央（宽）。"""
    ci, hot = s.component(libref, x, y, w, h, ref, comment="",
                          footprint=footprint, pins=spec, auto_labels=False)
    for pname, (hx, hy, side) in hot.items():
        pins[(ref, pname)] = (hx, hy, side)

    if w <= 10:                      # 竖直两脚件：位号放体左上、右对齐
        s.designator(ci, x - 1.0, y + h + 2.4, justification=2)
        texts.append((ref, x - 1.0 - CHW * len(ref), y + h + 2.0,
                      x - 1.0, y + h + 6.6))
    else:
        s.designator(ci, x, y + h + 2.4)
        texts.append((ref, x, y + h + 2.0, x + CHW * len(ref) + 1.0, y + h + 6.6))

    if value:
        mode = vpos or ("inside" if w >= 60 else "right")
        if mode == "inside":
            s.param(ci, "Comment", value, x + w / 2, y + h / 2 - 1.6,
                    justification=1)
            half = CHW * len(value) / 2
            texts.append((ref + ".val", x + w / 2 - half, y + h / 2 - 4.2,
                          x + w / 2 + half, y + h / 2 + 0.4))
        elif mode == "above":
            vx = x + CHW * len(ref) + 3.0
            s.param(ci, "Comment", value, vx, y + h + 2.4)
            texts.append((ref + ".val", vx, y + h + 2.0,
                          vx + CHW * len(value), y + h + 6.6))
        elif mode == "below":
            s.param(ci, "Comment", value, x, y - 5.4)
            texts.append((ref + ".val", x, y - 5.8,
                          x + CHW * len(value), y - 1.8))
        else:
            s.param(ci, "Comment", value, x + w + 2.5, y + h / 2 - 1.6)
            texts.append((ref + ".val", x + w + 2.5, y + h / 2 - 4.2,
                          x + w + 2.5 + CHW * len(value), y + h / 2 + 0.4))

    bodies.append((ref, x, y, x + w, y + h))
    return hot


# ============================ ① 电源输入 / 稳压 ============================
place("J1", "USB_5V", 30, 345, 22, 30, [
    (1, "VBUS", "R", 24, PINLEN, 7),
    (2, "GND", "B", 11, PINLEN, 7),
], value="USB 5V")   # 仅给 MCU/LDO 与继电器线圈供电，不参与被测电流回路

# 被测直流输入（快充头/电池侧，5–20V）与 MCU 供电 USB 5V 是两条独立回路。
# 负端必须与 MCU 共地（INA219 的 VBUS 为对 GND 的单端测量），且只限隔离低压直流。
place("J6", "DC_IN", 30, 296, 22, 26, [
    (1, "V+", "L", 18, PINLEN, 7),
    (2, "V-", "L", 8, PINLEN, 7),
], value="DC IN 5-20V", vpos="below")

place("C1", "CAP", 80, 340, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="10uF")

place("U3", "AMS1117-3.3", 112, 338, 40, 28, [
    (1, "VI", "L", 15, PINLEN, 7),
    (2, "GND", "B", 20, PINLEN, 7),
    (3, "VO", "R", 15, PINLEN, 7),
], value="AMS1117-3.3", vpos="above")

place("C2", "CAP", 182, 340, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="100nF")

# ============================ ② 电流采样 ============================
place("R1", "R_SHUNT", 226, 372, 22, 7, [
    (1, "1", "L", 3.5, PINLEN, 4),
    (2, "2", "R", 3.5, PINLEN, 4),
], value="0.1R/2W", vpos="below")   # 2.5A 时 I^2R=0.625W，1W 余量不足

# INA219 共 9 个有效引脚；VBUS 必须接入被测母线，否则总线电压寄存器无意义。
# VBUS 取分流电阻"电源侧"(VIN_DC) 而非负载侧(SHUNT_N)：继电器断开后仍能
# 读到真实输入电压，避免"断开->读到0V->判定安全->自动重合闸"的振荡。
place("U2", "INA219", 274, 330, 50, 40, [
    (1, "VIN+", "L", 34, PINLEN, 4),
    (2, "VIN-", "L", 21, PINLEN, 4),
    (3, "VBUS", "L", 8, PINLEN, 4),
    (4, "SDA", "R", 28, PINLEN, 2),
    (5, "SCL", "R", 14, PINLEN, 2),
    (6, "VS", "T", 26, PINLEN, 7),
    (7, "GND", "B", 12, PINLEN, 7),
    (8, "A0", "B", 25, PINLEN, 4),
    (9, "A1", "B", 38, PINLEN, 4),
], value="INA219")

# ============================ ③ 显示 + I2C 上拉 ============================
place("R3", "R", 396, 366, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="4.7k")

place("R2", "R", 430, 366, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="4.7k")

place("J2", "OLED", 486, 342, 30, 36, [
    (1, "GND", "L", 30, PINLEN, 7),
    (2, "VCC", "L", 22, PINLEN, 7),
    (3, "SCL", "L", 14, PINLEN, 2),
    (4, "SDA", "L", 6, PINLEN, 2),
], value="SSD1306", vpos="right")

# ============================ ④ 主控 ============================
place("U1", "STM32F103C8T6", 150, 185, 100, 130, [
    (1, "PA0", "L", 115, PINLEN, 2),
    (2, "PA1", "L", 102, PINLEN, 2),
    (3, "PA2", "L", 89, PINLEN, 2),
    (4, "PA3", "L", 76, PINLEN, 2),
    (5, "PB6", "L", 57, PINLEN, 2),
    (6, "PB7", "L", 44, PINLEN, 2),
    (7, "OSC_IN", "L", 25, PINLEN, 2),
    (8, "OSC_OUT", "L", 12, PINLEN, 2),
    (9, "PA9", "R", 115, PINLEN, 2),
    (10, "PA10", "R", 102, PINLEN, 2),
    (11, "PA13", "R", 89, PINLEN, 2),
    (12, "PA14", "R", 76, PINLEN, 2),
    (13, "NRST", "R", 58, PINLEN, 2),
    (14, "BOOT0", "R", 45, PINLEN, 2),
    (15, "VDD", "T", 25, PINLEN, 7),
    (16, "VDDA", "T", 50, PINLEN, 7),
    (17, "VBAT", "T", 75, PINLEN, 7),
    (18, "VSS", "B", 25, PINLEN, 7),
    (19, "VSSA", "B", 75, PINLEN, 7),
], value="STM32F103C8T6")

place("C3", "CAP", 302, 238, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="100nF")

place("R8", "R", 272, 176, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="10k")

# ============================ ⑤ NTC ============================
place("R4", "R", 36, 262, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="10k")

place("RT1", "NTC", 36, 196, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="NTC 10k")

# ============================ ⑥ 蜂鸣器 ============================
place("R5", "R", 338, 258, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="1k")

place("Q1", "S8050", 382, 250, 14, 14, [
    (1, "B", "L", 6, PINLEN, 4),
    (2, "C", "T", 9, PINLEN, 4),
    (3, "E", "B", 9, PINLEN, 4),
], value="S8050")

place("BZ1", "BUZZER", 414, 252, 22, 18, [
    (1, "+", "T", 15, PINLEN, 4),
    (2, "-", "B", 11, PINLEN, 4),
], value="Buzzer")

# ============================ ⑦ 继电器 ============================
place("R6", "R", 338, 170, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="1k")

# MCU 复位/未初始化时 PA2 为高阻输入，10k 下拉把 Q2 基极拉到确定低电平，
# 保证继电器在复位与上电瞬间硬件默认断开（fail-safe），不依赖软件初始化顺序。
place("R9", "R", 360, 120, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="10k")

place("Q2", "S8050", 380, 164, 14, 14, [
    (1, "B", "L", 6, PINLEN, 4),
    (2, "C", "T", 9, PINLEN, 4),
    (3, "E", "B", 9, PINLEN, 4),
], value="S8050")

place("D1", "D_1N4148", 414, 196, 8, 16, [
    (1, "K", "T", 4, PINLEN, 4),
    (2, "A", "B", 4, PINLEN, 4),
], value="1N4148")

place("K1", "RELAY", 444, 150, 40, 34, [
    (1, "A1", "L", 26, PINLEN, 7),
    (2, "A2", "L", 10, PINLEN, 7),
    (3, "COM", "R", 24, PINLEN, 4),
    (4, "NO", "R", 10, PINLEN, 4),
], value="5V Relay", vpos="below")

place("J4", "LOAD", 552, 152, 22, 26, [
    (1, "L+", "L", 18, PINLEN, 4),
    (2, "L-", "L", 8, PINLEN, 4),
], value="Load")

# ============================ ⑧ ESP8266 / SWD ============================
place("J3", "ESP-01", 480, 62, 30, 50, [
    (1, "VCC", "L", 42, PINLEN, 7),
    (2, "GND", "L", 36, PINLEN, 7),
    (3, "TX", "L", 30, PINLEN, 2),
    (4, "RX", "L", 24, PINLEN, 2),
    (5, "CH_PD", "L", 18, PINLEN, 2),
    (6, "RST", "L", 12, PINLEN, 2),
    (7, "GPIO0", "L", 6, PINLEN, 2),
], value="ESP-01", vpos="right")

place("R7", "R", 410, 120, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="10k")

place("J5", "SWD", 36, 96, 20, 36, [
    (1, "3V3", "L", 30, PINLEN, 7),
    (2, "SWDIO", "L", 23, PINLEN, 2),
    (3, "SWCLK", "L", 16, PINLEN, 2),
    (4, "NRST", "L", 9, PINLEN, 2),
    (5, "GND", "L", 2, PINLEN, 7),
], value="SWD 5P")

# ============================ ⑨ 晶振 ============================
place("Y1", "XTAL", 172, 104, 20, 10, [
    (1, "1", "L", 5, PINLEN, 4),
    (2, "2", "R", 5, PINLEN, 4),
], value="8MHz", vpos="below")

place("C4", "CAP", 148, 74, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="22pF")

place("C5", "CAP", 218, 74, 8, 16, [
    (1, "1", "T", 4, PINLEN, 4),
    (2, "2", "B", 4, PINLEN, 4),
], value="22pF")

# 晶振两侧电容用实线连到晶振引脚（不再叠两个同名标号）
NO_LABEL = {("C4", "1"), ("C5", "1")}
EXTRA_WIRES = [
    [(152, 96), (152, 109), (158, 109)],    # C4.1 热点 -> Y1.1 标号点
    [(222, 96), (222, 109), (206, 109)],    # C5.1 热点 -> Y1.2 标号点
]

# ============================ 网络表 ============================
PWR = {"+5V", "+3V3", "GND"}

nets = {
    # ① MCU/逻辑供电：仅 USB 5V -> LDO 3V3 与继电器线圈，不串入分流电阻
    "+5V": [("J1", "VBUS"), ("U3", "VI"), ("C1", "1"), ("K1", "A1"), ("D1", "K")],
    # ② 被测直流回路（5–20V）：只经 R1 分流 -> K1 触点 -> 负载；INA219 在此采样
    "VIN_DC": [("J6", "V+"), ("R1", "1"), ("U2", "VIN+"), ("U2", "VBUS")],
    "+3V3": [("U3", "VO"), ("C2", "1"), ("C3", "1"), ("U2", "VS"),
             ("U1", "VDD"), ("U1", "VDDA"), ("U1", "VBAT"),
             ("R2", "1"), ("R3", "1"), ("R4", "1"),
             ("J2", "VCC"), ("BZ1", "+"), ("J3", "VCC"),
             ("J3", "GPIO0"), ("J5", "3V3"), ("R7", "1")],
    "GND": [("J1", "GND"), ("U3", "GND"), ("C1", "2"), ("C2", "2"),
            ("C3", "2"), ("U2", "GND"), ("U2", "A0"), ("U2", "A1"),
            ("U1", "VSS"), ("U1", "VSSA"), ("C4", "2"), ("C5", "2"),
            ("J2", "GND"), ("Q1", "E"), ("Q2", "E"), ("J3", "GND"),
            ("J4", "L-"), ("J5", "GND"), ("RT1", "2"), ("R8", "2"),
            ("J6", "V-"), ("R9", "2")],

    "SHUNT_N": [("R1", "2"), ("U2", "VIN-"), ("K1", "COM")],
    "LOAD_P": [("K1", "NO"), ("J4", "L+")],
    "NTC_ADC": [("U1", "PA0"), ("R4", "2"), ("RT1", "1")],

    "I2C_SCL": [("U1", "PB6"), ("U2", "SCL"), ("J2", "SCL"), ("R3", "2")],
    "I2C_SDA": [("U1", "PB7"), ("U2", "SDA"), ("J2", "SDA"), ("R2", "2")],
    "BUZ_CTRL": [("U1", "PA1"), ("R5", "1")],
    "RELAY_CTRL": [("U1", "PA2"), ("R6", "1"), ("R9", "1")],
    "ESP_EN": [("U1", "PA3"), ("J3", "CH_PD")],
    "UART_TX": [("U1", "PA9"), ("J3", "RX")],
    "UART_RX": [("U1", "PA10"), ("J3", "TX")],
    "ESP_RST": [("J3", "RST"), ("R7", "2")],
    "OSC_IN": [("U1", "OSC_IN"), ("Y1", "1"), ("C4", "1")],
    "OSC_OUT": [("U1", "OSC_OUT"), ("Y1", "2"), ("C5", "1")],
    "NRST": [("U1", "NRST"), ("J5", "NRST")],
    "BOOT0": [("U1", "BOOT0"), ("R8", "1")],
    "BUZ_B": [("R5", "2"), ("Q1", "B")],
    "BUZ_C": [("Q1", "C"), ("BZ1", "-")],
    "RELAY_B": [("R6", "2"), ("Q2", "B")],
    "RELAY_C": [("Q2", "C"), ("K1", "A2"), ("D1", "A")],

    "SWDIO": [("U1", "PA13"), ("J5", "SWDIO")],
    "SWCLK": [("U1", "PA14"), ("J5", "SWCLK")],
}

PORT_ORI = {"L": 2, "R": 0, "T": 1, "B": 3}
LABEL_JUST = {"L": 0, "R": 0, "T": 0, "B": 0}


def stub_point(x, y, side, d=STUB):
    return {"L": (x - d, y), "R": (x + d, y),
            "T": (x, y + d), "B": (x, y - d)}[side]


used = set()
for net, members in nets.items():
    for ref, pname in members:
        key = (ref, pname)
        if key in used:
            continue
        if key not in pins:
            raise SystemExit("UNKNOWN PIN %s.%s" % (ref, pname))
        used.add(key)
        x, y, side = pins[key]
        ex, ey = stub_point(x, y, side)
        s.wire([(x, y), (ex, ey)])
        if key in NO_LABEL:
            continue
        if net in PWR:
            s.powerport(ex, ey, net, style=1, orientation=PORT_ORI[side])
        else:
            s.netlabel(ex, ey, net, orientation=0,
                       justification=LABEL_JUST[side])

for pts in EXTRA_WIRES:
    s.wire(pts)

# ============================ 说明文字 ============================
NOTES = [
    (30, 316, "POWER: USB 5V -> AMS1117-3.3 -> 3V3"),
    (226, 396, "SHUNT 0.1R / INA219 (I2C 0x40)"),
    (150, 157, "MCU STM32F103C8T6 @ 8MHz HSE"),
    (36, 300, "TEMPERATURE: 10k pull-up + NTC B3950"),
    (338, 300, "ALARM: low-side NPN drives buzzer"),
    (338, 130, "RELAY: cuts low-voltage load on fault"),
    (430, 34, "IOT: ESP-01 AT firmware (optional)"),
    (36, 62, "SWD debug port"),
]
for (x, y, t) in NOTES:
    s.text(x, y, t, font=4)

s.text(30, 16, "STM32 CHARGE MONITOR   |   SHEET 1/1   |   CM-SCH-02   |   REV.A")

# ============================ 自检 ============================
def hit(a, b, pad=0.0):
    return not (a[3] + pad <= b[1] or b[3] + pad <= a[1] or
                a[4] + pad <= b[2] or b[4] + pad <= a[2])


problems = []
for i in range(len(bodies)):
    for j in range(i + 1, len(bodies)):
        a, b = bodies[i], bodies[j]
        if hit((a[0], a[1], a[2], a[3], a[4]),
               (b[0], b[1], b[2], b[3], b[4]), pad=2.0):
            problems.append("BODY OVERLAP: %s <-> %s" % (a[0], b[0]))

for (name, x0, y0, x1, y1) in texts:
    owner = name.split(".")[0]
    for (ref, bx0, by0, bx1, by1) in bodies:
        if ref == owner:
            continue
        if not (x1 <= bx0 or bx1 <= x0 or y1 <= by0 or by1 <= y0):
            problems.append("TEXT ON BODY: %s -> %s" % (name, ref))

# ---- 电气完整性：每个符号引脚必须恰好归属一个网络 ----
# 曾经漏接 INA219 的 VBUS 引脚而未被发现，因此把覆盖检查固化为生成期断言。
net_of = {}
for netname, members in nets.items():
    for key in members:
        if key not in pins:
            problems.append("NET REFERENCES MISSING PIN: %s.%s" % key)
        if key in net_of:
            problems.append("PIN IN MULTIPLE NETS: %s.%s (%s / %s)" %
                            (key[0], key[1], net_of[key], netname))
        net_of[key] = netname
for key in pins:
    if key not in net_of:
        problems.append("UNCONNECTED PIN: %s.%s" % key)
for netname, members in nets.items():
    if netname not in PWR and len(members) < 2:
        problems.append("SINGLE-PIN NET: %s" % netname)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
s.save(OUT)
print("written:", OUT)
print("records:", len(s.recs), "components:", len(bodies), "nets:", len(nets))
if problems:
    print("---- LAYOUT WARNINGS (%d) ----" % len(problems))
    for p in problems[:40]:
        print("  ", p)
else:
    print("layout check: OK")
