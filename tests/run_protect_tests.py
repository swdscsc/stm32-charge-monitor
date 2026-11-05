# -*- coding: utf-8 -*-
"""编译并运行 protect.c 的 C 单元测试（主机侧，无需 ARM 工具链）。

用法:  python tests/run_protect_tests.py
依赖:  系统装有 gcc/clang（Windows 下可为 MinGW/MSYS2 的 gcc）。
"""
import os
import sys
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_C = os.path.join(ROOT, "tests", "protect_tests.c")
PROTECT_C = os.path.join(ROOT, "firmware", "Core", "Src", "protect.c")
INC = os.path.join(ROOT, "firmware", "Core", "Inc")
BUILD = os.path.join(ROOT, "tests", "build")
os.makedirs(BUILD, exist_ok=True)
OUT = os.path.join(BUILD, "protect_tests")


def find_cc():
    for name in ("gcc", "clang", "cc"):
        p = shutil.which(name)
        if p:
            return p
    return None


def main():
    cc = find_cc()
    if cc is None:
        print("[SKIP] 未找到 C 编译器(gcc/clang)，跳过 C 单元测试（请安装后重试）")
        return 2
    cmd = [cc, TEST_C, PROTECT_C, "-I", INC, "-lm", "-O2", "-o", OUT]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("[FAIL] 编译 C 单元测试失败:\n" + r.stdout + r.stderr)
        return 1
    exe = OUT + ".exe" if os.name == "nt" and not os.path.exists(OUT) else OUT
    run = subprocess.run([exe], capture_output=True, text=True, errors="replace")
    print(run.stdout, end="")
    if run.returncode != 0:
        print("[FAIL] C 单元测试未全部通过（返回码 %d）" % run.returncode)
        return 1
    if "ALL PASS" not in run.stdout:
        print("[FAIL] C 单元测试输出缺少 ALL PASS")
        return 1
    print("[PASS] 保护状态机 C 单元测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
