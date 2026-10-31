/**
  ******************************************************************************
  * @file    ntc.c
  * @brief   NTC 测温实现
  *          换算链: ADC码值 -> 分压电阻 -> NTC阻值 -> B参数方程(简化
  *          Steinhart-Hart) -> 开尔文 -> 摄氏度, 再经滑动窗口均值滤波。
  ******************************************************************************
  */
#include "ntc.h"
#include <math.h>

static ADC_HandleTypeDef *s_hadc;
static float s_window[FILTER_WINDOW];
static uint8_t s_win_idx = 0;
static uint8_t s_win_count = 0;

void NTC_Init(ADC_HandleTypeDef *hadc)
{
    s_hadc = hadc;
    for (uint8_t i = 0; i < FILTER_WINDOW; i++) s_window[i] = 25.0f;
}

static float NTC_ReadOnce(void)
{
    HAL_ADC_Start(s_hadc);
    if (HAL_ADC_PollForConversion(s_hadc, 10) != HAL_OK)
        return NAN;
    uint16_t code = (uint16_t)HAL_ADC_GetValue(s_hadc);
    HAL_ADC_Stop(s_hadc);

    if (code == 0 || code >= ADC_MAX)   /* 开路/短路保护 */
        return NAN;

    /* 分压: NTC 在下端(接地), 上端为 10k 上拉, Vntc = Vref * code/4095 */
    float v_ntc = (float)code * ADC_VREF / ADC_MAX;
    float r_ntc = NTC_SERIES_RESISTOR * v_ntc / (ADC_VREF - v_ntc);

    /* B 参数方程: 1/T = 1/T0 + (1/B) * ln(R/R0) */
    float kelvin = 1.0f / (1.0f / NTC_T_NOMINAL +
                   logf(r_ntc / NTC_R_NOMINAL) / NTC_B_VALUE);
    return kelvin - 273.15f;
}

float NTC_ReadTemperature(void)
{
    float t = NTC_ReadOnce();
    if (!isnan(t)) {
        s_window[s_win_idx] = t;
        s_win_idx = (s_win_idx + 1) % FILTER_WINDOW;
        if (s_win_count < FILTER_WINDOW) s_win_count++;
    }
    float sum = 0.0f;
    for (uint8_t i = 0; i < s_win_count; i++) sum += s_window[i];
    return sum / s_win_count;
}
