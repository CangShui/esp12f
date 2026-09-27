#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ES12F 单会话刷写：一次连接内完成 备份 -> 刷写 -> 读回校验。

两个关键点（都踩过坑）：
 1) ESP8266 的 .ino.bin 是 [eboot@0x0]+[app@0x1000] 的合并镜像，
    必须整体写到 flash 0x0。写 0x1000 会让原厂 eboot 把新 eboot 当应用跳进去，
    入口 0x4010F480 非法指令异常死循环。
 2) esptool 命令行一个进程只做一件事，跨进程切换会丢下载模式。
    这里用 esptool 的 Python API 在同一个 ESPLoader 会话里做完所有事。

前提：GPIO0 接 GND 并保持，然后断电 -> 上电。
用法：python flash_now.py [COM3] [tries]
"""
import glob
import hashlib
import os
import sys
import time

import esptool.cmds as C

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
MAXTRIES = int(sys.argv[2]) if len(sys.argv) > 2 else 500
BAUD = 460800
FLASH_ADDR = 0x0

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
RELEASE = os.path.join(ROOT, "release")
LOGDIR = os.path.join(ROOT, "logs")
os.makedirs(LOGDIR, exist_ok=True)
LOG = os.path.join(LOGDIR, "flash_now.log")


def say(msg):
    line = time.strftime("[%H:%M:%S] ") + msg
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def main():
    cands = sorted(glob.glob(os.path.join(RELEASE, "ES12F_Local_firmware.bin")))
    if not cands:
        say("找不到 %s\n请先运行 tools/build.ps1 与 tools/make_images.py" % RELEASE)
        return 1
    img = cands[0]
    img_size = os.path.getsize(img)
    img_hash = sha256_file(img)
    data = open(img, "rb").read()
    say("刷写镜像 %s  %d 字节  SHA256 %s" % (os.path.basename(img), img_size, img_hash))
    if data[0] != 0xE9 or data[0x1000] != 0xE9:
        say("镜像结构异常：0x0 或 0x1000 处没有 E9 魔数")
        return 1
    say("结构检查 OK：0x0=eboot  0x1000=app")

    # ---------- 1. 轮询等待下载模式 ----------
    say("===== 等待模块进入下载模式（最多 %d 次）=====" % MAXTRIES)
    say("请确认 GPIO0 已接 GND，并刚做过一次 断电->上电")
    esp = None
    for i in range(1, MAXTRIES + 1):
        try:
            esp = C.connect_esp(port=PORT, chip="esp8266", initial_baud=115200,
                                before="no-reset", connect_attempts=1)
            say("第 %d 次探测：已连上 %s" % (i, esp.CHIP_NAME))
            break
        except Exception as e:
            esp = None
            if i == 1 or i % 10 == 0:
                say("第 %d 次探测：未连上" % i)
            time.sleep(2.0)
    if esp is None:
        say("超时：仍未连上")
        return 2

    # ---------- 2. stub + 提速 ----------
    try:
        esp = C.run_stub(esp)
        say("stub flasher 已运行")
    except Exception as e:
        say("stub 上传失败: %s" % e)
        return 3
    try:
        esp.change_baud(BAUD)
        say("波特率已切到 %d" % BAUD)
    except Exception as e:
        say("提速失败，继续 115200: %s" % e)

    # ---------- 3. 备份 ----------
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(LOGDIR, "current_flash_backup_%s.bin" % stamp)
    say("===== 备份整片 1MB -> %s =====" % os.path.basename(backup))
    try:
        C.read_flash(esp, 0x0, 0x100000, backup)
    except Exception as e:
        say("备份失败: %s" % e)
        return 4
    say("备份完成 %d 字节  SHA256 %s" % (os.path.getsize(backup), sha256_file(backup)))

    # ---------- 4. 写 0x0（eboot + app 一起）----------
    say("===== 写入 0x0（eboot+app 合并镜像，配置扇区不动）=====")
    try:
        C.write_flash(esp, [(FLASH_ADDR, img)])
    except Exception as e:
        say("刷写失败: %s" % e)
        return 5
    say("写入完成")

    # ---------- 5. 读回校验 ----------
    say("===== 读回 0x0 处 %d 字节比对 =====" % img_size)
    try:
        rb = C.read_flash(esp, FLASH_ADDR, img_size)
    except Exception as e:
        say("读回失败: %s" % e)
        return 6
    got = hashlib.sha256(rb).hexdigest().upper() if rb else "N/A"
    say("镜像 SHA256 : %s" % img_hash)
    say("芯片 SHA256 : %s" % got)
    if got == img_hash:
        say("校验通过 OK：芯片 0x0..0x%X 与镜像逐字节一致" % img_size)
        say("===== 全部完成 =====")
        say("下一步：断开 GPIO0 与 GND，再断电上电一次。")
        try:
            esp._port.close()
        except Exception:
            pass
        return 0
    say("校验失败：不一致")
    return 7


if __name__ == "__main__":
    sys.exit(main())
