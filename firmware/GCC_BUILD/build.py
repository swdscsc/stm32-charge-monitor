# -*- coding: utf-8 -*-
"""ARM GCC 构建驱动：编译 STM32 固件并生成 .elf/.bin"""
import subprocess, sys, os, glob

ROOT   = r"E:\rj666\stm32-build"
GCC    = os.path.join(ROOT, "arm-gcc", "bin", "arm-none-eabi-gcc.exe")
OBJCOPY= os.path.join(ROOT, "arm-gcc", "bin", "arm-none-eabi-objcopy.exe")
SIZE   = os.path.join(ROOT, "arm-gcc", "bin", "arm-none-eabi-size.exe")
CUBE   = os.path.join(ROOT, "STM32F1xx_HAL_Driver")
CMSIS  = os.path.join(ROOT, "CMSIS")
BUILD  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
os.makedirs(BUILD, exist_ok=True)

CORE = r"E:\23计科1+202308324143+沈炜丹\毕业设计-STM32智能充电监控显示系统\firmware\Core"
CPU = ["-mcpu=cortex-m3", "-mthumb", "-DSTM32F103xB", "-DUSE_HAL_DRIVER"]
CFLAGS = CPU + ["-Os", "-Wall", "-ffreestanding", "-fdata-sections", "-ffunction-sections",
                "-I", os.path.join(CORE, "Inc"),
                "-I", os.path.join(CUBE, "Inc"),
                "-I", os.path.join(CMSIS, "Device", "ST", "STM32F1xx", "Include"),
                "-I", os.path.join(CMSIS, "Include"),
                "-I", os.path.dirname(os.path.abspath(__file__))]

HAL_SRC = ["stm32f1xx_hal.c", "stm32f1xx_hal_cortex.c", "stm32f1xx_hal_rcc.c",
           "stm32f1xx_hal_rcc_ex.c", "stm32f1xx_hal_gpio.c", "stm32f1xx_hal_flash.c",
           "stm32f1xx_hal_flash_ex.c", "stm32f1xx_hal_pwr.c", "stm32f1xx_hal_i2c.c",
           "stm32f1xx_hal_adc.c", "stm32f1xx_hal_adc_ex.c", "stm32f1xx_hal_uart.c",
           "stm32f1xx_hal_dma.c"]
APP_SRC = ["main.c", "ina219.c", "ntc.c", "ssd1306.c", "protect.c", "esp8266.c"]
SYS_SRC = [os.path.join(CMSIS, "Device", "ST", "STM32F1xx", "Source", "Templates", "system_stm32f1xx.c")]
STARTUP = os.path.join(CMSIS, "Device", "ST", "STM32F1xx", "Source", "Templates", "gcc", "startup_stm32f103xb.s")

objs = []
errors = 0

def run(cmd, tag):
    global errors
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0 or ("error" in out.lower() and out):
        print(f"[FAIL] {tag}\n{out}")
        errors += 1
    elif out:
        print(f"[warn] {tag}\n{out}")
    return r.returncode == 0

for src in HAL_SRC:
    path = os.path.join(CUBE, "Src", src)
    obj = os.path.join(BUILD, src + ".o")
    if run([GCC] + CFLAGS + ["-c", path, "-o", obj], src):
        objs.append(obj)

for src in APP_SRC:
    path = os.path.join(CORE, "Src", src)
    obj = os.path.join(BUILD, src + ".o")
    if run([GCC] + CFLAGS + ["-c", path, "-o", obj], src):
        objs.append(obj)

for path in SYS_SRC:
    obj = os.path.join(BUILD, os.path.basename(path) + ".o")
    if run([GCC] + CFLAGS + ["-c", path, "-o", obj], os.path.basename(path)):
        objs.append(obj)

obj_s = os.path.join(BUILD, "startup.o")
if run([GCC] + CPU + ["-c", STARTUP, "-o", obj_s], "startup_stm32f103xb.s"):
    objs.append(obj_s)

if errors:
    print(f"\n编译失败: {errors} 个文件出错")
    sys.exit(1)

elf = os.path.join(BUILD, "firmware.elf")
ld  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STM32F103C8TX_FLASH.ld")
r = subprocess.run([GCC] + CPU + ["-T", ld, "--specs=nano.specs", "--specs=nosys.specs",
                                  "-Wl,--gc-sections", "-Wl,--defsym=end=_ebss", f"-Wl,-Map={BUILD}/firmware.map",
                                  "-o", elf] + objs + ["-lm"], capture_output=True, text=True, errors="replace")
if r.returncode != 0:
    print("[FAIL] 链接\n" + (r.stdout + r.stderr))
    sys.exit(1)

print(subprocess.run([SIZE, elf], capture_output=True, text=True, errors="replace").stdout)
binf = os.path.join(BUILD, "firmware.bin")
subprocess.run([OBJCOPY, "-O", "binary", elf, binf], check=True)
print("BUILD OK ->", elf)
print("BIN ->", binf, os.path.getsize(binf), "bytes")
