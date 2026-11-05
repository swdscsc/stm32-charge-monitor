"""Altium ASCII SchDoc 生成库（Protel for Windows - Schematic Capture Ascii v5.0）

从 Altium 真实导出的 ASCII SchDoc 反推出的方言要点：
  * 首行  |HEADER=Protel for Windows - Schematic Capture Ascii File Version 5.0|WEIGHT=n
  * 每条记录 '|RECORD=' 开头、尾随 '|' 结束，各占一行
  * 坐标单位 = 10 mil；小数部分另存 <NAME>_FRAC（1e-5 单位）
  * OWNERINDEX 为 0 基记录序号（sheet 记录 = 0，header 不计）
  * 矩形是 RECORD=10（LOCATION + CORNER），不是 13
  * 导线 RECORD=27（LOCATIONCOUNT + X1..Xn/Y1..Yn）
  * 引脚 RECORD=2；LOCATION 是引脚根部(贴元件体侧)，电气热点 =
    LOCATION + 方向 × PINLENGTH；方向由 PINCONGLOMERATE 低 2 位给出
    (0=+X / 1=+Y / 2=-X / 3=-Y，Y 轴向上)，0x38 = 显示标志
  * 导线必须接在电气热点上；接在 LOCATION 会让末端标号被判 Floating
  * 网络标号 RECORD=25，电源端口 RECORD=17，连接点 RECORD=29，文本 RECORD=4
"""
import math

COORD_PER_MM = 100.0 / 25.4      # 1 坐标单位 = 10 mil = 0.254 mm
FRAC = 100000

FONT_MAIN = 1      # Times New Roman 10 —— 位号 / 注释
FONT_PIN = 2       # Arial 9          —— 引脚名
FONT_LABEL = 3     # Arial 9          —— 网络标号 / 电源端口
FONT_NOTE = 4      # Arial 7          —— 说明文字

# 两脚无源件的引脚名（1/2/K/A）在原理图上没有信息量，Altium 惯例是隐藏，
# 只显示引脚号；隐藏后也避免了竖排引脚名与位号打架。
PASSIVE_LIBS = {"CAP", "R", "R_SHUNT", "NTC", "XTAL", "D_1N4148"}
HIDE_PIN_NAMES = True
HIDDEN_PIN_NAMES = {"1", "2", "K", "A"}


def mm(v):
    """毫米 -> (整数坐标单位, 小数部分)。

    坐标一律量化到整数单位(0.254 mm)，让所有引脚/导线落在 1 单位栅格上，
    Altium 编译时就不会再报 "Off grid Pin"。
    """
    u = v * COORD_PER_MM
    i = int(math.floor(u))
    f = int(round((u - i) * FRAC))
    if f >= FRAC:
        i, f = i + 1, 0
    if f > FRAC / 2:
        i += 1
    return i, 0


def mm2u(v):
    """毫米 -> 坐标单位（整数）"""
    return int(round(v * COORD_PER_MM))


class Sch:
    def __init__(self, width_mm=420.0, height_mm=297.0, title="", rev="A",
                 sheetname="Sheet1", xzones=8, yzones=5, margin=10):
        self.recs = []
        self.next_uuid = 0
        self._sheet_index = 0
        self._desig = {}
        cx, cxf = mm(width_mm)
        cy, cyf = mm(height_mm)
        self.add(
            "RECORD=31",
            "FONTIDCOUNT=4",
            "SIZE1=10", "FONTNAME1=Times New Roman",
            "SIZE2=9", "FONTNAME2=Arial",
            "SIZE3=9", "FONTNAME3=Arial",
            "SIZE4=7", "FONTNAME4=Arial",
            "USEMBCS=T", "ISBOC=T",
            "HOTSPOTGRIDON=T", "HOTSPOTGRIDSIZE=4",
            "SHEETSTYLE=17", "SYSTEMFONT=1", "BORDERON=T",
            "SHEETNUMBERSPACESIZE=4", "AREACOLOR=16317695",
            "SNAPGRIDON=T", "VISIBLEGRIDON=T",
            "SNAPGRIDSIZE=1", "VISIBLEGRIDSIZE=10",
            "CUSTOMX=%d" % cx, "CUSTOMX_FRAC=%d" % cxf,
            "CUSTOMY=%d" % cy, "CUSTOMY_FRAC=%d" % cyf,
            "USECUSTOMSHEET=T",
            "CUSTOMXZONES=%d" % xzones, "CUSTOMYZONES=%d" % yzones,
            "CUSTOMMARGINWIDTH=%d" % margin,
            "DISPLAY_UNIT=4",
            "SHEETNUMBER=1", "SHEETTOTAL=1",
            "SHEETNAME=%s" % sheetname,
            "TITLE=%s" % title, "REVISION=%s" % rev,
        )

    # ------------------------------------------------------------------
    def add(self, *fields):
        idx = len(self.recs)
        self.recs.append("|".join(fields))
        return idx

    def sheet_idx(self):
        """顶层图元的唯一序号。Altium 用 INDEXINSHEET 建立连接图；
        缺失或全为 0 会把每个网络标号/电源端口判为 Floating（ERC 警告）。"""
        self._sheet_index += 1
        return "INDEXINSHEET=%d" % self._sheet_index

    def uid(self, prefix="a"):
        self.next_uuid += 1
        return "gg%s%06d" % (prefix, self.next_uuid)

    def _loc(self, x_mm, y_mm, tag="LOCATION"):
        xi, xf = mm(x_mm)
        yi, yf = mm(y_mm)
        return ["%s.X=%d" % (tag, xi), "%s.X_FRAC=%d" % (tag, xf),
                "%s.Y=%d" % (tag, yi), "%s.Y_FRAC=%d" % (tag, yf)]

    # ------------------------------------------------------------------
    def component(self, libref, x, y, w, h, designator, comment="",
                  footprint="", pins=(), show_comment=True, body_color=0,
                  auto_labels=True):
        """放元件。pins: [(desig, name, side, offset, length, electrical)]

        side: 'L'/'R'/'T'/'B'；offset 自左下角算起（L/R 为 y 偏移，T/B 为 x 偏移）
        返回 (comp_index, {pin_name: (x, y, side)})
        """
        ci = self.add(
            "RECORD=1", *self._loc(x, y),
            "ORIENTATION=0",
            "LIBREFERENCE=%s" % libref,
            "SHOWHIDDENPINS=F", "CURRENTPARTID=1", "DISPLAYMODE=0",
            "ISMIRRORED=F", "PARTIDLOCKED=F", "TARGETFILENAME=",
            "UNIQUEID=%s" % self.uid("c"))

        x2, y2 = x + w, y + h
        xi, xf = mm(x2)
        yi, yf = mm(y2)
        self.add(
            "RECORD=10", "OWNERINDEX=%d" % ci, "OWNERPARTID=1",
            "OWNERPARTDISPLAYMODE=0", "ISNOTACCESIBLE=T",
            *self._loc(x, y),
            "CORNER.X=%d" % xi, "CORNER.X_FRAC=%d" % xf,
            "CORNER.Y=%d" % yi, "CORNER.Y_FRAC=%d" % yf,
            "CORNERXRADIUS=0", "CORNERYRADIUS=0",
            "LINEWIDTH=1", "COLOR=%d" % body_color)

        self._desig[ci] = designator
        if auto_labels:
            self.designator(ci, x, y2 + 1.2)

        if comment and show_comment:
            self.param(ci, "Comment", comment, x, y - 3.4)

        if footprint:
            self.add(
                "RECORD=41", "COLOR=0", *self._loc(x, y - 3.4),
                "OWNERINDEX=%d" % ci, "OWNERPARTID=-1",
                "FONTID=%d" % FONT_MAIN, "NAME=Footprint",
                "TEXT=Footprint_%s" % footprint,
                "SHOWNAME=F", "ISHIDDEN=T", "ORIENTATION=0",
                "JUSTIFICATION=0")

        hot = {}
        for (pdes, pname, side, off, plen, elec) in pins:
            # Altium pin 记录的 LOCATION 是「引脚根部」(贴元件体一侧)，电气热点
            # = LOCATION + 方向 * PINLENGTH。方向由 PINCONGLOMERATE 低 2 位编码，
            # 从 Altium 原生 SchDoc 逐点反推（Y 轴向上）：0=+X 1=+Y 2=-X 3=-Y。
            # 早期版本把 LOCATION 直接写成热点、且方向位全部用反，Altium 因此
            # 认为导线落在非电气点上 -> 末端标号/电源端口批量报 Floating。
            if side == "L":          # 热点在体左外侧，根部贴在体左边缘
                hx, hy = x - plen, y + off
                rot, dx, dy = 2, -1, 0
            elif side == "R":
                hx, hy = x2 + plen, y + off
                rot, dx, dy = 0, +1, 0
            elif side == "T":
                hx, hy = x + off, y2 + plen
                rot, dx, dy = 1, 0, +1
            else:                    # B
                hx, hy = x + off, y - plen
                rot, dx, dy = 3, 0, -1
            cong = 56 | rot
            plen_u = mm2u(plen)
            hxi, _ = mm(hx)
            hyi, _ = mm(hy)
            # 用整数坐标单位反推根部，避免 mm() 的 floor 与 mm2u() 的 round
            # 相差 1 单位导致 Altium 推出的热点与导线端点错开一格。
            rxi = hxi - dx * plen_u
            ryi = hyi - dy * plen_u
            # Altium 在本方言里把引脚名压在引脚线上、还伸到体外，与网络标号打架；
            # 每个引脚都已有网络标号/电源端口，故统一隐藏引脚名，只保留引脚号。
            shown = "" if HIDE_PIN_NAMES else pname
            if libref in PASSIVE_LIBS and pname in HIDDEN_PIN_NAMES:
                shown = ""
            self.add(
                "RECORD=2", "OWNERINDEX=%d" % ci, "OWNERPARTID=1",
                "OWNERPARTDISPLAYMODE=0", "FORMALTYPE=1",
                # 注意：不能写 ISNOTACCESIBLE=T，否则 Altium 把引脚判为电气不可访问，
                # 连到它的导线不算有效连接，末端网络标号会被批量报 "Floating Net Label"。
                "ELECTRICAL=%d" % elec,
                "SYMBOL_INNER=0", "SYMBOL_INNEREDGE=0",
                "SYMBOL_OUTER=0", "SYMBOL_OUTEREDGE=0",
                "COLOR=136", "FONTID=%d" % FONT_PIN,
                "DESIGNATOR=%s" % pdes, "NAME=%s" % (shown or "~"),
                "PINCONGLOMERATE=%d" % cong,
                "LOCATION.X=%d" % rxi, "LOCATION.Y=%d" % ryi,
                "PINLENGTH=%d" % plen_u)
            key = pname if pname else str(pdes)
            hot[key] = (hx, hy, side)
        return ci, hot

    # ------------------------------------------------------------------
    def designator(self, ci, x, y, justification=0):
        return self.add(
            "RECORD=34", "COLOR=0", *self._loc(x, y),
            "OWNERINDEX=%d" % ci, "OWNERPARTID=-1",
            "FONTID=%d" % FONT_MAIN, "NAME=Designator",
            "TEXT=%s" % self._desig.get(ci, "U?"),
            "SHOWNAME=F", "ISHIDDEN=F", "ORIENTATION=0",
            "JUSTIFICATION=%d" % justification)

    def param(self, ci, name, text, x, y, justification=0, hidden=False):
        return self.add(
            "RECORD=41", "COLOR=0", *self._loc(x, y),
            "OWNERINDEX=%d" % ci, "OWNERPARTID=-1",
            "FONTID=%d" % FONT_MAIN, "NAME=%s" % name,
            "TEXT=%s" % text, "SHOWNAME=F",
            "ISHIDDEN=%s" % ("T" if hidden else "F"),
            "ORIENTATION=0", "JUSTIFICATION=%d" % justification)

    # ------------------------------------------------------------------
    def wire(self, pts, color=0):
        # 原生格式：INDEXINSHEET + OWNERPARTID=-1，坐标字段只用 Xn/Yn（不带 _FRAC）
        f = ["RECORD=27", self.sheet_idx(), "OWNERPARTID=-1",
             "LINEWIDTH=1", "COLOR=%d" % color,
             "LOCATIONCOUNT=%d" % len(pts)]
        for i, (x, y) in enumerate(pts, 1):
            xi, _ = mm(x)
            yi, _ = mm(y)
            f += ["X%d=%d" % (i, xi), "Y%d=%d" % (i, yi)]
        return self.add(*f)

    def netlabel(self, x, y, text, orientation=0, justification=0):
        return self.add(
            "RECORD=25", self.sheet_idx(), "OWNERPARTID=-1", *self._loc(x, y),
            "FONTID=%d" % FONT_LABEL, "TEXT=%s" % text,
            "ORIENTATION=%d" % orientation,
            "JUSTIFICATION=%d" % justification, "COLOR=0")

    def powerport(self, x, y, text, style=1, orientation=1):
        return self.add(
            "RECORD=17", self.sheet_idx(), "OWNERPARTID=-1", *self._loc(x, y),
            "SHOWNETNAME=T",
            "FONTID=%d" % FONT_LABEL, "TEXT=%s" % text,
            "STYLE=%d" % style, "ISHIDDEN=F",
            "ORIENTATION=%d" % orientation, "COLOR=0")

    def junction(self, x, y, size=2):
        return self.add("RECORD=29", "INDEXINSHEET=-1", "OWNERPARTID=-1", *self._loc(x, y),
                        "SIZE=%d" % size, "COLOR=0")

    def text(self, x, y, s, font=FONT_NOTE, orientation=0, justification=0):
        return self.add(
            "RECORD=4", self.sheet_idx(), "OWNERPARTID=-1", *self._loc(x, y),
            "FONTID=%d" % font, "TEXT=%s" % s,
            "ORIENTATION=%d" % orientation,
            "JUSTIFICATION=%d" % justification, "COLOR=0")

    # ------------------------------------------------------------------
    def render(self):
        head = ("|HEADER=Protel for Windows - Schematic Capture Ascii File "
                "Version 5.0|WEIGHT=%d" % len(self.recs))
        lines = [head] + ["|" + r + "|" for r in self.recs]
        return "\r\n".join(lines) + "\r\n"

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.render().encode("latin-1", "replace"))
        return path
