# -*- coding: utf-8 -*-
"""当前版测试入口。TC01-TC05 是 Python 数值/行为模型，不直接执行 C 源码。"""
import math
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []

def run_case(name, description, fn):
    try:
        detail = fn()
        RESULTS.append((name, True))
        print(f"[PASS] {name} {description}: {detail}")
    except Exception as exc:
        RESULTS.append((name, False))
        print(f"[FAIL] {name} {description}: {exc}")

I_LSB_A = 0.0008
P_LSB_W = 0.016
R0 = 10000.0
BETA = 3950.0
T0_K = 298.15
VREF = 3.3
ADC_MAX = 4095

def ina_model(voltage, current):
    raw_v = round(voltage / 0.004)
    raw_i = round(current / I_LSB_A)
    raw_p = round(voltage * current / P_LSB_W)
    return raw_v * 0.004, raw_i * I_LSB_A, raw_p * P_LSB_W

def ntc_model(temp_c):
    tk = temp_c + 273.15
    resistance = R0 * math.exp(BETA * (1.0 / tk - 1.0 / T0_K))
    adc_v = VREF * resistance / (R0 + resistance)
    code = min(max(round(adc_v / VREF * ADC_MAX), 1), ADC_MAX - 1)
    v = code / ADC_MAX * VREF
    r = R0 * v / (VREF - v)
    return 1.0 / (1.0 / T0_K + math.log(r / R0) / BETA) - 273.15

def protection_model(samples):
    state, alarm_count, cutoff_count = "NORMAL", 0, 0
    for sample in samples:
        if not sample.get("valid", True):
            state = "CUTOFF"
            continue
        temp = sample.get("temp", 25.0)
        voltage = sample.get("voltage", 5.0)
        current = sample.get("current", 0.5)
        dangerous = temp >= 60.0 or voltage >= 21.0 or current >= 2.5
        alarm = temp >= 45.0 or voltage >= 21.0 or current >= 2.5
        if state == "NORMAL":
            if dangerous:
                cutoff_count += 1
                alarm_count = 0
                if cutoff_count >= 5:
                    state = "CUTOFF"
            elif alarm:
                alarm_count += 1
                cutoff_count = 0
                if alarm_count >= 5:
                    state = "ALARM"
            else:
                alarm_count = cutoff_count = 0
        elif state == "ALARM":
            if dangerous:
                cutoff_count += 1
                if cutoff_count >= 5:
                    state = "CUTOFF"
            else:
                cutoff_count = 0
                if temp < 42.0 and voltage < 21.0 and current < 2.5:
                    state = "NORMAL"
    return state

def tc01():
    for v0, i0 in [(5.0,0.5),(9.0,1.0),(12.0,1.5),(15.0,2.0),(20.0,2.5)]:
        v,i,p = ina_model(v0,i0)
        assert abs(v-v0) <= 0.004 and abs(i-i0) <= I_LSB_A and abs(p-v0*i0) <= P_LSB_W
    return "5个工作点误差不超过1 LSB"

def tc02():
    v,_,_ = ina_model(20.0,2.5)
    assert abs(v-20.0) <= 0.004
    return "20V 编码回归数值模型通过"

def tc03():
    errors = [abs(ntc_model(float(t))-t) for t in range(0,86,5)]
    worst = max(errors)
    assert worst <= 0.5, f"最大误差 {worst:.3f}℃"
    return f"NTC模型最大误差 {worst:.3f}℃；非实物精度"

def tc04():
    assert protection_model([{"temp":50.0}]*4) == "NORMAL"
    assert protection_model([{"temp":50.0}]*5) == "ALARM"
    assert protection_model([{"temp":50.0}]*5+[{"temp":61.0}]*4) == "ALARM"
    assert protection_model([{"temp":50.0}]*5+[{"temp":61.0}]*5) == "CUTOFF"
    assert protection_model([{"valid":False}]) == "CUTOFF"
    assert protection_model([{"valid":False}]+[{"temp":25.0}]*10) == "CUTOFF"
    return "5次防抖、故障即时切断、CUTOFF闭锁（Python模型）"

def tc05():
    rng = random.Random(42)
    vs = [20.0+rng.gauss(0,0.02) for _ in range(6000)]
    cs = [2.5+rng.gauss(0,0.005) for _ in range(6000)]
    assert abs(sum(vs)/len(vs)-20.0) < 0.01
    assert abs(sum(cs)/len(cs)-2.5) < 0.001
    return "6000个随机样本统计模型；不代表真实运行600秒"

def tc06():
    script = os.path.join(ROOT,"firmware","GCC_BUILD","build.py")
    result = subprocess.run([sys.executable,script],capture_output=True,text=True,errors="replace",cwd=os.path.dirname(script))
    output = result.stdout+result.stderr
    assert result.returncode == 0 and "BUILD OK" in output, output[-1200:]
    assert "warning:" not in output.lower(), output[-1200:]
    return "Arm GCC 构建成功且无 warning"

def tc07():
    binary = os.path.join(ROOT,"firmware","GCC_BUILD","build","firmware.bin")
    assert os.path.isfile(binary), "未找到 firmware.bin；先执行 TC06"
    size = os.path.getsize(binary)
    assert 4096 < size < 64*1024, f"固件体积异常：{size} bytes"
    return f"firmware.bin {size} bytes / 64KB"

if __name__ == "__main__":
    for case in [("TC01","INA219数值模型",tc01),("TC02","20V编码回归",tc02),("TC03","NTC数值模型",tc03),("TC04","保护行为模型",tc04),("TC05","随机数统计模型",tc05),("TC06","Arm GCC编译",tc06),("TC07","固件体积",tc07)]:
        run_case(*case)
    passed = sum(1 for _,ok in RESULTS if ok)
    print(f"结果: {passed}/{len(RESULTS)} 通过")
    sys.exit(0 if passed == len(RESULTS) else 1)
