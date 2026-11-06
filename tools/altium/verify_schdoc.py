"""SchDoc 文本级校验：网表一致性 + 两种连接画法的电气热点对齐。

生成器自带的电气自检只能证明「内存里的网表正确」；本工具进一步证明
「写进 .SchDoc 的记录没有丢、没有多、名字没有拼错」，并且**按 Altium 的
引脚语义复算电气热点**，确保连接落在电气点而不是引脚根部——后者正是
Altium 批量报 Floating Net Label / Floating Power Object 的根因。

支持两种合法的连接画法，自动识别：
  * stub   —— 每个引脚拉一根短导线，末端挂网络标号 / 电源端口（本项目采用）
  * direct —— 不画导线，网络标号 / 电源端口直接贴在引脚电气热点上
               （多图纸工程常见，如 altium_mcp 生成的分图纸设计）

同时兼容两种文件格式：Protel ASCII 纯文本、Altium OLE 复合文档（CDF）。

注意：这是文本级一致性校验，**不等同于 Altium ERC**。

用法：
  python tools/altium/verify_schdoc.py                   # 校验本仓库 SchDoc + 画法回归自测
  python tools/altium/verify_schdoc.py --path FILE|DIR  # 校验任意 SchDoc 或多图纸工程目录
  python tools/altium/verify_schdoc.py --selftest       # 只跑内置画法回归样本
"""
import ast
import glob
import io
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(ROOT, "simulation", "gen_altium_schdoc.py")
SCH = os.path.join(ROOT, "hardware", "charge_monitor.SchDoc")

PIN, POWERPORT, NETLABEL, WIRE = 2, 17, 25, 27

# Altium pin 的 LOCATION 是引脚根部，电气热点 = LOCATION + 方向 * PINLENGTH。
# 方向由 PINCONGLOMERATE 低 2 位编码，从 Altium 原生 SchDoc 逐点反推：
# 0=+X 1=+Y 2=-X 3=-Y（Y 轴向上）。已由另一套生成器（altium_mcp 多图纸工程）
# 的 201 个引脚 / 155 个标号独立交叉验证。
PIN_DIR = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}

RECORD_RE = re.compile(rb"\|RECORD=(\d+)\|[^\x00\r\n]*")


def assigned(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise SystemExit("[FAIL] 生成器中找不到 %s" % name)


def parse_records(data):
    """从 SchDoc 原始内容提取 [(record_id, fields)]。

    纯文本与 OLE 复合文档都以 |RECORD=N| 起头、以 NUL 或换行结束，
    因此可以用同一套字节级正则解析。文本里的中文按 latin1 解码会乱码，
    但本工具只读取 ASCII 字段名与英文网络名，不受影响。
    """
    if isinstance(data, str):
        data = data.encode("utf-8", "replace")
    out = []
    for m in RECORD_RE.finditer(data):
        rid = int(m.group(1))
        line = m.group(0).decode("latin1")
        d = dict(kv.split("=", 1)
                 for kv in line.strip().strip("|").split("|") if "=" in kv)
        out.append((rid, d))
    return out


def load_records(path):
    with open(path, "rb") as f:
        return parse_records(f.read())


def _xy(d, prefix="LOCATION"):
    try:
        return int(d[prefix + ".X"]), int(d[prefix + ".Y"])
    except (KeyError, ValueError, TypeError):
        return None


def _int(d, key, default=0):
    try:
        return int(d.get(key, default) or default)
    except (ValueError, TypeError):
        return default


def check_sheet(records, name="sheet"):
    """复算引脚电气热点，按自动识别的画法检查连接是否落在电气点上。

    返回 dict：style / pins / wires / marks / endpoints / errors。
    stub   画法：所有引脚热点与所有标号端口都必须在导线端点上。
    direct 画法：所有标号端口必须直接落在某个引脚热点上；
                 落在引脚根部或四周无引脚者分别给出明确诊断。
    """
    hotspots, roots, endpoints, marks = [], set(), set(), []
    wire_count = 0
    for rid, d in records:
        if rid == PIN:
            xy = _xy(d)
            if xy is None:
                continue
            L = _int(d, "PINLENGTH")
            dx, dy = PIN_DIR[_int(d, "PINCONGLOMERATE") & 3]
            roots.add(xy)
            hotspots.append((xy[0] + dx * L, xy[1] + dy * L,
                             d.get("DESIGNATOR", "?")))
        elif rid == WIRE:
            wire_count += 1
            n = _int(d, "LOCATIONCOUNT")
            for i in range(1, n + 1):
                kx, ky = "X%d" % i, "Y%d" % i
                if kx in d and ky in d:
                    endpoints.add((int(d[kx]), int(d[ky])))
        elif rid in (NETLABEL, POWERPORT):
            xy = _xy(d)
            if xy is None:
                continue
            marks.append((xy[0], xy[1], d.get("TEXT", "?"),
                          "标号" if rid == NETLABEL else "电源端口"))

    style = "stub" if wire_count else ("direct" if marks else "empty")
    errors = []
    if style == "stub":
        for x, y, des in hotspots:
            if (x, y) not in endpoints:
                errors.append("引脚 %s 电气热点 (%d,%d) 未接导线" % (des, x, y))
        for x, y, text, kind in marks:
            if (x, y) not in endpoints:
                errors.append("%s %s 坐标 (%d,%d) 不在导线端点" %
                              (kind, text, x, y))
    elif style == "direct":
        hot = {(x, y) for x, y, _ in hotspots}
        for x, y, text, kind in marks:
            if (x, y) in hot:
                continue
            if (x, y) in roots:
                errors.append("%s %s 坐标 (%d,%d) 贴在引脚根部而非电气热点" %
                              (kind, text, x, y))
            else:
                errors.append("%s %s 坐标 (%d,%d) 未贴到任何引脚电气热点（悬空）" %
                              (kind, text, x, y))
    else:
        errors.append("既无导线也无网络标号，无法判定连接画法")

    return {"name": name, "style": style, "pins": len(hotspots),
            "wires": wire_count, "marks": len(marks),
            "endpoints": len(endpoints), "errors": errors}


def check_path(path):
    """校验单个 SchDoc 或整个多图纸工程目录，返回 (汇总信息, 退出码)。"""
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.SchDoc")))
    elif os.path.isfile(path):
        files = [path]
    else:
        return ["路径不存在: %s" % path], 1
    if not files:
        return ["目录下没有 .SchDoc: %s" % path], 1

    results, rc = [], 0
    for f in files:
        try:
            r = check_sheet(load_records(f), os.path.basename(f))
        except (OSError, ValueError) as e:
            results.append((os.path.basename(f), "?", 0, 0, 0, ["读取失败: %s" % e]))
            rc = 1
            continue
        results.append((r["name"], r["style"], r["pins"], r["wires"],
                        r["marks"], r["errors"]))
        if r["errors"]:
            rc = 1

    print("SchDoc 连接画法校验: %s" % path)
    for name, style, pins, wires, marks, errs in results:
        print("  %-28s 画法=%-6s 引脚=%-4d 导线=%-4d 标号/端口=%-4d %s" %
              (name, style, pins, wires, marks,
               "OK" if not errs else "FAIL(%d)" % len(errs)))
        for e in errs:
            print("      - %s" % e)
    styles = Counter(r[1] for r in results if r[1] != "?")
    total_err = sum(len(r[5]) for r in results)
    print("  汇总: %d 张图纸, 画法 %s, 未对齐 %d 处 -> %s" %
          (len(results), dict(styles), total_err,
           "FAIL" if rc else "PASS"))
    return results, rc


def _rec(rid, **kw):
    return "|RECORD=%d|%s|" % (
        rid, "|".join("%s=%s" % (k, v) for k, v in kw.items()))


def _pin(x=100, y=200):
    # PINCONGLOMERATE=58 -> 低 2 位 = 2 -> 热点在 -X 方向，即 (x-20, y)
    return _rec(PIN, OWNERINDEX=1, OWNERPARTID=1, FORMALTYPE=1, ELECTRICAL=7,
                PINCONGLOMERATE=58, PINLENGTH=20,
                **{"LOCATION.X": x, "LOCATION.Y": y, "DESIGNATOR": 1,
                   "NAME": "VCC"})


def _label(x, y, text, port=False):
    return _rec(POWERPORT if port else NETLABEL, INDEXINSHEET=9,
                OWNERPARTID=-1, FONTID=1, TEXT=text,
                **{"LOCATION.X": x, "LOCATION.Y": y})


def _wire(x1, y1, x2, y2):
    return _rec(WIRE, INDEXINSHEET=8, OWNERPARTID=-1, LINEWIDTH=1,
                LOCATIONCOUNT=2, X1=x1, Y1=y1, X2=x2, Y2=y2, COLOR=0)


def selftest():
    """内置回归样本：证明工具能正确识别并判定两种画法的正例与反例。

    完全在内存中构造，不依赖任何外部工程文件，可在任何机器/CI 上复现。
    """
    cases = [
        ("direct-正确", [_pin(), _label(80, 200, "NET_A")], "direct", 0),
        ("direct-贴根部", [_pin(), _label(100, 200, "BAD_ROOT")], "direct", 1),
        ("direct-悬空", [_pin(), _label(80, 210, "BAD_FLOAT", port=True)],
         "direct", 1),
        ("stub-正确", [_pin(), _wire(80, 200, 50, 200),
                       _label(50, 200, "NET_A")], "stub", 0),
        ("stub-导线在根部", [_pin(), _wire(100, 200, 50, 200),
                             _label(50, 200, "NET_A")], "stub", 1),
    ]
    problems = []
    for name, lines, want_style, want_fail in cases:
        r = check_sheet(parse_records("\n".join(lines)), name)
        if r["style"] != want_style:
            problems.append("%s: 画法判定 %s，期望 %s" %
                            (name, r["style"], want_style))
        ok = not r["errors"]
        if ok == bool(want_fail):
            problems.append("%s: 期望%s，实际 errs=%s" %
                            (name, "报错" if want_fail else "通过", r["errors"]))
        if want_fail == 1 and name == "direct-贴根部" and \
                not any("根部" in e for e in r["errors"]):
            problems.append("%s: 未诊断出'贴在引脚根部'" % name)
        if want_fail == 1 and name == "direct-悬空" and \
                not any("悬空" in e for e in r["errors"]):
            problems.append("%s: 未诊断出'悬空'" % name)
    return len(cases), problems


def whitebox():
    """本仓库 SchDoc 与生成器网表的白盒一致性校验（原 TC09 主体）。"""
    with io.open(GEN, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=GEN)
    nets = assigned(tree, "nets")
    pwr = set(assigned(tree, "PWR"))
    no_label = set(assigned(tree, "NO_LABEL"))
    extra_wires = assigned(tree, "EXTRA_WIRES")

    pin_expected = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "place" and len(node.args) >= 7
                and isinstance(node.args[6], (ast.List, ast.Tuple))):
            pin_expected += len(node.args[6].elts)

    labels, ports, kinds = Counter(), Counter(), Counter()
    records = load_records(SCH)
    for rid, d in records:
        kinds[rid] += 1
        if rid in (NETLABEL, POWERPORT) and "TEXT" in d:
            (labels if rid == NETLABEL else ports)[d["TEXT"]] += 1

    errs = []
    exp_labels = {}
    for net, members in nets.items():
        if net in pwr:
            continue
        exp_labels[net] = sum(1 for key in members if key not in no_label)
    for net, want in exp_labels.items():
        if labels[net] != want:
            errs.append("网络标号 %s: 期望 %d 个，实际 %d 个" %
                        (net, want, labels[net]))
    for net in pwr:
        want = len(nets.get(net, []))
        if ports[net] != want:
            errs.append("电源端口 %s: 期望 %d 个，实际 %d 个" %
                        (net, want, ports[net]))
    for name in labels:
        if name not in nets or name in pwr:
            errs.append("出现未知/错位的网络标号: %s" % name)
    for name in ports:
        if name not in pwr:
            errs.append("出现未知电源端口: %s" % name)

    member_total = sum(len(v) for v in nets.values())
    wire_want = member_total + len(extra_wires)
    if kinds[WIRE] != wire_want:
        errs.append("导线: 期望 %d 条，实际 %d 条" % (wire_want, kinds[WIRE]))
    if kinds[PIN] != pin_expected:
        errs.append("引脚: 期望 %d 个，实际 %d 个" % (pin_expected, kinds[PIN]))

    conn = check_sheet(records, os.path.basename(SCH))
    errs.extend(conn["errors"])
    if conn["style"] != "stub":
        errs.append("本项目画法应为 stub，实际判定 %s" % conn["style"])

    print("SchDoc 文本级校验")
    print("  网络 %d 个（电源 %d）、引脚 %d、导线 %d、网络标号 %d、电源端口 %d" %
          (len(nets), len(pwr), kinds[PIN], kinds[WIRE],
           sum(labels.values()), sum(ports.values())))
    print("  画法 %s；引脚电气热点 %d 个、导线端点 %d 个、标号/端口 %d 个" %
          (conn["style"], conn["pins"], conn["endpoints"], conn["marks"]))
    return errs


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0

    if "--path" in argv:
        i = argv.index("--path")
        if i + 1 >= len(argv):
            print("[FAIL] --path 后需给出 .SchDoc 文件或目录")
            return 1
        _, rc = check_path(argv[i + 1])
        return rc

    ncases, st_problems = selftest()
    if "--selftest" in argv:
        print("画法回归自测: %d 组" % ncases)
        for p in st_problems:
            print("  [FAIL]", p)
        print("  [%s] %d/%d 组通过" %
              ("PASS" if not st_problems else "FAIL",
               ncases - len(set(p.split(":")[0] for p in st_problems)), ncases))
        return 1 if st_problems else 0

    errs = whitebox()
    errs.extend(["画法回归自测 " + p for p in st_problems])
    if errs:
        for e in errs:
            print("  [FAIL]", e)
        return 1
    print("  [PASS] 网表、标号、端口、引脚数量一致；所有电气热点与标号均落在导线端点")
    print("  [PASS] 画法回归自测 %d/%d 组（stub 与 direct 的正例/反例均可正确判定）" %
          (ncases, ncases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
