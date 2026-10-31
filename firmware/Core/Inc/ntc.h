/**
  ******************************************************************************
  * @file    ntc.h
  * @brief   NTC 热敏电阻测温 (ADC采样 + Steinhart-Hart 方程换算)
  ******************************************************************************
  */
#ifndef __NTC_H
#define __NTC_H

#include "main.h"

#define NTC_B_VALUE          3950.0f   /* B值 (MF52-103 3435型取3950档)  */
#define NTC_R_NOMINAL        10000.0f  /* 25℃ 标称阻值 10kΩ              */
#define NTC_T_NOMINAL        298.15f   /* 25℃ 开尔文温度                 */
#define NTC_SERIES_RESISTOR  10000.0f  /* 上拉分压电阻 10kΩ               */
#define ADC_VREF             3.3f
#define ADC_MAX              4095.0f

void  NTC_Init(ADC_HandleTypeDef *hadc);
float NTC_ReadTemperature(void);   /* 带滑动窗口滤波, 返回摄氏温度 */

#endif /* __NTC_H */
