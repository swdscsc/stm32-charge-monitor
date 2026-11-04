# -*- coding: utf-8 -*-
"""可移植 ARM GCC 构建脚本。

环境变量：
  ARM_GCC_BIN   arm-none-eabi 工具链 bin 目录（也可将工具加入 PATH）
  STM32_HAL_ROOT  STM32F1xx_HAL_Driver 根目录，含 Inc/ 与 Src/
  CMSIS_ROOT      CMSIS 根目录，含 Device/ 与 Include/
"""
import os
import sys
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CORE = os.path.join(ROOT, "firmware", "Core")
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)

TOOL_BIN = os.environ.get("ARM_GCC_BIN", "")

def tool(name):
    candidate = os.path.join(TOOL_BIN, name + (".exe" if os.name == "nt" else "")) if TOOL_BIN else None
    if candidate and os.path.isfile(candidate):
        return candidate
    found = shutil.which(name)
    if found:
        return found
    print(f"[ERROR] 找不到 {name}。请安装 Arm GNU Toolchain，并将其 bin 加入 PATH 或设置 ARM_GCC_BIN。")
    sys.exit(2)

GCC = tool("arm-none-eabi-gcc")
OBJCOPY = tool("arm-none-eabi-objcopy")
SIZE = tool("arm-none-eabi-size")
HAL = os.environ.get("STM32_HAL_ROOT", os.path.join(ROOT, "Drivers", "STM32F1xx_HAL_Driver"))
CMSIS = os.environ.get("CMSIS_ROOT", os.path.join(ROOT, "Drivers", "CMSIS"))
DEVICE = os.path.join(CMSIS, "Device", "ST", "STM32F1xx")

required = [os.path.join(HAL, "Inc"), os.path.join(HAL, "Src"),
            os.path.join(DEVICE, "Include"), os.path.join(CMSIS, "Include")]
missing = [p for p in required if not os.path.isdir(p)]
if missing:
    print("[ERROR] 缺少 STM32 HAL/CMSIS 依赖目录：")
    for path in missing:
        print("  -", path)
    print("请设置 STM32_HAL_ROOT 与 CMSIS_ROOT，或按 README 放入 Drivers/ 目录。")
    sys.exit(2)

CPU = ["-mcpu=cortex-m3", "-mthumb", "-DSTM32F103xB", "-DUSE_HAL_DRIVER"]
CFLAGS = CPU + ["-std=c99", "-Os", "-Wall", "-Wextra", "-ffreestanding",
    "-fdata-sections", "-ffunction-sections",
    "-I", os.path.join(CORE, "Inc"), "-I", os.path.join(HAL, "Inc"),
    "-I", os.path.join(DEVICE, "Include"), "-I", os.path.join(CMSIS, "Include"),
    "-I", HERE]
HAL_SRC = ["stm32f1xx_hal.c", "stm32f1xx_hal_cortex.c", "stm32f1xx_hal_rcc.c",
    "stm32f1xx_hal_rcc_ex.c", "stm32f1xx_hal_gpio.c", "stm32f1xx_hal_flash.c",
    "stm32f1xx_hal_flash_ex.c", "stm32f1xx_hal_pwr.c", "stm32f1xx_hal_i2c.c",
    "stm32f1xx_hal_adc.c", "stm32f1xx_hal_adc_ex.c", "stm32f1xx_hal_uart.c",
    "stm32f1xx_hal_dma.c"]
APP_SRC = ["main.c", "ina219.c", "ntc.c", "ssd1306.c", "protect.c", "esp8266.c"]
SYS_SRC = [os.path.join(DEVICE, "Source", "Templates", "system_stm32f1xx.c")]
STARTUP = os.path.join(DEVICE, "Source", "Templates", "gcc", "startup_stm32f103xb.s")

objects = []
errors = 0

def run(cmd, tag):
    global errors
    result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        print(f"[FAIL] {tag}\n{output}")
        errors += 1
    elif output:
        print(output)
    return result.returncode == 0

for source in HAL_SRC:
    src = os.path.join(HAL, "Src", source)
    obj = os.path.join(BUILD, source + ".o")
    if run([GCC] + CFLAGS + ["-c", src, "-o", obj], source):
        objects.append(obj)
for source in APP_SRC:
    src = os.path.join(CORE, "Src", source)
    obj = os.path.join(BUILD, source + ".o")
    if run([GCC] + CFLAGS + ["-c", src, "-o", obj], source):
        objects.append(obj)
for src in SYS_SRC:
    obj = os.path.join(BUILD, os.path.basename(src) + ".o")
    if run([GCC] + CFLAGS + ["-c", src, "-o", obj], os.path.basename(src)):
        objects.append(obj)
startup_obj = os.path.join(BUILD, "startup.o")
if run([GCC] + CPU + ["-c", STARTUP, "-o", startup_obj], "startup_stm32f103xb.s"):
    objects.append(startup_obj)
if errors:
    print(f"\n编译失败：{errors} 个文件出错")
    sys.exit(1)

elf = os.path.join(BUILD, "firmware.elf")
linker = os.path.join(HERE, "STM32F103C8TX_FLASH.ld")
map_file = os.path.join(BUILD, "firmware.map")
link = subprocess.run([GCC] + CPU + ["-T", linker, "--specs=nano.specs", "--specs=nosys.specs",
    "-Wl,--gc-sections", f"-Wl,-Map={map_file}", "-o", elf] + objects + ["-lm"],
    capture_output=True, text=True, errors="replace")
if link.returncode != 0:
    print("[FAIL] 链接\n" + link.stdout + link.stderr)
    sys.exit(1)
print(subprocess.run([SIZE, elf], capture_output=True, text=True, errors="replace").stdout)
binary = os.path.join(BUILD, "firmware.bin")
subprocess.run([OBJCOPY, "-O", "binary", elf, binary], check=True)
print("BUILD OK ->", elf)
print("BIN ->", binary, os.path.getsize(binary), "bytes")
