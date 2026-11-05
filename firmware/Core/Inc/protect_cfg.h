/**
  ******************************************************************************
  * @file    protect_cfg.h
  * @brief   安全保护逻辑的配置与数据结构（不依赖 HAL，便于主机单元测试）
  ******************************************************************************
  */
#ifndef __PROTECT_CFG_H
#define __PROTECT_CFG_H
#include <stdint.h>

/* 监测数据结构：保护与采集共用，不含任何 HAL 类型，可在 PC 上直接编译 */
typedef struct {
    float bus_voltage;     /* 总线电压 (V) */
    float current;         /* 负载电流 (A) */
    float power;           /* 功率 (W) */
    float temperature;     /* NTC 温度 (℃) */
    uint8_t sensor_fault;  /* 任一关键传感器无效时置 1；保护逻辑立即切断 */
    uint8_t alarm_active;  /* 当前处于告警/切断状态 */
    uint8_t relay_on;      /* 继电器实际状态镜像 */
} monitor_data_t;

/* ---------------- 安全阈值 ---------------- */
#define TEMP_ALARM_THRESHOLD   45.0f   /* 温度告警阈值 (℃) */
#define TEMP_CUTOFF_THRESHOLD  60.0f   /* 温度切断阈值 (℃) */
#define TEMP_ALARM_HYST        3.0f   /* 温度告警回差 (℃) */
#define OV_VOLTAGE_THRESHOLD   21.0f  /* 过压切断阈值 (V)，须结合实际母线额定值复核 */
#define OC_CURRENT_THRESHOLD   2.5f   /* 过流切断阈值 (A)，须结合分流器/模块额定值复核 */
#define ALARM_DEBOUNCE_COUNT   5U     /* 告警/切断防抖周期数 (每周期 100ms) */
#define RECOVER_DEBOUNCE_COUNT 5U     /* 传感器故障自动恢复防抖周期数 */

/* 切断原因：用于区分闭锁行为 */
#define CUT_CAUSE_THRESHOLD    0U     /* 阈值越限切断：保持闭锁，需显式恢复 */
#define CUT_CAUSE_SENSOR      1U     /* 传感器故障切断：采样恢复且安全后自动恢复 */

#endif /* __PROTECT_CFG_H */
