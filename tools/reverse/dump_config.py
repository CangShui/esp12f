#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析原厂固件的配置扇区（flash 0xFB000）。

原厂在 0xFB000 用的是自定义结构（不是标准 SDK 格式）：

    偏移    长度   内容
    0x00     32    SSID
    0x20     64    WiFi 密码
    0x60     32    AccessKey
    0x75      1    CheckStateEnable
    0x76      1    LedEnable

同一个扇区在新固件里由 firmware/ES12F_Local/storage.h 读写，
所以原厂已配好的 WiFi 可以直接沿用。

用法:  python dump_config.py <1MB备份.bin>
"""
import os
import sys

OFF = 0xFB000
LAYOUT = [
    (0x00, 32, "SSID"),
    (0x20, 64, "WiFi 密码"),
    (0x60, 32, "AccessKey"),
    (0x75, 1,  "CheckStateEnable"),
    (0x76, 1,  "LedEnable"),
]


def cstr(b):
    """取 C 字符串（到 \\x00 或 \\xFF 为止）。"""
    out = bytearray()
    for c in b:
        if c in (0x00, 0xFF):
            break
        out.append(c)
    return out.decode("utf-8", "replace")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        path = os.path.join(root, "backup", "es12f_firmware_backup_1MB.bin")
        print("未指定文件，使用缺省: %s\n" % path)
    if not os.path.exists(path):
        sys.exit("找不到文件: %s\n用法: python dump_config.py <1MB备份.bin>" % path)

    d = open(path, "rb").read()
    if len(d) < OFF + 0x1000:
        sys.exit("文件太小，不是 1MB 整片 dump: %d 字节" % len(d))

    sec = d[OFF:OFF + 0x1000]
    blank = all(b == 0xFF for b in sec)
    print("文件     : %s (%d 字节)" % (os.path.basename(path), len(d)))
    print("配置扇区 : flash 0x%X" % OFF)
    print("状态     : %s" % ("空白（0xFF）→ 首次上电会进配网热点模式" if blank else "已有内容"))
    print()
    print("%-8s %-6s %-16s %s" % ("偏移", "长度", "字段", "值"))
    print("-" * 72)
    for off, ln, name in LAYOUT:
        raw = sec[off:off + ln]
        if name in ("CheckStateEnable", "LedEnable"):
            val = "0x%02X" % raw[0]
        else:
            val = cstr(raw)
            if val == "":
                val = "（空）" if raw[0] in (0x00, 0xFF) else repr(raw[:16])
        print("0x%04X   %-6d %-16s %s" % (off, ln, name, val))
    print()
    print("注：备份文件可能已脱敏（凭据被 0x00 覆写），此时看到空值是预期的。")


if __name__ == "__main__":
    main()
