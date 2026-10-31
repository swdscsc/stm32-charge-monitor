# ARM GCC 编译脚本（在无 Keil/STM32CubeIDE 的机器上验证固件可编译）
# 用法: 将本文件放到 firmware/GCC_BUILD 下，arm-gcc 解压到 E:/rj666/stm32-build/arm-gcc，
#       CubeF1 解压到 E:/rj666/stm32-build/STM32CubeF1-master
CROSS   = E:/rj666/stm32-build/arm-gcc/bin/arm-none-eabi-
CUBE    = E:/rj666/stm32-build/STM32CubeF1-master/Drivers
CORE    = ../Core

CC      = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
SIZE    = $(CROSS)size

CPU     = -mcpu=cortex-m3 -mthumb -DSTM32F103xB -DUSE_HAL_DRIVER
CFLAGS  = $(CPU) -Os -Wall -ffreestanding -fdata-sections -ffunction-sections \
          -I$(CORE)/Inc -I$(CUBE)/STM32F1xx_HAL_Driver/Inc \
          -I$(CUBE)/CMSIS/Device/ST/STM32F1xx/Include \
          -I$(CUBE)/CMSIS/Include -I.
LDFLAGS = $(CPU) -T STM32F103C8TX_FLASH.ld --specs=nano.specs \
          -Wl,--gc-sections -Wl,-Map=firmware.map

HAL_SRC = stm32f1xx_hal.c stm32f1xx_hal_cortex.c stm32f1xx_hal_rcc.c \
          stm32f1xx_hal_rcc_ex.c stm32f1xx_hal_gpio.c stm32f1xx_hal_flash.c \
          stm32f1xx_hal_flash_ex.c stm32f1xx_hal_pwr.c stm32f1xx_hal_i2c.c \
          stm32f1xx_hal_adc.c stm32f1xx_hal_adc_ex.c stm32f1xx_hal_uart.c \
          stm32f1xx_hal_uart_ex.c
APP_SRC = main.c ina219.c ntc.c ssd1306.c protect.c esp8266.c

SRCS  = $(addprefix $(CUBE)/STM32F1xx_HAL_Driver/Src/,$(HAL_SRC)) \
        $(addprefix $(CUBE)/CMSIS/Device/ST/STM32F1xx/Source/Templates/gcc/,system_stm32f1xx.c startup_stm32f103xb.s) \
        $(addprefix $(CORE)/Src/,$(APP_SRC))
OBJS  = $(SRCS:.c=.o) $(SRCS:.s=.o)

firmware.elf: $(OBJS) STM32F103C8TX_FLASH.ld
	$(CC) $(LDFLAGS) $(OBJS) -o $@
	$(SIZE) $@
	$(OBJCOPY) -O binary $@ firmware.bin

clean:
	rm -f $(OBJS) firmware.elf firmware.bin firmware.map
