/**
  ******************************************************************************
  * @file    main.c
  * @brief   基于STM32的智能充电监控显示系统 —— 主程序
  * @author  沈炜丹 (202308324143)  指导教师: 王全辉
  *
  * 系统组成: STM32F103C8T6 + INA219(I2C1) + NTC10k(ADC1_IN0) +
  *           0.96寸OLED SSD1306(I2C1) + 有源蜂鸣器 + 继电器 + ESP8266(USART1)
  *
  * 主循环采用固定周期调度(无RTOS, 前后台+时间片轮询):
  *   100ms : 采集 INA219 / NTC -> 滑动滤波 -> 保护逻辑判定
  *   500ms : OLED 界面刷新
  *   1000ms: ESP8266 MQTT 遥测上传(可选)
  ******************************************************************************
  */
#include "main.h"
#include "ina219.h"
#include "ntc.h"
#include "ssd1306.h"
#include "protect.h"
#include "esp8266.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

/* ======================== 外设句柄 ======================== */
I2C_HandleTypeDef  hi2c1;
ADC_HandleTypeDef  hadc1;
UART_HandleTypeDef huart1;

/* ======================== 全局状态 ======================== */
monitor_data_t g_mon = {0};
static uint8_t ina219_ok = 0;    /* INA219 在线标志 */

/* 滑动窗口滤波: 电压/电流 (NTC 在 ntc.c 内部滤波) */
static float v_win[FILTER_WINDOW], i_win[FILTER_WINDOW];
static uint8_t vi_idx = 0, vi_cnt = 0;

static void FilterPush(float v, float i);
static void FilterGet(float *v, float *i);

/* ======================== 时钟配置: HSE 8MHz -> PLL x9 = 72MHz ======================== */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLMUL = RCC_PLL_MUL9;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) Error_Handler();

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV2;   /* 36MHz, I2C2/TIM 上限 */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2) != HAL_OK) Error_Handler();
}

/* ======================== GPIO ======================== */
static void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};

    /* 蜂鸣器 / 继电器 / ESP8266使能: 推挽输出, 初始低电平 */
    gpio.Pin = BUZZER_Pin | RELAY_Pin | ESP8266_EN_Pin;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &gpio);
    HAL_GPIO_WritePin(GPIOA, BUZZER_Pin | RELAY_Pin | ESP8266_EN_Pin, GPIO_PIN_RESET);

    /* SWD 保留: PA13/PA14 不初始化 */
}

/* ======================== I2C1 (PB6/PB7, 400kHz Fast Mode) ======================== */
static void MX_I2C1_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.ClockSpeed = 400000;
    hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK) Error_Handler();
}

/* ======================== ADC1_IN0 (PA0, 独立模式) ======================== */
static void MX_ADC1_Init(void)
{
    ADC_ChannelConfTypeDef ch = {0};

    __HAL_RCC_ADC1_CLK_ENABLE();
    hadc1.Instance = ADC1;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    if (HAL_ADC_Init(&hadc1) != HAL_OK) Error_Handler();

    ch.Channel = ADC_CHANNEL_0;
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_71CYCLES_5;   /* 高阻抗NTC分压, 长采样 */
    if (HAL_ADC_ConfigChannel(&hadc1, &ch) != HAL_OK) Error_Handler();

    /* 校准 (F1 特有, 提升精度) */
    HAL_ADCEx_Calibration_Start(&hadc1);
}

/* ======================== USART1 (ESP8266, 115200) ======================== */
static void MX_USART1_Init(void)
{
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    if (HAL_UART_Init(&huart1) != HAL_OK) Error_Handler();
}

/* ======================== SysTick 节拍 ======================== */
static volatile uint32_t s_ms = 0;
void HAL_SYSTICK_Callback(void) { s_ms++; }
static uint32_t millis(void) { return s_ms; }

/* ======================== OLED 界面 ======================== */
/*
 * 布局 (128x64, 8行x21列 6x8 字体):
 *   Page0: CHARGE MONITOR  P:xx.xW
 *   Page1-2: 电压大字号
 *   Page3-4: 电流大字号
 *   Page5: TEMP / ST
 *   Page6: RELAY / INA 状态
 *   Page7: 报警提示（按需显示）
 */
static void OLED_RenderUI(void)
{
    SSD1306_Clear();
    SSD1306_ShowString(0, 0, "CHARGE MONITOR");
    SSD1306_ShowString(15, 0, "P:");
    SSD1306_ShowFloat(17, 0, g_mon.power, 1);

    /* 大数字按上下两行排版：避免第二组数字越过128px屏幕右边界 */
    SSD1306_ShowBigNumber(0, 1, g_mon.bus_voltage, 2);
    SSD1306_ShowString(11, 1, "V");
    SSD1306_ShowBigNumber(0, 3, g_mon.current, 3);
    SSD1306_ShowString(11, 3, "A");

    SSD1306_ShowString(0, 5, "TEMP:");
    SSD1306_ShowFloat(5, 5, g_mon.temperature, 1);
    SSD1306_ShowString(12, 5, "C ST:");
    SSD1306_ShowString(17, 5, Protect_StateName());

    SSD1306_ShowString(0, 6, g_mon.relay_on ? "[RELAY ON ]" : "[RELAY OFF]");
    SSD1306_ShowString(12, 6, ina219_ok ? "[INA OK]" : "[INA ER]");

    if (g_mon.alarm_active) {
        SSD1306_ShowString(0, 7, "** WARNING! CHECK **");
    }
    SSD1306_Update();
}

/* ======================== 主函数 ======================== */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_I2C1_Init();
    MX_ADC1_Init();
    MX_USART1_Init();

    NTC_Init(&hadc1);
    ina219_ok = (INA219_Init(&hi2c1) == HAL_OK);
    SSD1306_Init(&hi2c1);
    Protect_Init();
#if ENABLE_ESP8266
    ESP8266_Init(&huart1);
#endif

    /* 开机自检画面 */
    SSD1306_Clear();
    SSD1306_ShowString(0, 3, "SELF-TEST...");
    SSD1306_Update();
    HAL_Delay(1000);

    uint32_t t_sample = 0, t_oled = 0, t_iot = 0;

    while (1) {
        uint32_t now = millis();

        /* ---- 100ms: 采集 + 保护 ---- */
        if (now - t_sample >= SAMPLE_PERIOD_MS) {
            t_sample = now;

            float v = 0.0f, i = 0.0f, p = 0.0f;
            g_mon.sensor_fault = 0U;
            if (ina219_ok && INA219_ReadAll(&v, &i, &p) == HAL_OK) {
                FilterPush(v, i);
                FilterGet(&g_mon.bus_voltage, &g_mon.current);
                g_mon.power = g_mon.bus_voltage * g_mon.current;
            } else {
                g_mon.sensor_fault = 1U; /* INA219失联：本周期立即进入故障切断 */
                ina219_ok = 0U;
                if (INA219_Init(&hi2c1) == HAL_OK) ina219_ok = 1U;
            }

            float temperature = NTC_ReadTemperature();
            if (isfinite(temperature)) {
                g_mon.temperature = temperature;
            } else {
                g_mon.sensor_fault = 1U; /* NTC无效：禁止使用旧温度继续供电 */
            }
            Protect_Update(&g_mon);
        }

        /* ---- 500ms: 显示刷新 ---- */
        if (now - t_oled >= OLED_REFRESH_MS) {
            t_oled = now;
            OLED_RenderUI();
        }

        /* ---- 1000ms: 物联网上传 ---- */
#if ENABLE_ESP8266
        if (now - t_iot >= IOT_UPLOAD_MS) {
            t_iot = now;
            ESP8266_SendData(&g_mon);
        }
#endif
    }
}

/* ---- 滑动窗口均值滤波 ---- */
static void FilterPush(float v, float i)
{
    v_win[vi_idx] = v;
    i_win[vi_idx] = i;
    vi_idx = (vi_idx + 1) % FILTER_WINDOW;
    if (vi_cnt < FILTER_WINDOW) vi_cnt++;
}

static void FilterGet(float *v, float *i)
{
    float vs = 0, is = 0;
    for (uint8_t k = 0; k < vi_cnt; k++) { vs += v_win[k]; is += i_win[k]; }
    *v = vs / vi_cnt;
    *i = is / vi_cnt;
}

/* ======================== HAL 底层初始化 (CubeMX 生成习惯) ======================== */
void HAL_MspInit(void)
{
    __HAL_RCC_AFIO_CLK_ENABLE();
    __HAL_RCC_PWR_CLK_ENABLE();
}

void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c)
{
    if (hi2c->Instance == I2C1) {
        __HAL_RCC_I2C1_CLK_ENABLE();
        GPIO_InitTypeDef gpio = {0};
        gpio.Pin = GPIO_PIN_6 | GPIO_PIN_7;
        gpio.Mode = GPIO_MODE_AF_OD;         /* I2C 开漏复用 */
        gpio.Pull = GPIO_PULLUP;
        gpio.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOB, &gpio);
    }
}

void HAL_ADC_MspInit(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        GPIO_InitTypeDef gpio = {0};
        gpio.Pin = NTC_ADC_Pin;
        gpio.Mode = GPIO_MODE_ANALOG;        /* PA0 模拟输入 */
        gpio.Pull = GPIO_NOPULL;
        HAL_GPIO_Init(GPIOA, &gpio);
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1) {
        __HAL_RCC_USART1_CLK_ENABLE();
        GPIO_InitTypeDef gpio = {0};
        gpio.Pin = GPIO_PIN_9;               /* TX 复用推挽 */
        gpio.Mode = GPIO_MODE_AF_PP;
        gpio.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &gpio);
        gpio.Pin = GPIO_PIN_10;              /* RX 浮空输入 */
        gpio.Mode = GPIO_MODE_INPUT;
        gpio.Pull = GPIO_PULLUP;
        HAL_GPIO_Init(GPIOA, &gpio);
    }
}

void Error_Handler(void)
{
    __disable_irq();
    while (1) {
        /* 致命错误: 快闪蜂鸣器提示 */
        HAL_GPIO_TogglePin(BUZZER_GPIO_Port, BUZZER_Pin);
        for (volatile uint32_t d = 0; d < 200000; d++) {}
    }
}
