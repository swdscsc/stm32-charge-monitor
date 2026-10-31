/**
  ******************************************************************************
  * @file    ina219.c
  * @brief   INA219 驱动实现
  *          测量原理: 负载电流 Is = Vshunt / Rshunt, 由标定寄存器换算,
  *          总线电压以 4mV LSB 直接读取, 功率 P = Vbus * I。
  ******************************************************************************
  */
#include "ina219.h"

static I2C_HandleTypeDef *s_hi2c;

static HAL_StatusTypeDef INA219_WriteReg(uint8_t reg, uint16_t val)
{
    uint8_t buf[3];
    buf[0] = reg;
    buf[1] = (uint8_t)(val >> 8);
    buf[2] = (uint8_t)(val & 0xFF);
    return HAL_I2C_Master_Transmit(s_hi2c, INA219_ADDR, buf, 3, 100);
}

static HAL_StatusTypeDef INA219_ReadReg(uint8_t reg, uint16_t *val)
{
    uint8_t buf[2];
    HAL_StatusTypeDef st = HAL_I2C_Master_Transmit(s_hi2c, INA219_ADDR, &reg, 1, 100);
    if (st != HAL_OK) return st;
    st = HAL_I2C_Master_Receive(s_hi2c, INA219_ADDR, buf, 2, 100);
    if (st != HAL_OK) return st;
    *val = ((uint16_t)buf[0] << 8) | buf[1];
    return HAL_OK;
}

HAL_StatusTypeDef INA219_Init(I2C_HandleTypeDef *hi2c)
{
    s_hi2c = hi2c;
    uint16_t id = 0;
    /* 复位后校验芯片在位: 写标定寄存器并回读 */
    if (INA219_WriteReg(INA219_REG_CALIBRATION, INA219_CAL_VALUE) != HAL_OK)
        return HAL_ERROR;
    if (INA219_ReadReg(INA219_REG_CALIBRATION, &id) != HAL_OK || id != INA219_CAL_VALUE)
        return HAL_ERROR;
    return INA219_WriteReg(INA219_REG_CONFIG, INA219_CONFIG_VALUE);
}

uint8_t INA219_IsReady(void)
{
    return (HAL_I2C_IsDeviceReady(s_hi2c, INA219_ADDR, 2, 50) == HAL_OK);
}

HAL_StatusTypeDef INA219_ReadAll(float *voltage, float *current, float *power)
{
    uint16_t raw_bus = 0, raw_power = 0, raw_cur = 0;

    if (INA219_ReadReg(INA219_REG_BUSVOLTAGE, &raw_bus) != HAL_OK)
        return HAL_ERROR;
    if (INA219_ReadReg(INA219_REG_POWER, &raw_power) != HAL_OK)
        return HAL_ERROR;
    if (INA219_ReadReg(INA219_REG_CURRENT, &raw_cur) != HAL_OK)
        return HAL_ERROR;

    /* 总线电压: 16位寄存器右移3位丢状态位, 13位有效, LSB=4mV (SBOS499E 8.6.3) */
    *voltage = (float)((raw_bus >> 3) & 0x1FFF) * 0.004f;

    /* 电流为有符号数, LSB 由标定寄存器决定 */
    int16_t cur = (int16_t)raw_cur;
    *current = (float)cur * INA219_CURRENT_LSB_MA / 1000.0f;
    if (*current < 0.0f) *current = 0.0f;

    /* 功率寄存器 LSB = 20 * Current_LSB */
    *power = (float)raw_power * INA219_POWER_LSB_MW / 1000.0f;

    return HAL_OK;
}
