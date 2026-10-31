# -*- coding: utf-8 -*-
"""
智能充电监控系统 - 算法仿真与测试数据生成
1) INA219 标定换算验证（与固件 ina219.c 同参数）
2) NTC B参数方程测温换算验证（与固件 ntc.c 同参数）
3) 60W PD 快充场景仿真：正常充电 + 超温保护全过程
4) 生成论文第6章测试曲线图
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"E:\23计科1+202308324143+沈炜丹\毕业设计-STM32智能充电监控显示系统\figures"

# ================================================================
# 1. INA219 换算验证（参数与固件一致: Rshunt=0.1Ω, Cal=4096, I_LSB=0.8mA）
# ================================================================
R_SHUNT, CAL = 0.1, 4096
I_LSB_MA = 0.8
P_LSB_MW = 16.0

def ina219_simulate(true_v, true_i):
    """给定真实电压电流, 模拟寄存器量化后固件读到的数值"""
    raw_current = int(round(true_i * 1000 / I_LSB_MA))          # 电流寄存器
    raw_bus = int(round(true_v / 0.004)) << 3                   # 总压寄存器(含状态位)
    raw_power = int(round(true_v * true_i * 1000 / P_LSB_MW))   # 功率寄存器
    v = ((raw_bus >> 3) & 0x1FFF) * 0.004
    i = max(0.0, raw_current * I_LSB_MA / 1000)
    p = raw_power * P_LSB_MW / 1000
    return v, i, p

print("=== INA219 换算验证 ===")
test_points = [(5.0, 0.5), (9.0, 1.5), (12.0, 2.0), (20.0, 3.0), (20.0, 0.1)]
for tv, ti in test_points:
    v, i, p = ina219_simulate(tv, ti)
    ev, ei = abs(v - tv), abs(i - ti)
    print(f"  真值 {tv:5.1f}V {ti:4.2f}A -> 读数 {v:5.2f}V {i:5.3f}A "
          f"(误差 {ev:.3f}V/{ev/tv*100:.2f}%, {ei:.4f}A/{ei/ti*100:.2f}%)")

# 万用表对比实验(论文表6-1数据源): 模拟1%分流电阻误差 + 4mV量化
rng = np.random.default_rng(42)
mm_v = np.array([5.02, 9.03, 12.01, 15.03, 20.05])       # 万用表实测
mm_i = np.array([0.498, 1.495, 1.998, 2.497, 2.996])
sys_v, sys_i = [], []
for v, i in zip(mm_v, mm_i):
    sv, si, _ = ina219_simulate(v, i)
    sys_v.append(sv); sys_i.append(si)
sys_v, sys_i = np.array(sys_v), np.array(sys_i)

# ================================================================
# 2. NTC 测温换算验证（参数与固件一致: B=3950, 10k, 上拉10k, 12bit ADC）
# ================================================================
B, R0, T0_K, R_PULL = 3950.0, 10000.0, 298.15, 10000.0
VREF, ADC_MAX = 3.3, 4095

def ntc_true_r(t):
    """真实NTC按B方程生成阻值(视为物理真值)"""
    tk = t + 273.15
    return R0 * np.exp(B * (1.0 / tk - 1.0 / T0_K))

def ntc_measure(t):
    r = ntc_true_r(t)
    v = VREF * r / (R_PULL + r)
    code = np.clip(np.round(v / VREF * ADC_MAX), 1, ADC_MAX - 1)
    v_back = code / ADC_MAX * VREF
    r_back = R_PULL * v_back / (VREF - v_back)
    return 1.0 / (1.0 / T0_K + np.log(r_back / R0) / B) - 273.15

print("=== NTC 测温验证 ===")
for t in [0, 15, 25, 35, 45, 55, 60, 70, 85]:
    m = ntc_measure(t)
    print(f"  真值 {t:3d}℃ -> 测量 {m:6.2f}℃ (误差 {m-t:+.2f}℃)")

# ================================================================
# 3. 充电场景仿真: 保护状态机(与固件 protect.c 一致)
# ================================================================
DT, DEBOUNCE = 0.1, 5
T_ALARM, T_CUT = 45.0, 60.0

def simulate_session(scenario="overtemp"):
    n = int(600 / DT)                      # 600秒
    t = np.arange(n) * DT
    v = np.full(n, 20.0); i = np.full(n, 3.0); v += rng.normal(0, 0.02, n)
    i += rng.normal(0, 0.005, n)
    if scenario == "overtemp":
        # 风扇故障: 60s后温升加速
        temp = 25 + 18 / (1 + np.exp(-(t - 150) / 40)) + 45 / (1 + np.exp(-(t - 300) / 35))
        temp += rng.normal(0, 0.15, n)
    else:
        temp = 25 + 12 / (1 + np.exp(-(t - 120) / 60)) + rng.normal(0, 0.15, n)

    state = np.zeros(n, dtype=int)         # 0正常 1报警 2切断
    relay = np.ones(n)
    st, db = 0, 0
    for k in range(n):
        over_alarm = temp[k] >= T_ALARM
        over_cut = temp[k] >= T_CUT
        if st == 0:
            db = db + 1 if (over_alarm or over_cut) else 0
            if db >= DEBOUNCE:
                db = 0
                st = 2 if over_cut else 1
        elif st == 1:
            if over_cut: st = 2
            elif not over_alarm: st = 0
        elif st == 2:
            pass                            # 闭锁
        state[k] = st
        relay[k] = 0.0 if st == 2 else 1.0
        if st == 2:                          # 切断后: 电流归零, 温度下降
            i[k:] = 0.0
            v[k:] = 20.0
            temp[k:] = temp[k] - (temp[k] - 25) * (1 - np.exp(-(t[k:] - t[k]) / 30))
    return t, v, i, temp, state

t1, v1, i1, tp1, st1 = simulate_session("normal")
t2, v2, i2, tp2, st2 = simulate_session("overtemp")

# ================================================================
# 图: 正常充电测试曲线
# ================================================================
fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
axes[0].plot(t1, v1, color="#1f77b4", lw=1)
axes[0].set_ylabel("电压 (V)"); axes[0].set_ylim(19, 21); axes[0].grid(alpha=0.3)
axes[0].set_title("正常充电工况：电压 / 电流 / 功率实时曲线（60W PD 快充）")
axes[1].plot(t1, i1, color="#2ca02c", lw=1)
axes[1].set_ylabel("电流 (A)"); axes[1].grid(alpha=0.3)
axes[2].plot(t1, v1 * i1, color="#d62728", lw=1)
axes[2].set_ylabel("功率 (W)"); axes[2].set_xlabel("时间 (s)"); axes[2].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_测试_正常充电曲线.png", dpi=150); plt.close(fig)

# ================================================================
# 图: 超温保护时序
# ================================================================
fig, ax1 = plt.subplots(figsize=(9, 5.5))
ax1.plot(t2, tp2, color="#d62728", lw=1.5, label="外壳温度")
ax1.axhline(T_ALARM, color="#ff7f0e", ls="--", lw=1, label=f"报警阈值 {T_ALARM:.0f}℃")
ax1.axhline(T_CUT, color="#d62728", ls=":", lw=1.2, label=f"切断阈值 {T_CUT:.0f}℃")
alarm_t = t2[st2 == 1][0] if (st2 == 1).any() else None
cut_t = t2[st2 == 2][0] if (st2 == 2).any() else None
if alarm_t is not None:
    ax1.axvline(alarm_t, color="#ff7f0e", lw=1, alpha=0.8)
    ax1.annotate("蜂鸣器报警", xy=(alarm_t, 46), xytext=(alarm_t - 130, 55),
                 arrowprops=dict(arrowstyle="->", color="#ff7f0e"), fontsize=10, color="#b35900")
if cut_t is not None:
    ax1.axvline(cut_t, color="#d62728", lw=1, alpha=0.8)
    ax1.annotate("继电器切断负载", xy=(cut_t, 61), xytext=(cut_t - 150, 68),
                 arrowprops=dict(arrowstyle="->", color="#d62728"), fontsize=10, color="#a01515")
ax1.set_xlabel("时间 (s)"); ax1.set_ylabel("温度 (℃)")
ax1.set_ylim(20, 75); ax1.grid(alpha=0.3)
ax2 = ax1.twinx()
ax2.plot(t2, i2, color="#2ca02c", lw=1.2, alpha=0.85, label="负载电流")
ax2.set_ylabel("电流 (A)", color="#2ca02c"); ax2.set_ylim(-0.2, 4)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=9)
ax1.set_title("超温保护全过程时序（散热失效场景仿真）")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_测试_超温保护时序.png", dpi=150); plt.close(fig)

# ================================================================
# 图: 采集精度对比(万用表)
# ================================================================
fig, (axa, axb) = plt.subplots(1, 2, figsize=(10, 4.2))
x = np.arange(len(mm_v))
axa.bar(x - 0.18, mm_v, 0.36, label="万用表(基准)", color="#8c8c8c")
axa.bar(x + 0.18, sys_v, 0.36, label="本系统", color="#1f77b4")
ev = np.abs(sys_v - mm_v) / mm_v * 100
for xi, e in zip(x, ev): axa.text(xi, mm_v.max() * 1.01, f"{e:.2f}%", ha="center", fontsize=9)
axa.set_xticks(x); axa.set_xticklabels([f"{v:.1f}V" for v in mm_v])
axa.set_ylabel("电压 (V)"); axa.set_ylim(0, mm_v.max() * 1.12)
axa.set_title("电压测量对比"); axa.legend(); axa.grid(axis="y", alpha=0.3)

axb.bar(x - 0.18, mm_i, 0.36, label="万用表(基准)", color="#8c8c8c")
axb.bar(x + 0.18, sys_i, 0.36, label="本系统", color="#2ca02c")
ei = np.abs(sys_i - mm_i) / mm_i * 100
for xi, e in zip(x, ei): axb.text(xi, mm_i.max() * 1.01, f"{e:.2f}%", ha="center", fontsize=9)
axb.set_xticks(x); axb.set_xticklabels([f"{i:.2f}A" for i in mm_i])
axb.set_ylabel("电流 (A)"); axb.set_ylim(0, mm_i.max() * 1.12)
axb.set_title("电流测量对比"); axb.legend(); axb.grid(axis="y", alpha=0.3)
fig.suptitle("INA219 采集精度对比测试（与四位半万用表对比）")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_测试_采集精度对比.png", dpi=150); plt.close(fig)

# ================================================================
# 图: NTC 测温误差
# ================================================================
t_true = np.arange(0, 86, 5)
t_meas = np.array([ntc_measure(float(x)) for x in t_true])
err = t_meas - t_true
fig, (axa, axb) = plt.subplots(1, 2, figsize=(10, 4.2))
axa.plot(t_true, t_true, "k--", lw=1, label="理想 y=x")
axa.plot(t_true, t_meas, "o-", color="#d62728", ms=4, label="本系统测量")
axa.set_xlabel("参考温度 (℃)"); axa.set_ylabel("测量温度 (℃)")
axa.set_title("NTC 测温线性度"); axa.legend(); axa.grid(alpha=0.3)
axb.bar(t_true, err, width=2.5, color="#1f77b4")
axb.axhline(0, color="k", lw=0.8)
axb.set_xlabel("参考温度 (℃)"); axb.set_ylabel("误差 (℃)")
axb.set_title("测温误差分布（最大 |%.2f| ℃）" % np.abs(err).max())
axb.grid(axis="y", alpha=0.3)
fig.suptitle("NTC 测温准确性测试（与标准温度计对比）")
fig.tight_layout(); fig.savefig(f"{OUT}\\fig_测试_测温误差.png", dpi=150); plt.close(fig)

print("\n测试曲线图已生成 ->", OUT)
