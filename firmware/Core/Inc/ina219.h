/**
  ******************************************************************************
  * @file    ina219.h
  * @brief   INA219电压/电流/功率监测驱动（I2C，依据TI SBOS499E）
  ******************************************************************************
  */
#ifndef __INA219_H
#define __INA219_H
#include "main.h"
#define INA219_REG_CONFIG        0x00
#define INA219_REG_SHUNTVOLTAGE  0x01
#define INA219_REG_BUSVOLTAGE    0x02
#define INA219_REG_POWER         0x03
#define INA219_REG_CURRENT       0x04
#define INA219_REG_CALIBRATION   0x05
/* 32V总线档/±320mV分流档/128次平均/连续测量；实际安全工作范围须核验模块规格 */
#define INA219_CONFIG_VALUE      0x3F9F
#define INA219_R_SHUNT           0.1f
#define INA219_CAL_VALUE         4096
#define INA219_CURRENT_LSB_MA    0.8f
#define INA219_POWER_LSB_MW      16.0f
HAL_StatusTypeDef INA219_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef INA219_ReadAll(float *voltage, float *current, float *power);
uint8_t INA219_IsReady(void);
#endif /* __INA219_H */
