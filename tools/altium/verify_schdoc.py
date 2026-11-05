"""文本级校验：hardware/charge_monitor.SchDoc 是否与生成器网表一致。

生成器自带的电气自检只能证明「内存里的网表正确」；本工具进一步证明
「写进 .SchDoc 的记录没有丢、没有多、名字没有拼错」，并且**按 Altium 的
引脚语义复算电气热点**，确保每根导线真的连到了电气点而不是引脚根部——
后者正是 Altium 批量报 Floating Net Label / Floating Power Object 的根因。

注意：这是文本级一致性校验，**不等同于 Altium ERC**。

用法：python tools/altium/verify_schdoc.py
"""
import ast
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
# 0=+X 1=+Y 2=-X 3=-Y（Y 轴向上）。
PIN_DIR = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}


def assigned(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise SystemExit("[FAIL] 生成器中找不到 %s" % name)


def fields_of(line):
    return dict(kv.split("=", 1)
                for kv in line.strip().strip("|").split("|") if "=" in kv)


def connectivity(path):
    """复算引脚电气热点，检查热点与所有标号/端口都落在导线端点上。"""
    hotspots, endpoints, marks = [], set(), []
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"\|RECORD=(\d+)\|", line)
            if not m:
                continue
            rid = int(m.group(1))
            d = fields_of(line)
            if rid == PIN:
                x, y = int(d["LOCATION.X"]), int(d["LOCATION.Y"])
                L = int(d["PINLENGTH"])
                dx, dy = PIN_DIR[int(d.get("PINCONGLOMERATE", "0")) & 3]
                hotspots.append((x + dx * L, y + dy * L,
                                 d.get("DESIGNATOR", "?")))
            elif rid == WIRE:
                n = int(d.get("LOCATIONCOUNT", "0"))
                for i in range(1, n + 1):
                    if "X%d" % i in d and "Y%d" % i in d:
                        endpoints.add((int(d["X%d" % i]), int(d["Y%d" % i])))
            elif rid in (NETLABEL, POWERPORT):
                marks.append((int(d["LOCATION.X"]), int(d["LOCATION.Y"]),
                              d.get("TEXT", "?"),
                              "标号" if rid == NETLABEL else "电源端口"))

    errs = []
    for x, y, des in hotspots:
        if (x, y) not in endpoints:
            errs.append("引脚 %s 电气热点 (%d,%d) 未接导线" % (des, x, y))
    for x, y, text, kind in marks:
        if (x, y) not in endpoints:
            errs.append("%s %s 坐标 (%d,%d) 不在导线端点" % (kind, text, x, y))
    return errs, len(hotspots), len(endpoints), len(marks)


def main():
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
    with io.open(SCH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"\|RECORD=(\d+)\|", line)
            if not m:
                continue
            rid = int(m.group(1))
            kinds[rid] += 1
            if rid in (NETLABEL, POWERPORT):
                t = re.search(r"\|TEXT=([^|]*)\|", line)
                if t:
                    (labels if rid == NETLABEL else ports)[t.group(1)] += 1

    errs = []
    exp_labels = {}
    for net, members in nets.items():
        if net in pwr:
            continue
        exp_labels[net] = sum(1 for key in members if key not in no_label)
    for net, want in exp_labels.items():
        if labels[net] != want:
            errs.append("网络标号 %s: 期望 %d 个，实际 %d 个" % (net, want, labels[net]))
    for net in pwr:
        want = len(nets.get(net, []))
        if ports[net] != want:
            errs.append("电源端口 %s: 期望 %d 个，实际 %d 个" % (net, want, ports[net]))
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

    conn_errs, nhot, nend, nmark = connectivity(SCH)
    errs.extend(conn_errs)

    print("SchDoc 文本级校验")
    print("  网络 %d 个（电源 %d）、引脚 %d、导线 %d、网络标号 %d、电源端口 %d" %
          (len(nets), len(pwr), kinds[PIN], kinds[WIRE],
           sum(labels.values()), sum(ports.values())))
    print("  引脚电气热点 %d 个、导线端点 %d 个、标号/端口 %d 个" %
          (nhot, nend, nmark))
    if errs:
        for e in errs:
            print("  [FAIL]", e)
        return 1
    print("  [PASS] 网表、标号、端口、引脚数量一致，且所有电气热点与标号均落在导线端点")
    return 0


if __name__ == "__main__":
    sys.exit(main())
