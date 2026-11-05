/**
  ******************************************************************************
  * @file    main.h
  * @brief   基于STM32的智能充电监控显示系统 - 引脚定义与全局配置
  * @note    主控: STM32F103C8T6 (LQFP48, 72MHz)
  ******************************************************************************
  */
#ifndef __MAIN_H
#define __MAIN_H
#ifdef __cplusplus
extern "C" {
#endif
#include "stm32f1xx_hal.h"
#include "protect_cfg.h"   /* 监测数据结构与保护阈值（与保护逻辑共用，单一定义） */

/* I2C1: PB6-SCL, PB7-SDA; ADC1_IN0: PA0; USART1: PA9/PA10 */
#define NTC_ADC_Pin          GPIO_PIN_0
#define NTC_ADC_GPIO_Port    GPIOA
#define BUZZER_Pin           GPIO_PIN_1
#define BUZZER_GPIO_Port     GPIOA
#define RELAY_Pin            GPIO_PIN_2 /* 高电平吸合；低电平断开，需按实物模块核验 */
#define RELAY_GPIO_Port      GPIOA
#define ESP8266_EN_Pin       GPIO_PIN_3
#define ESP8266_EN_GPIO_Port GPIOA

#define SAMPLE_PERIOD_MS       100
#define OLED_REFRESH_MS        500
#define IOT_UPLOAD_MS          1000
#define FILTER_WINDOW          8
#define INA219_ADDR            (0x40 << 1)
#define SSD1306_ADDR           (0x78)

/* 显式恢复请求标志：由本地/远程复位指令置位，主循环消费并调用 Protect_Recover() */
extern volatile uint8_t g_recover_req;
void Error_Handler(void);
#ifdef __cplusplus
}
#endif
#endif /* __MAIN_H */
