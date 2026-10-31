/**
  ******************************************************************************
  * @file    esp8266.h
  * @brief   ESP8266 物联网数据上传 (USART1, MQTT, 编译开关可裁剪)
  ******************************************************************************
  */
#ifndef __ESP8266_H
#define __ESP8266_H

#include "main.h"

#define ENABLE_ESP8266   1     /* 置0可完全裁剪物联网功能 */

#if ENABLE_ESP8266

#define ESP_TOPIC_PREFIX  "charge/monitor"
#define ESP_WIFI_SSID     "your-ssid"
#define ESP_WIFI_PASS     "your-password"
#define ESP_MQTT_BROKER   "broker.emqx.io"   /* 公共MQTT服务器 */

void ESP8266_Init(UART_HandleTypeDef *huart);
void ESP8266_SendData(const monitor_data_t *mon);  /* 每1s调用 */

#endif
#endif /* __ESP8266_H */
