/**
  ******************************************************************************
  * @file    protect.c
  * @brief   保护逻辑实现
  *          设计要点: 1) 任何超限必须连续 ALARM_DEBOUNCE_COUNT 次采样
 *          均成立才确认, 防止毛刺误触发; 2) 进入 CUTOFF 后继电器闭锁,
 *          需温度回降到安全区并手动恢复, 避免热振荡反复通断。
  ******************************************************************************
  */
#include "protect.h"

static protect_state_t s_state = PROTECT_NORMAL;
static uint8_t s_debounce = 0;

void Protect_Init(void)
{
    s_state = PROTECT_NORMAL;
    s_debounce = 0;
    HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin, GPIO_PIN_SET);    /* 吸合 */
    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
}

/* 返回 1 表示该采样点存在超限 */
static uint8_t CheckLimits(const monitor_data_t *mon)
{
    if (mon->temperature >= TEMP_CUTOFF_THRESHOLD) return 1;
    if (mon->temperature >= TEMP_ALARM_THRESHOLD)  return 1;
    if (mon->bus_voltage   >= OV_VOLTAGE_THRESHOLD) return 1;
    if (mon->current       >= OC_CURRENT_THRESHOLD) return 1;
    return 0;
}

protect_state_t Protect_Update(const monitor_data_t *mon)
{
    uint8_t over = CheckLimits(mon);

    switch (s_state) {
    case PROTECT_NORMAL:
        if (over) {
            if (++s_debounce >= ALARM_DEBOUNCE_COUNT) {
                s_debounce = 0;
                if (mon->temperature >= TEMP_CUTOFF_THRESHOLD ||
                    mon->bus_voltage >= OV_VOLTAGE_THRESHOLD ||
                    mon->current >= OC_CURRENT_THRESHOLD) {
                    /* 危险级: 切断低压负载 */
                    HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin, GPIO_PIN_RESET);
                    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);
                    s_state = PROTECT_CUTOFF;
                } else {
                    /* 警告级: 仅蜂鸣提示 */
                    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);
                    s_state = PROTECT_ALARM;
                }
            }
        } else {
            s_debounce = 0;
            HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
        }
        break;

    case PROTECT_ALARM:
        if (!over) {
            HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
            s_state = PROTECT_NORMAL;
        } else if (mon->temperature >= TEMP_CUTOFF_THRESHOLD ||
                   mon->bus_voltage >= OV_VOLTAGE_THRESHOLD ||
                   mon->current >= OC_CURRENT_THRESHOLD) {
            HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin, GPIO_PIN_RESET);
            s_state = PROTECT_CUTOFF;
        }
        break;

    case PROTECT_CUTOFF:
        /* 闭锁: 蜂鸣器以 2Hz 慢闪提示, 继电器保持断开 */
        HAL_GPIO_TogglePin(BUZZER_GPIO_Port, BUZZER_Pin);
        break;
    }

    g_mon.alarm_active = (s_state != PROTECT_NORMAL);
    g_mon.relay_on = (s_state != PROTECT_CUTOFF);
    return s_state;
}

void Protect_Recover(void)
{
    if (s_state == PROTECT_CUTOFF) {
        s_state = PROTECT_NORMAL;
        s_debounce = 0;
        HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin, GPIO_PIN_SET);
    }
}

const char *Protect_StateName(void)
{
    switch (s_state) {
    case PROTECT_NORMAL: return "NORMAL";
    case PROTECT_ALARM:  return "ALARM ";
    default:             return "CUT   ";
    }
}
