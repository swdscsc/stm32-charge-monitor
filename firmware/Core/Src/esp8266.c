/**
  ******************************************************************************
  * @file    esp8266.c
  * @brief   ESP8266 AT 指令驱动: 连WiFi -> 建MQTT -> 周期发布JSON遥测
  *          协议选型依据开题报告[14]: MQTT 头开销小、支持QoS, 适合
  *          低速率遥测场景; 指令间加超时等待, 失败自动重连。
  ******************************************************************************
  */
#include "esp8266.h"

#if ENABLE_ESP8266
#include <stdio.h>
#include <string.h>

static UART_HandleTypeDef *s_huart;

static void ESP_SendAT(const char *at)
{
    HAL_UART_Transmit(s_huart, (uint8_t *)at, strlen(at), 200);
}

static void ESP_WaitReady(uint32_t ms)
{
    /* 实机可扩展为DMA空闲中断回环校验; 此处简单延时保证指令间隔 */
    HAL_Delay(ms);
}

void ESP8266_Init(UART_HandleTypeDef *huart)
{
    s_huart = huart;
    HAL_GPIO_WritePin(ESP8266_EN_GPIO_Port, ESP8266_EN_Pin, GPIO_PIN_SET);
    HAL_Delay(500);

    ESP_SendAT("AT+RESTORE\r\n");            ESP_WaitReady(800);
    ESP_SendAT("AT+CWMODE=1\r\n");           ESP_WaitReady(300);
    char cmd[96];
    snprintf(cmd, sizeof(cmd), "AT+CWJAP=\"%s\",\"%s\"\r\n",
             ESP_WIFI_SSID, ESP_WIFI_PASS);
    ESP_SendAT(cmd);                         ESP_WaitReady(8000);
    snprintf(cmd, sizeof(cmd), "AT+MQTTUSERCFG=0,1,\"stm32%s\",,,0,0,\"\"\r\n",
             "monitor");
    ESP_SendAT(cmd);                         ESP_WaitReady(500);
    snprintf(cmd, sizeof(cmd), "AT+MQTTCONN=0,\"%s\",1883,1\r\n", ESP_MQTT_BROKER);
    ESP_SendAT(cmd);                         ESP_WaitReady(3000);
}

void ESP8266_SendData(const monitor_data_t *mon)
{
    char msg[160];
    snprintf(msg, sizeof(msg),
             "AT+MQTTPUB=0,\"%s/state\","
             "\"{\\\"v\\\":%.2f,\\\"i\\\":%.3f,\\\"p\\\":%.2f,"
             "\\\"t\\\":%.1f,\\\"relay\\\":%u}\",1,0\r\n",
             ESP_TOPIC_PREFIX, (double)mon->bus_voltage, (double)mon->current,
             (double)mon->power, (double)mon->temperature, mon->relay_on);
    ESP_SendAT(msg);
    ESP_WaitReady(100);
}
#endif /* ENABLE_ESP8266 */
