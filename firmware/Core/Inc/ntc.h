/**
  ******************************************************************************
  * @file    ntc.h
  * @brief   NTC热敏电阻测温（ADC采样 + B参数方程）
  ******************************************************************************
  */
#ifndef __NTC_H
#define __NTC_H
#include "main.h"
#define NTC_B_VALUE          3950.0f
#define NTC_R_NOMINAL        10000.0f
#define NTC_T_NOMINAL        298.15f
#define NTC_SERIES_RESISTOR  10000.0f
#define ADC_VREF             3.3f
#define ADC_MAX              4095.0f
void NTC_Init(ADC_HandleTypeDef *hadc);
/* 返回 NAN 表示 ADC/NTC 采样无效；调用方必须按传感器故障处理 */
float NTC_ReadTemperature(void);
#endif /* __NTC_H */
