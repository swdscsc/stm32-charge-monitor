/**
  ******************************************************************************
  * @file    protect.c
  * @brief   保护状态机：连续采样确认、传感器故障切断与安全条件恢复
  ******************************************************************************
  */
#include "protect.h"
#include <math.h>
static protect_state_t s_state = PROTECT_NORMAL;
static uint8_t s_alarm_debounce = 0U, s_cutoff_debounce = 0U;
static uint8_t s_startup_debounce = 0U, s_last_sample_safe = 0U;
static void RelayOff(void) { HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin, GPIO_PIN_RESET); g_mon.relay_on = 0U; }
static void RelayOn(void) { HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin, GPIO_PIN_SET); g_mon.relay_on = 1U; }
void Protect_Init(void)
{
    s_state = PROTECT_NORMAL; s_alarm_debounce = 0U; s_cutoff_debounce = 0U;
    s_startup_debounce = 0U; s_last_sample_safe = 0U;
    RelayOff(); /* 上电默认断开，连续取得有效安全采样后才吸合 */
    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
    g_mon.alarm_active = 1U;
}
static uint8_t SampleValid(const monitor_data_t *m)
{
    return (uint8_t)(m != NULL && m->sensor_fault == 0U && isfinite(m->temperature) &&
        isfinite(m->bus_voltage) && isfinite(m->current) && isfinite(m->power) &&
        m->temperature >= -40.0f && m->temperature <= 150.0f &&
        m->bus_voltage >= 0.0f && m->bus_voltage <= 32.0f && m->current >= 0.0f);
}
static uint8_t AlarmLimit(const monitor_data_t *m)
{ return (uint8_t)(m->temperature >= TEMP_ALARM_THRESHOLD || m->bus_voltage >= OV_VOLTAGE_THRESHOLD || m->current >= OC_CURRENT_THRESHOLD); }
static uint8_t CutoffLimit(const monitor_data_t *m)
{ return (uint8_t)(m->temperature >= TEMP_CUTOFF_THRESHOLD || m->bus_voltage >= OV_VOLTAGE_THRESHOLD || m->current >= OC_CURRENT_THRESHOLD); }
protect_state_t Protect_Update(const monitor_data_t *mon)
{
    if (!SampleValid(mon)) {
        s_state = PROTECT_CUTOFF; s_alarm_debounce = 0U; s_cutoff_debounce = 0U;
        s_startup_debounce = 0U; s_last_sample_safe = 0U; RelayOff();
        HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);
    } else {
        uint8_t alarm = AlarmLimit(mon), cutoff = CutoffLimit(mon);
        s_last_sample_safe = (uint8_t)(!alarm && !cutoff);
        switch (s_state) {
        case PROTECT_NORMAL:
            if (cutoff) {
                s_startup_debounce = 0U;
                if (++s_cutoff_debounce >= ALARM_DEBOUNCE_COUNT) {
                    s_state = PROTECT_CUTOFF; s_cutoff_debounce = 0U; RelayOff();
                    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);
                }
            } else {
                s_cutoff_debounce = 0U;
                if (alarm) {
                    s_startup_debounce = 0U;
                    if (++s_alarm_debounce >= ALARM_DEBOUNCE_COUNT) {
                        s_state = PROTECT_ALARM; s_alarm_debounce = 0U;
                        HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);
                    }
                } else {
                    s_alarm_debounce = 0U;
                    if (!g_mon.relay_on && ++s_startup_debounce >= ALARM_DEBOUNCE_COUNT) RelayOn();
                    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
                }
            }
            break;
        case PROTECT_ALARM:
            if (cutoff) {
                if (++s_cutoff_debounce >= ALARM_DEBOUNCE_COUNT) {
                    s_state = PROTECT_CUTOFF; s_cutoff_debounce = 0U; RelayOff();
                }
            } else {
                s_cutoff_debounce = 0U;
                if (mon->temperature < (TEMP_ALARM_THRESHOLD - TEMP_ALARM_HYST) &&
                    mon->bus_voltage < OV_VOLTAGE_THRESHOLD && mon->current < OC_CURRENT_THRESHOLD) {
                    s_state = PROTECT_NORMAL;
                    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
                }
            }
            break;
        case PROTECT_CUTOFF:
        default:
            RelayOff(); HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);
            break;
        }
    }
    g_mon.alarm_active = (uint8_t)(s_state != PROTECT_NORMAL);
    if (s_state == PROTECT_CUTOFF) RelayOff();
    return s_state;
}
void Protect_Recover(void)
{
    if (s_state == PROTECT_CUTOFF && s_last_sample_safe != 0U) {
        s_state = PROTECT_NORMAL; s_alarm_debounce = 0U; s_cutoff_debounce = 0U;
        s_startup_debounce = 0U; HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
        RelayOn(); g_mon.alarm_active = 0U;
    }
}
const char *Protect_StateName(void)
{
    switch (s_state) { case PROTECT_NORMAL: return "NORMAL"; case PROTECT_ALARM: return "ALARM "; default: return "CUT   "; }
}
