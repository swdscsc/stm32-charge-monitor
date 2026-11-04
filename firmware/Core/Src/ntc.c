/**
  ******************************************************************************
  * @file    ntc.c
  * @brief   NTC测温：ADC采样、B参数换算与滑动窗口滤波
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
    s_win_idx = 0;
    s_win_count = 0;
    for (uint8_t i = 0; i < FILTER_WINDOW; i++) s_window[i] = 0.0f;
}

static float NTC_ReadOnce(void)
{
    uint16_t code;
    if (s_hadc == NULL) return NAN;
    if (HAL_ADC_Start(s_hadc) != HAL_OK) return NAN;
    if (HAL_ADC_PollForConversion(s_hadc, 10) != HAL_OK) {
        (void)HAL_ADC_Stop(s_hadc);
        return NAN;
    }
    code = (uint16_t)HAL_ADC_GetValue(s_hadc);
    (void)HAL_ADC_Stop(s_hadc);

    /* ADC端点表示分压短路/开路，不能用旧值伪装为有效温度 */
    if (code == 0U || code >= (uint16_t)ADC_MAX) return NAN;

    /* NTC在下端：3.3V -> 10k上拉 -> ADC -> NTC -> GND */
    float v_ntc = (float)code * ADC_VREF / ADC_MAX;
    float denominator = ADC_VREF - v_ntc;
    if (denominator <= 0.0f) return NAN;
    float r_ntc = NTC_SERIES_RESISTOR * v_ntc / denominator;
    if (!isfinite(r_ntc) || r_ntc <= 0.0f) return NAN;

    float inv_kelvin = 1.0f / NTC_T_NOMINAL +
                       logf(r_ntc / NTC_R_NOMINAL) / NTC_B_VALUE;
    if (!isfinite(inv_kelvin) || inv_kelvin <= 0.0f) return NAN;
    float temperature = (1.0f / inv_kelvin) - 273.15f;
    return isfinite(temperature) ? temperature : NAN;
}

float NTC_ReadTemperature(void)
{
    float t = NTC_ReadOnce();
    if (!isfinite(t)) return NAN;

    s_window[s_win_idx] = t;
    s_win_idx = (uint8_t)((s_win_idx + 1U) % FILTER_WINDOW);
    if (s_win_count < FILTER_WINDOW) s_win_count++;

    if (s_win_count == 0U) return NAN;
    float sum = 0.0f;
    for (uint8_t i = 0; i < s_win_count; i++) sum += s_window[i];
    return sum / (float)s_win_count;
}
