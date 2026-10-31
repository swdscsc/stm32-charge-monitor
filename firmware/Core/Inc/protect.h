/**
  ******************************************************************************
  * @file    protect.h
  * @brief   安全保护逻辑: 阈值判断 + 连续N次防抖 + 继电器/蜂鸣器执行
  ******************************************************************************
  */
#ifndef __PROTECT_H
#define __PROTECT_H

#include "main.h"

typedef enum {
    PROTECT_NORMAL = 0,   /* 正常充电         */
    PROTECT_ALARM,        /* 超温/超限报警    */
    PROTECT_CUTOFF        /* 已切断负载       */
} protect_state_t;

void             Protect_Init(void);
protect_state_t  Protect_Update(const monitor_data_t *mon);  /* 每100ms调用 */
void             Protect_Recover(void);                      /* 手动恢复    */
const char      *Protect_StateName(void);

#endif /* __PROTECT_H */
