/**
  ******************************************************************************
  * @file    main.h
  * @brief   基于STM32的智能充电监控显示系统 - 引脚定义与全局配置
  * @author  沈炜丹 (202308324143)
  * @note    主控: STM32F103C8T6 (LQFP48, 72MHz)
  ******************************************************************************
  */
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"

/* ======================== 引脚分配 (CubeMX 配置) ======================== */
/* I2C1: PB6-SCL, PB7-SDA  ->  OLED(SSD1306, 0x78) + INA219(0x40) */
/* ADC1_IN0: PA0           ->  NTC 热敏电阻分压点                    */
/* USART1: PA9-TX, PA10-RX ->  ESP8266 (115200bps, 可选)            */
#define NTC_ADC_Pin          GPIO_PIN_0
#define NTC_ADC_GPIO_Port    GPIOA
#define BUZZER_Pin           GPIO_PIN_1            /* 有源蜂鸣器(高电平响) */
#define BUZZER_GPIO_Port     GPIOA
#define RELAY_Pin            GPIO_PIN_2            /* 继电器IN(高电吸合)   */
#define RELAY_GPIO_Port      GPIOA
#define ESP8266_EN_Pin       GPIO_PIN_3            /* ESP8266 使能/复位    */
#define ESP8266_EN_GPIO_Port GPIOA

/* ======================== 安全阈值配置 ======================== */
#define TEMP_ALARM_THRESHOLD   45.0f  /* 外壳温度报警阈值 (℃)  */
#define TEMP_CUTOFF_THRESHOLD  60.0f  /* 外壳温度切断阈值 (℃)  */
#define OV_VOLTAGE_THRESHOLD   21.0f  /* 输出过压阈值 (V)       */
#define OC_CURRENT_THRESHOLD   3.3f   /* 输出过流阈值 (A)       */
#define ALARM_DEBOUNCE_COUNT   5      /* 连续超限采样次数防抖   */

/* ======================== 系统节拍 ======================== */
#define SAMPLE_PERIOD_MS       100    /* 采集周期 100ms         */
#define OLED_REFRESH_MS        500    /* OLED 刷新周期 500ms    */
#define IOT_UPLOAD_MS          1000   /* 物联网上传周期 1s      */
#define FILTER_WINDOW          8      /* 滑动窗口滤波长度       */

/* 传感器 I2C 地址 (7位地址左移1位后的8位写地址) */
#define INA219_ADDR            (0x40 << 1)
#define SSD1306_ADDR           (0x78)

/* 全局公共数据结构 */
typedef struct {
    float bus_voltage;      /* 负载侧电压 V  */
    float current;          /* 负载侧电流 A  */
    float power;            /* 实时功率 W    */
    float temperature;      /* 外壳温度 ℃    */
    uint8_t  alarm_active;  /* 蜂鸣器报警中  */
    uint8_t  relay_on;      /* 继电器状态    */
} monitor_data_t;

extern monitor_data_t g_mon;

void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
