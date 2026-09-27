#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从编译产物生成可刷写镜像。

输入 : <repo>/build/ES12F_Local.ino.bin   （由 tools/build.ps1 生成）
输出 : <repo>/release/ES12F_Local_firmware.bin   合并镜像，写 flash 0x0
       <repo>/release/ES12F_Local_full_1MB.bin   完整 1MB 出厂镜像，写 0x0
       <repo>/release/SHA256SUMS.txt

!! 关键 !!
ESP8266 Arduino 的 `xxx.ino.bin` **不是纯应用镜像**，而是
    [eboot 引导程序 @flash 0x0] + [应用 @flash 0x1000]
的合并镜像（见 platform.txt: `write_flash 0x0 {build.project_name}.bin`）。
必须整体写到 flash 的 0x0，绝不能只写 0x1000 —— 否则原厂 eboot 会把
"新 eboot" 当成应用跳进去，入口 0x4010F480 直接非法指令异常死循环。
"""
import hashlib
import os
import shutil
import struct
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
COMBINED = os.path.join(ROOT, "build", "ES12F_Local.ino.bin")
OUTDIR = os.path.join(ROOT, "release")

FLASH_SIZE = 0x100000
CONFIG_SECTOR = 0xFB000      # eeprom/rfcal/wifi 区起点，配置就存在这里


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def describe(buf, base, label):
    magic, nseg, mode, sf = struct.unpack_from("<BBBB", buf, base)
    entry = struct.unpack_from("<I", buf, base + 4)[0]
    print("  %-6s @0x%04X magic=0x%02X nseg=%d mode=%d freq=0x%02X entry=0x%08X"
          % (label, base, magic, nseg, mode, sf, entry))
    p = base + 8
    for i in range(nseg):
        a, s = struct.unpack_from("<II", buf, p)
        print("           seg%d addr=0x%08X size=%d" % (i, a, s))
        p += 8 + s
    return p


def main():
    if not os.path.exists(COMBINED):
        sys.exit("缺少 %s\n请先运行 tools/build.ps1 编译。" % COMBINED)

    os.makedirs(OUTDIR, exist_ok=True)
    combined = open(COMBINED, "rb").read()

    if combined[0] != 0xE9:
        sys.exit("合并镜像 0x0 处没有 E9 魔数")
    if combined[0x1000] != 0xE9:
        sys.exit("合并镜像 0x1000 处没有 E9 魔数（app 镜像头）")
    if len(combined) > CONFIG_SECTOR:
        sys.exit("镜像过大: %d 字节" % len(combined))

    print("合并镜像结构：")
    describe(combined, 0x0, "eboot")
    describe(combined, 0x1000, "app")
    print("  文件长度 %d，写到 0x0 后占用 0x0..0x%X" % (len(combined), len(combined)))
    print()

    # ---- 1) 主刷写文件（写 0x0，保留芯片上的 WiFi 配置）----
    out1 = os.path.join(OUTDIR, "ES12F_Local_firmware.bin")
    shutil.copyfile(COMBINED, out1)

    # ---- 2) 完整 1MB 出厂镜像（配置清空，首次上电进配网模式）----
    img = bytearray(b"\xFF" * FLASH_SIZE)
    img[0:len(combined)] = combined
    out2 = os.path.join(OUTDIR, "ES12F_Local_full_1MB.bin")
    open(out2, "wb").write(bytes(img))

    h1, h2 = sha256(out1), sha256(out2)
    print("产出：")
    print("  %-40s %8d B  SHA256 %s" % (os.path.basename(out1), os.path.getsize(out1), h1))
    print("  %-40s %8d B  SHA256 %s" % (os.path.basename(out2), os.path.getsize(out2), h2))
    print()
    print("  · 写 0x0 时配置扇区 0x%X 不受影响（%d < 0x%X）→ 原有 WiFi 保留"
          % (CONFIG_SECTOR, len(combined), CONFIG_SECTOR))
    print("  · 完整镜像 0x%X 起全部为 0xFF → 首次上电进配网热点模式" % CONFIG_SECTOR)

    with open(os.path.join(OUTDIR, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.write("# ES12F 本地化固件 —— 镜像指纹\n")
        f.write("# 生成方式: tools/build.ps1 -> tools/make_images.py\n")
        f.write("# 刷写地址: 两个文件都写 flash 0x0\n\n")
        f.write("%s  %s\n" % (h1, os.path.basename(out1)))
        f.write("%s  %s\n" % (h2, os.path.basename(out2)))

    # 自检
    assert open(out1, "rb").read() == combined
    full = open(out2, "rb").read()
    assert full[0:len(combined)] == combined
    assert all(b == 0xFF for b in full[CONFIG_SECTOR:])
    print()
    print("自检通过 OK，指纹已写入 release/SHA256SUMS.txt")


if __name__ == "__main__":
    main()
