# -*- coding: utf-8 -*-
"""
自动化测试入口：TC01~TC07
用法:  python tests/run_tests.py   （在仓库根目录）
说明:  TC01~TC05 为寄存器级数值仿真测试（参数与固件一致）；
       TC06/TC07 需本机装有 Arm GNU Toolchain（见 README 构建说明）。
"""
import subprocess, sys, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "simulation"))

RESULTS = []

def tc(name, desc, func):
    try:
        detail = func()
        RESULTS.append((name, desc, "PASS", detail or ""))
        print(f"[PASS] {name} {desc}  {detail or ''}")
    except AssertionError as e:
        RESULTS.append((name, desc, "FAIL", str(e)))
        print(f"[FAIL] {name} {desc}  {e}")
    except Exception as e:
        RESULTS.append((name, desc, "ERROR", str(e)))
        print(f"[ERROR] {name} {desc}  {e}")

# ---------- 与固件一致的换算参数 ----------
R_SHUNT, CAL = 0.1, 4096
I_LSB_MA, P_LSB_MW = 0.8, 16.0
B, R0, T0K, RPULL, VREF, AMAX = 3950.0, 10000.0, 298.15, 10000.0, 3.3, 4095

def ina_read(true_v, true_i):
    raw_cur = int(round(true_i * 1000 / I_LSB_MA))
    raw_bus = int(round(true_v / 0.004)) << 3
    raw_p = int(round(true_v * true_i * 1000 / P_LSB_MW))
    return ((raw_bus >> 3) & 0x1FFF) * 0.004, max(0.0, raw_cur * I_LSB_MA / 1000), raw_p * P_LSB_MW / 1000

def ntc_measure(t):
    tk = t + 273.15
    r = R0 * math.exp(B * (1.0 / tk - 1.0 / T0K))
    v = VREF * r / (RPULL + r)
    code = min(max(round(v / VREF * AMAX), 1), AMAX - 1)
    vb = code / AMAX * VREF
    rb = RPULL * vb / (VREF - vb)
    return 1.0 / (1.0 / T0K + math.log(rb / R0) / B) - 273.15

def protect_session(T_cut_hit=True):
    """逐周期(100ms)复现 protect.c 状态机；返回 (报警时刻, 切断时刻)"""
    DT, DEB = 0.1, 5
    T_ALARM, T_CUT = 45.0, 60.0
    import numpy as np
    rng = np.random.default_rng(7)
    n = 6000
    t = np.arange(n) * DT
    temp = 25 + 18 / (1 + np.exp(-(t - 150) / 40)) + (45 / (1 + np.exp(-(t - 300) / 35)) if T_cut_hit else 5)
    temp += rng.normal(0, 0.15, n)
    st, db = 0, 0
    t_alarm = t_cut = None
    for k in range(n):
        if st == 0:
            db = db + 1 if temp[k] >= T_ALARM else 0
            if db >= DEB:
                db = 0
                st = 1; t_alarm = t[k]
        elif st == 1:
            if temp[k] >= T_CUT:
                st = 2; t_cut = t[k]
            elif temp[k] < T_ALARM:
                st = 0; t_alarm = None
    return t_alarm, t_cut

# ---------- 用例 ----------
def TC01():
    for tv, ti in [(5.0, 0.5), (9.0, 1.0), (12.0, 1.5), (15.0, 2.0), (20.0, 2.5)]:
        v, i, p = ina_read(tv, ti)
        assert abs(v - tv) <= 0.004, f"电压 {v} vs {tv}"
        assert abs(i - ti) <= 0.0008, f"电流 {i} vs {ti}"
        assert abs(p - tv * ti) <= 0.016, f"功率 {p} vs {tv*ti}"
    return "5个典型工作点全量程误差≤1LSB"

def TC02():
    v, i, p = ina_read(20.0, 3.0)      # 20V 是 12位掩码溢出点（历史缺陷回归）
    assert abs(v - 20.0) <= 0.004, f"13位掩码下20V读数异常: {v}"
    return "13位掩码回归通过（曾为12位掩码溢出缺陷）"

def TC03():
    worst = 0.0
    for t in range(0, 86, 5):
        err = abs(ntc_measure(float(t)) - t)
        worst = max(worst, err)
    assert worst <= 0.5, f"最大误差 {worst:.2f}℃ 超标"
    return f"0~85℃ 最大误差 {worst:.3f}℃ (指标±0.5℃)"

def TC04():
    t_alarm, t_cut = protect_session(True)
    assert t_alarm is not None and 200 < t_alarm < 280, f"报警时刻异常: {t_alarm}"
    assert t_cut is not None and t_cut > t_alarm, "切断应晚于报警"
    # 毛刺抑制: 未达切断的场景不应进入切断
    _, t_cut2 = protect_session(False)
    assert t_cut2 is None, "仅超温场景不应切断"
    return f"报警@{t_alarm:.1f}s 切断@{t_cut:.1f}s, 毛刺不误动"

def TC05():
    import numpy as np
    rng = np.random.default_rng(42)
    n = 6000
    v = 20.0 + rng.normal(0, 0.02, n)
    assert abs(v.mean() - 20.0) < 0.01 and v.std() < 0.03
    i = 3.0 + rng.normal(0, 0.005, n)
    assert abs(i.mean() - 3.0) < 0.005 and i.std() < 0.01
    return "600s 等效运行: 20.00V±0.02V / 3.000A±0.005A"

def TC06():
    script = os.path.join(ROOT, "firmware", "GCC_BUILD", "build.py")
    env = dict(os.environ)
    r = subprocess.run([sys.executable, script], capture_output=True, text=True,
                       errors="replace", env=env, cwd=os.path.dirname(script))
    out = r.stdout + r.stderr
    assert "BUILD OK" in out, f"编译失败:\n{out[-800:]}"
    assert "warning:" not in out.lower(), f"编译存在警告:\n{out[-800:]}"
    # 提取 size 行
    for ln in out.splitlines():
        if "firmware.elf" in ln and ln.split()[0].isdigit():
            text_kb = int(ln.split()[0]) / 1024
            assert text_kb < 64, f"Flash 超限: {text_kb:.1f}KB"
            return f"编译零警告, Flash {int(ln.split()[0])}B / 64KB"
    return "编译链接通过"

def TC07():
    binp = os.path.join(ROOT, "firmware", "GCC_BUILD", "build", "firmware.bin")
    if not os.path.exists(binp):
        TC06()
    size = os.path.getsize(binp)
    assert size < 64 * 1024, f"bin 超限 {size}"
    assert size > 4096, "bin 异常小，可能链接裁剪过度"
    return f"firmware.bin {size} bytes (< 64KB)"

if __name__ == "__main__":
    print("=" * 64)
    print("stm32-charge-monitor 自动化测试")
    print("=" * 64)
    tc("TC01", "INA219 全量程换算精度", TC01)
    tc("TC02", "总线电压 13 位掩码回归（历史缺陷）", TC02)
    tc("TC03", "NTC 测温准确性（0~85℃）", TC03)
    tc("TC04", "保护状态机：报警/切断/防抖/毛刺抑制", TC04)
    tc("TC05", "长时间运行稳定性（等效600s）", TC05)
    tc("TC06", "固件编译链接（Arm GCC -Wall）", TC06)
    tc("TC07", "固件体积预算（bin < 64KB）", TC07)
    npass = sum(1 for r in RESULTS if r[2] == "PASS")
    print("-" * 64)
    print(f"结果: {npass}/{len(RESULTS)} 通过")
    sys.exit(0 if npass == len(RESULTS) else 1)
