/**
  ******************************************************************************
  * @file    protect_tests.c
  * @brief   保护状态机单元测试（主机编译运行，直接覆盖真实 protect.c 逻辑）
  *
  * 编译运行:
  *   gcc protect_tests.c ../firmware/Core/Src/protect.c \
  *       -I ../firmware/Core/Inc -lm -o build/protect_tests && ./build/protect_tests
  *
  * 覆盖: 上电启动吸合、告警/切断判定、防抖、毛刺抑制、传感器故障立即切断与
  *       自动恢复、阈值越限闭锁与显式恢复、恢复安全门卫。
  ******************************************************************************
  */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "protect.h"

/* ---- HAL 桩：记录继电器/蜂鸣器动作，供断言检查 ---- */
static uint8_t g_relay = 0U, g_buzzer = 0U;
void Protect_HAL_RelaySet(uint8_t on) { g_relay = on; }
void Protect_HAL_BuzzerSet(uint8_t on) { g_buzzer = on; }

/* 全局监测数据（protect.c 以 extern 引用） */
monitor_data_t g_mon = {0};

static int failures = 0;
#define CHECK(cond, msg) do {                                            \
    if (!(cond)) { printf("    [FAIL] %s\n", (msg)); failures++; }       \
    else        { printf("    [ ok ] %s\n", (msg)); }                    \
} while (0)

/* 一份安全有效的默认采样 */
static monitor_data_t safe_sample(void)
{
    monitor_data_t m;
    memset(&m, 0, sizeof(m));
    m.bus_voltage = 5.0f; m.current = 1.0f; m.power = 5.0f;
    m.temperature = 25.0f; m.sensor_fault = 0U;
    return m;
}

/* 连续喂 n 份相同采样，返回最终状态 */
static protect_state_t feed(const monitor_data_t *m, int n)
{
    protect_state_t s = PROTECT_NORMAL;
    for (int k = 0; k < n; k++) s = Protect_Update(m);
    return s;
}

/* ---- 用例 ---- */

static void t_startup(void)
{
    printf("[TEST] 上电启动：默认断开，安全采样后吸合\n");
    Protect_Init();
    CHECK(Protect_StateName() != NULL, "Protect_Init 后状态可读");
    CHECK(g_relay == 0U, "上电默认继电器断开");
    monitor_data_t m = safe_sample();
    protect_state_t s = feed(&m, (int)ALARM_DEBOUNCE_COUNT + 1);
    CHECK(s == PROTECT_NORMAL, "持续安全采样保持在 NORMAL");
    CHECK(g_relay == 1U, "启动防抖后继电器吸合");
    CHECK(g_buzzer == 0U, "正常态蜂鸣器静默");
}

static void t_alarm(void)
{
    printf("[TEST] 超温告警：45℃<=T<60℃，进入 ALARM 但不切断\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1); /* 先吸合 */
    monitor_data_t m = safe_sample(); m.temperature = 50.0f;   /* 仅超告警阈值 */
    protect_state_t s = feed(&m, (int)ALARM_DEBOUNCE_COUNT + 1);
    CHECK(s == PROTECT_ALARM, "持续超温进入 ALARM");
    CHECK(g_relay == 1U, "告警态继电器仍吸合（未切断）");
    CHECK(g_buzzer == 1U, "告警态蜂鸣器鸣响");
}

static void t_threshold_cutoff(void)
{
    printf("[TEST] 阈值越限切断：T>=60℃ 经防抖进入 CUTOFF\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1);
    monitor_data_t m = safe_sample(); m.temperature = 65.0f;
    protect_state_t s = feed(&m, (int)ALARM_DEBOUNCE_COUNT + 1);
    CHECK(s == PROTECT_CUTOFF, "持续超温进入 CUTOFF");
    CHECK(g_relay == 0U, "切断态继电器断开");
    CHECK(g_buzzer == 1U, "切断态蜂鸣器鸣响");
}

static void t_glitch(void)
{
    printf("[TEST] 毛刺抑制：单次越限不切断\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1);
    monitor_data_t hot = safe_sample(); hot.temperature = 65.0f;
    monitor_data_t ok  = safe_sample();
    Protect_Update(&hot);                 /* 仅一个周期越限 */
    protect_state_t s = feed(&ok, (int)ALARM_DEBOUNCE_COUNT + 1);
    CHECK(s == PROTECT_NORMAL, "短暂越限后恢复为 NORMAL（未误切断）");
    CHECK(g_relay == 1U, "毛刺后继电器保持吸合");
}

static void t_sensor_fault_cutoff(void)
{
    printf("[TEST] 传感器故障：立即切断\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1);
    monitor_data_t m = safe_sample(); m.sensor_fault = 1U;
    protect_state_t s = Protect_Update(&m);
    CHECK(s == PROTECT_CUTOFF, "传感器故障立即进入 CUTOFF");
    CHECK(g_relay == 0U, "故障切断继电器断开");
    CHECK(g_buzzer == 1U, "故障切断蜂鸣器鸣响");
}

static void t_sensor_fault_auto_recover(void)
{
    printf("[TEST] 传感器故障自动恢复：采样恢复且安全后经防抖恢复吸合\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1);
    monitor_data_t bad = safe_sample(); bad.sensor_fault = 1U;
    Protect_Update(&bad);                  /* 进入传感器故障切断 */
    CHECK(Protect_StateName() && g_relay == 0U, "已处于故障切断");
    monitor_data_t good = safe_sample();
    protect_state_t s = feed(&good, (int)(RECOVER_DEBOUNCE_COUNT + ALARM_DEBOUNCE_COUNT + 2));
    CHECK(s == PROTECT_NORMAL, "采样恢复后自动回到 NORMAL");
    CHECK(g_relay == 1U, "恢复后继电器重新吸合");
}

static void t_threshold_latch(void)
{
    printf("[TEST] 阈值切断闭锁：安全恢复后仍闭锁，需显式 Protect_Recover\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1);
    monitor_data_t hot = safe_sample(); hot.temperature = 65.0f;
    feed(&hot, (int)ALARM_DEBOUNCE_COUNT + 1);   /* 进入阈值切断 */
    /* 回到安全采样：阈值切断应保持闭锁 */
    monitor_data_t good = safe_sample();
    protect_state_t s = feed(&good, (int)ALARM_DEBOUNCE_COUNT + 2);
    CHECK(s == PROTECT_CUTOFF, "阈值切断在安全采样下仍闭锁");
    CHECK(g_relay == 0U, "闭锁期间继电器保持断开");
    /* 显式恢复（当前安全） */
    g_mon = good;
    Protect_Recover();
    CHECK(strncmp(Protect_StateName(), "NORMAL", 6) == 0, "显式恢复后解除闭锁进入 NORMAL");
    /* 恢复后继续安全采样：继电器重新吸合 */
    s = feed(&good, (int)ALARM_DEBOUNCE_COUNT + 1);
    CHECK(s == PROTECT_NORMAL, "显式恢复后回到 NORMAL");
    CHECK(g_relay == 1U, "显式恢复后继电器吸合");
}

static void t_recover_guard(void)
{
    printf("[TEST] 恢复安全门卫：危险未消除时 Protect_Recover 不生效\n");
    Protect_Init();
    feed(&(monitor_data_t){0}, (int)ALARM_DEBOUNCE_COUNT + 1);
    monitor_data_t hot = safe_sample(); hot.temperature = 65.0f;
    feed(&hot, (int)ALARM_DEBOUNCE_COUNT + 1);   /* 阈值切断 */
    /* 危险仍在：即使调用 Protect_Recover 也不恢复 */
    g_mon = hot;
    Protect_Recover();
    CHECK(Protect_StateName() && g_relay == 0U, "危险未消除时保持 CUTOFF");
}

int main(void)
{
    printf("==================================================\n");
    printf("protect.c 保护状态机单元测试（主机）\n");
    printf("==================================================\n");
    t_startup();
    t_alarm();
    t_threshold_cutoff();
    t_glitch();
    t_sensor_fault_cutoff();
    t_sensor_fault_auto_recover();
    t_threshold_latch();
    t_recover_guard();
    printf("==================================================\n");
    if (failures == 0) {
        printf("ALL PASS\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
