/**
  ******************************************************************************
  * @file    protect.h
  * @brief   安全保护逻辑：阈值、防抖、故障切断与安全恢复
  ******************************************************************************
  */
#ifndef __PROTECT_H
#define __PROTECT_H
#include "main.h"
typedef enum {
    PROTECT_NORMAL = 0,
    PROTECT_ALARM,
    PROTECT_CUTOFF
} protect_state_t;
void Protect_Init(void);
protect_state_t Protect_Update(const monitor_data_t *mon);
/* 仅当最近一次采样有效且全部回到安全区时才允许恢复 */
void Protect_Recover(void);
const char *Protect_StateName(void);
#endif /* __PROTECT_H */
