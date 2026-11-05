/**
  ******************************************************************************
  * @file    protect.h
  * @brief   安全保护逻辑：阈值、防抖、故障切断与安全恢复
  ******************************************************************************
  */
#ifndef __PROTECT_H
#define __PROTECT_H
#include "protect_cfg.h"

typedef enum {
    PROTECT_NORMAL = 0,
    PROTECT_ALARM,
    PROTECT_CUTOFF
} protect_state_t;

/* 全局监测数据（由采集层写入，保护层读取并镜像继电器/告警状态） */
extern monitor_data_t g_mon;

/* 硬件抽象：由保护逻辑调用，固件侧在 protect_hal.c 中实现（写 GPIO），
   主机单元测试侧用桩函数替换。 */
void Protect_HAL_RelaySet(uint8_t on);
void Protect_HAL_BuzzerSet(uint8_t on);

void Protect_Init(void);
protect_state_t Protect_Update(const monitor_data_t *mon);

/* 显式恢复入口：仅当最近一次采样有效且全部回到安全区时才允许解除闭锁。
   阈值越限切断为闭锁设计，必须显式调用本函数（如远程/本地复位指令）方可恢复；
   传感器故障切断则在采样恢复后由 Protect_Update 自动恢复。 */
void Protect_Recover(void);

const char *Protect_StateName(void);
#endif /* __PROTECT_H */
