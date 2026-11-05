# ARM GCC 备用构建脚本（推荐优先使用 build.py，它是已验证路径）
# 依赖路径可用环境变量覆盖，默认值与 build.py 一致：
#   ARM_GCC_BIN / STM32_HAL_ROOT / CMSIS_ROOT
ARM_GCC_BIN ?= E:/rj666/stm32-build/arm-gcc/bin
HAL_ROOT    ?= $(STM32_HAL_ROOT)
ifeq ($(HAL_ROOT),)
HAL_ROOT    := E:/rj666/stm32-build/STM32F1xx_HAL_Driver
endif
CMSIS_ROOT  ?= E:/rj666/stm32-build/CMSIS
CROSS   = $(ARM_GCC_BIN)/arm-none-eabi-
CORE    = ../Core

CC      = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
SIZE    = $(CROSS)size

CPU     = -mcpu=cortex-m3 -mthumb -DSTM32F103xB -DUSE_HAL_DRIVER
CFLAGS  = $(CPU) -std=c99 -Os -Wall -Wextra -ffreestanding \
          -fdata-sections -ffunction-sections \
          -I$(CORE)/Inc -I$(HAL_ROOT)/Inc \
          -I$(CMSIS_ROOT)/Device/ST/STM32F1xx/Include \
          -I$(CMSIS_ROOT)/Include -I.
LDFLAGS = $(CPU) -T STM32F103C8TX_FLASH.ld --specs=nano.specs --specs=nosys.specs \
          -Wl,--gc-sections -Wl,-Map=firmware.map
# 调试/单步时可加 -DDISABLE_IWDG 关闭独立看门狗

HAL_SRC = stm32f1xx_hal.c stm32f1xx_hal_cortex.c stm32f1xx_hal_rcc.c \
          stm32f1xx_hal_rcc_ex.c stm32f1xx_hal_gpio.c stm32f1xx_hal_flash.c \
          stm32f1xx_hal_flash_ex.c stm32f1xx_hal_pwr.c stm32f1xx_hal_i2c.c \
          stm32f1xx_hal_adc.c stm32f1xx_hal_adc_ex.c stm32f1xx_hal_uart.c \
          stm32f1xx_hal_dma.c stm32f1xx_hal_iwdg.c
APP_SRC = main.c ina219.c ntc.c ssd1306.c protect.c protect_hal.c esp8266.c

SRCS  = $(addprefix $(HAL_ROOT)/Src/,$(HAL_SRC)) \
        $(CMSIS_ROOT)/Device/ST/STM32F1xx/Source/Templates/system_stm32f1xx.c \
        $(CMSIS_ROOT)/Device/ST/STM32F1xx/Source/Templates/gcc/startup_stm32f103xb.s \
        $(addprefix $(CORE)/Src/,$(APP_SRC))
OBJS  = $(SRCS:.c=.o) $(SRCS:.s=.o)

firmware.elf: $(OBJS) STM32F103C8TX_FLASH.ld
	$(CC) $(LDFLAGS) $(OBJS) -o $@
	$(SIZE) $@
	$(OBJCOPY) -O binary $@ firmware.bin

clean:
	rm -f $(OBJS) firmware.elf firmware.bin firmware.map
