"""Altium ASCII SchDoc 生成库（Protel for Windows - Schematic Capture Ascii v5.0）

从 Altium 真实导出的 ASCII SchDoc 反推出的方言要点：
  * 首行  |HEADER=Protel for Windows - Schematic Capture Ascii File Version 5.0|WEIGHT=n
  * 每条记录 '|RECORD=' 开头、尾随 '|' 结束，各占一行
  * 坐标单位 = 10 mil；小数部分另存 <NAME>_FRAC（1e-5 单位）
  * OWNERINDEX 为 0 基记录序号（sheet 记录 = 0，header 不计）
  * 矩形是 RECORD=10（LOCATION + CORNER），不是 13
  * 导线 RECORD=27（LOCATIONCOUNT + X1..Xn/Y1..Yn）
  * 引脚 RECORD=2；PINCONGLOMERATE 低 2 位 = 朝向(0右/1上/2左/3下)，0x38 = 显示标志
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
            # PINCONGLOMERATE 低 2 位 = 引脚线"由电气端指向元件体"的方向
            #   0=右 1=上 2=左 3=下
            if side == "L":                 # 电气端在体左 -> 线向右进体
                hx, hy, cong = x - plen, y + off, 56 | 0
            elif side == "R":               # 电气端在体右 -> 线向左进体
                hx, hy, cong = x2 + plen, y + off, 56 | 2
            elif side == "T":               # 电气端在体上 -> 线向下进体
                hx, hy, cong = x + off, y2 + plen, 56 | 3
            else:                           # 电气端在体下 -> 线向上进体
                hx, hy, cong = x + off, y - plen, 56 | 1
            # Altium 在本方言里把引脚名压在引脚线上、还伸到体外，与网络标号打架；
            # 每个引脚都已有网络标号/电源端口，故统一隐藏引脚名，只保留引脚号。
            shown = "" if HIDE_PIN_NAMES else pname
            if libref in PASSIVE_LIBS and pname in HIDDEN_PIN_NAMES:
                shown = ""
            self.add(
                "RECORD=2", "OWNERINDEX=%d" % ci, "OWNERPARTID=1",
                "OWNERPARTDISPLAYMODE=0", "ISNOTACCESIBLE=T",
                "ELECTRICAL=%d" % elec,
                "SYMBOL_INNER=0", "SYMBOL_INNEREDGE=0",
                "SYMBOL_OUTER=0", "SYMBOL_OUTEREDGE=0",
                "COLOR=136", "FONTID=%d" % FONT_PIN,
                "DESIGNATOR=%s" % pdes, "NAME=%s" % (shown or "~"),
                "PINCONGLOMERATE=%d" % cong,
                *self._loc(hx, hy),
                "PINLENGTH=%d" % mm2u(plen))
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
        f = ["RECORD=27", "OWNERINDEX=0", "OWNERPARTID=-1",
             "LINEWIDTH=1", "LOCATIONCOUNT=%d" % len(pts)]
        for i, (x, y) in enumerate(pts, 1):
            xi, xf = mm(x)
            yi, yf = mm(y)
            f += ["X%d=%d" % (i, xi), "X%d_FRAC=%d" % (i, xf),
                  "Y%d=%d" % (i, yi), "Y%d_FRAC=%d" % (i, yf)]
        f += ["COLOR=%d" % color]
        return self.add(*f)

    def netlabel(self, x, y, text, orientation=0, justification=0):
        return self.add(
            "RECORD=25", "OWNERINDEX=0", "OWNERPARTID=-1", *self._loc(x, y),
            "FONTID=%d" % FONT_LABEL, "TEXT=%s" % text,
            "ORIENTATION=%d" % orientation,
            "JUSTIFICATION=%d" % justification, "COLOR=0")

    def powerport(self, x, y, text, style=1, orientation=1):
        return self.add(
            "RECORD=17", "OWNERINDEX=0", "OWNERPARTID=-1", *self._loc(x, y),
            "FONTID=%d" % FONT_LABEL, "TEXT=%s" % text,
            "STYLE=%d" % style, "ISHIDDEN=F",
            "ORIENTATION=%d" % orientation, "COLOR=0")

    def junction(self, x, y, size=2):
        return self.add("RECORD=29", "OWNERINDEX=0", "OWNERPARTID=-1", *self._loc(x, y),
                        "SIZE=%d" % size, "COLOR=0")

    def text(self, x, y, s, font=FONT_NOTE, orientation=0, justification=0):
        return self.add(
            "RECORD=4", "OWNERINDEX=0", "OWNERPARTID=-1", *self._loc(x, y),
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
