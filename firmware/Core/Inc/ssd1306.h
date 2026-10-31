/**
  ******************************************************************************
  * @file    ssd1306.h
  * @brief   0.96寸 OLED (SSD1306, 128x64, I2C) 显示驱动
  ******************************************************************************
  */
#ifndef __SSD1306_H
#define __SSD1306_H

#include "main.h"

#define SSD1306_WIDTH   128
#define SSD1306_HEIGHT  64

HAL_StatusTypeDef SSD1306_Init(I2C_HandleTypeDef *hi2c);
void              SSD1306_Clear(void);
void              SSD1306_Fill(uint8_t pattern);
void              SSD1306_Update(void);                    /* 刷显存到屏 */
void              SSD1306_DrawPixel(uint8_t x, uint8_t y, uint8_t color);
void              SSD1306_ShowChar(uint8_t col, uint8_t page, char ch);
void              SSD1306_ShowString(uint8_t col, uint8_t page, const char *str);
void              SSD1306_ShowFloat(uint8_t col, uint8_t page, float val,
                                    uint8_t decimals);
void              SSD1306_ShowBigNumber(uint8_t col, uint8_t page, float val,
                                        uint8_t decimals); /* 8x16 大字号 */

#endif /* __SSD1306_H */
