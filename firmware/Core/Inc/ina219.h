/**
  ******************************************************************************
  * @file    ina219.h
  * @brief   INA219 电压/电流/功率监测驱动 (I2C, 依据 TI SBOS499E 数据手册)
  ******************************************************************************
  */
#ifndef __INA219_H
#define __INA219_H

#include "main.h"

/* INA219 寄存器地址 (Table 1, SBOS499E) */
#define INA219_REG_CONFIG        0x00
#define INA219_REG_SHUNTVOLTAGE  0x01
#define INA219_REG_BUSVOLTAGE    0x02
#define INA219_REG_POWER         0x03
#define INA219_REG_CURRENT       0x04
#define INA219_REG_CALIBRATION   0x05

/* 配置: 128样本平均, 总转换时间约 42ms, 量程32V/320mV, 连续测量 */
#define INA219_CONFIG_VALUE      0x3F9F

/* 分流电阻与标定 (0.1Ω / R100, 1%精度) */
#define INA219_R_SHUNT           0.1f
#define INA219_CAL_VALUE         4096        /* = trunc(0.00512/(0.1*0.00008)) */
#define INA219_CURRENT_LSB_MA    0.8f        /* mA/bit */
#define INA219_POWER_LSB_MW      16.0f       /* mA*20  */

HAL_StatusTypeDef INA219_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef INA219_ReadAll(float *voltage, float *current, float *power);
uint8_t           INA219_IsReady(void);

#endif /* __INA219_H */
