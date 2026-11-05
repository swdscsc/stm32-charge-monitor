/**
  ******************************************************************************
  * @file    protect_hal.c
  * @brief   保护逻辑的硬件抽象实现（固件侧）：将继电器/蜂鸣器动作映射到 GPIO
  ******************************************************************************
  */
#include "protect.h"
#include "main.h"   /* 提供继电器/蜂鸣器引脚宏与 HAL_GPIO_WritePin */

void Protect_HAL_RelaySet(uint8_t on)
{
    HAL_GPIO_WritePin(RELAY_GPIO_Port, RELAY_Pin,
                      on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

void Protect_HAL_BuzzerSet(uint8_t on)
{
    HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin,
                      on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
