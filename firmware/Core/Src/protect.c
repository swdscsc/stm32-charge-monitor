/**
  ******************************************************************************
  * @file    protect.c
  * @brief   保护状态机：连续采样确认、传感器故障切断与安全条件恢复
  *
  * 设计原则（答辩可达性）：
  *  - 传感器故障（INA219/NTC 无效）属于"未知即危险"，立即切断；采样恢复且连续
  *    若干周期确认安全后自动恢复，避免单次通信抖动造成永久断电。
  *  - 阈值越限（过温/过压/过流）属于确定性危险，切断后保持闭锁，必须由显式
  *    恢复入口 Protect_Recover() 解除，防止危险条件未消除时自动重合闸。
  *  - 所有硬件动作（继电器/蜂鸣器）经 Protect_HAL_RelaySet/BuzzerSet 抽象，
  *    本文件不依赖 HAL，可直接在 PC 上编译做单元测试。
  ******************************************************************************
  */
#include "protect.h"
#include <math.h>

static protect_state_t s_state = PROTECT_NORMAL;
static uint8_t s_alarm_debounce = 0U, s_cutoff_debounce = 0U;
static uint8_t s_startup_debounce = 0U, s_last_sample_safe = 0U;
static uint8_t s_recover_debounce = 0U;
static uint8_t s_cutoff_cause = CUT_CAUSE_THRESHOLD;

static void RelayOff(void)   { Protect_HAL_RelaySet(0U); g_mon.relay_on = 0U; }
static void RelayOn(void)    { Protect_HAL_RelaySet(1U); g_mon.relay_on = 1U; }
static void BuzzerOn(void)   { Protect_HAL_BuzzerSet(1U); }
static void BuzzerOff(void)  { Protect_HAL_BuzzerSet(0U); }

void Protect_Init(void)
{
    s_state = PROTECT_NORMAL; s_alarm_debounce = 0U; s_cutoff_debounce = 0U;
    s_startup_debounce = 0U; s_last_sample_safe = 0U;
    s_recover_debounce = 0U; s_cutoff_cause = CUT_CAUSE_THRESHOLD;
    RelayOff();              /* 上电默认断开，连续取得有效安全采样后才吸合 */
    BuzzerOff();
    g_mon.alarm_active = 1U;
}

static uint8_t SampleValid(const monitor_data_t *m)
{
    return (uint8_t)(m != NULL && m->sensor_fault == 0U && isfinite(m->temperature) &&
        isfinite(m->bus_voltage) && isfinite(m->current) && isfinite(m->power) &&
        m->temperature >= -40.0f && m->temperature <= 150.0f &&
        m->bus_voltage >= 0.0f && m->bus_voltage <= 26.0f && m->current >= 0.0f);
}

static uint8_t AlarmLimit(const monitor_data_t *m)
{ return (uint8_t)(m->temperature >= TEMP_ALARM_THRESHOLD || m->bus_voltage >= OV_VOLTAGE_THRESHOLD || m->current >= OC_CURRENT_THRESHOLD); }

static uint8_t CutoffLimit(const monitor_data_t *m)
{ return (uint8_t)(m->temperature >= TEMP_CUTOFF_THRESHOLD || m->bus_voltage >= OV_VOLTAGE_THRESHOLD || m->current >= OC_CURRENT_THRESHOLD); }

protect_state_t Protect_Update(const monitor_data_t *mon)
{
    if (!SampleValid(mon)) {
        /* 传感器故障：未知即危险，立即切断并标记为"传感器故障原因" */
        s_state = PROTECT_CUTOFF; s_alarm_debounce = 0U; s_cutoff_debounce = 0U;
        s_startup_debounce = 0U; s_last_sample_safe = 0U; s_recover_debounce = 0U;
        s_cutoff_cause = CUT_CAUSE_SENSOR;
        RelayOff(); BuzzerOn();
    } else {
        uint8_t alarm = AlarmLimit(mon), cutoff = CutoffLimit(mon);
        s_last_sample_safe = (uint8_t)(!alarm && !cutoff);
        switch (s_state) {
        case PROTECT_NORMAL:
            if (cutoff) {
                s_startup_debounce = 0U;
                if (++s_cutoff_debounce >= ALARM_DEBOUNCE_COUNT) {
                    s_state = PROTECT_CUTOFF; s_cutoff_debounce = 0U;
                    s_cutoff_cause = CUT_CAUSE_THRESHOLD;
                    RelayOff(); BuzzerOn();
                }
            } else {
                s_cutoff_debounce = 0U;
                if (alarm) {
                    s_startup_debounce = 0U;
                    if (++s_alarm_debounce >= ALARM_DEBOUNCE_COUNT) {
                        s_state = PROTECT_ALARM; s_alarm_debounce = 0U;
                        BuzzerOn();
                    }
                } else {
                    s_alarm_debounce = 0U;
                    if (!g_mon.relay_on && ++s_startup_debounce >= ALARM_DEBOUNCE_COUNT)
                        RelayOn();
                    BuzzerOff();
                }
            }
            break;
        case PROTECT_ALARM:
            if (cutoff) {
                if (++s_cutoff_debounce >= ALARM_DEBOUNCE_COUNT) {
                    s_state = PROTECT_CUTOFF; s_cutoff_debounce = 0U;
                    s_cutoff_cause = CUT_CAUSE_THRESHOLD;
                    RelayOff(); BuzzerOn();
                }
            } else {
                s_cutoff_debounce = 0U;
                if (mon->temperature < (TEMP_ALARM_THRESHOLD - TEMP_ALARM_HYST) &&
                    mon->bus_voltage < OV_VOLTAGE_THRESHOLD && mon->current < OC_CURRENT_THRESHOLD) {
                    s_state = PROTECT_NORMAL;
                    BuzzerOff();
                }
            }
            break;
        case PROTECT_CUTOFF:
        default:
            RelayOff(); BuzzerOn();
            if (s_cutoff_cause == CUT_CAUSE_SENSOR) {
                /* 传感器故障切断：采样恢复且确认安全后自动恢复（防抖） */
                if (s_last_sample_safe) {
                    if (++s_recover_debounce >= RECOVER_DEBOUNCE_COUNT) {
                        s_state = PROTECT_NORMAL; s_recover_debounce = 0U;
                        s_startup_debounce = 0U;
                        BuzzerOff();   /* 继电器由 NORMAL 启动防抖重新吸合 */
                    }
                } else {
                    s_recover_debounce = 0U;
                }
            }
            /* 阈值越限切断：保持闭锁，仅 Protect_Recover() 可解除 */
            break;
        }
    }
    g_mon.alarm_active = (uint8_t)(s_state != PROTECT_NORMAL);
    if (s_state == PROTECT_CUTOFF) RelayOff();
    return s_state;
}

void Protect_Recover(void)
{
    /* 显式恢复：仅当当前采样有效且安全时才解除闭锁，防止危险未消除时重合闸 */
    if (SampleValid(&g_mon) && s_last_sample_safe != 0U) {
        s_state = PROTECT_NORMAL; s_alarm_debounce = 0U; s_cutoff_debounce = 0U;
        s_startup_debounce = 0U; s_recover_debounce = 0U;
        s_cutoff_cause = CUT_CAUSE_THRESHOLD;
        BuzzerOff();   /* 继电器由 NORMAL 启动防抖重新吸合 */
        g_mon.alarm_active = 0U;
    }
}

const char *Protect_StateName(void)
{
    switch (s_state) { case PROTECT_NORMAL: return "NORMAL"; case PROTECT_ALARM: return "ALARM "; default: return "CUT   "; }
}
