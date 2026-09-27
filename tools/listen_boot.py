#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ES12F 启动监听（双波特率）：
  阶段A 115200 —— 应用 Serial.begin(115200) 之后的日志
  阶段B  74880 —— ROM 启动横幅 / eboot 加载信息 / 崩溃异常（26MHz 晶振默认波特率）
阶段A 收到数据就跳过阶段B。
"""
import os
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
SEC_A = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SEC_B = int(sys.argv[3]) if len(sys.argv) > 3 else 20
TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
LOGDIR = os.path.join(ROOT, "logs")
os.makedirs(LOGDIR, exist_ok=True)
LOG = os.path.join(LOGDIR, "serial_boot.log")
RAW = os.path.join(LOGDIR, "serial_boot_raw.bin")


def capture(baud, seconds, tag):
    s = serial.Serial(PORT, baud, timeout=0.2)
    s.reset_input_buffer()
    print("[%s] listening @%d for %ds ..." % (tag, baud, seconds), flush=True)
    t0 = time.time()
    buf = b""
    while time.time() - t0 < seconds:
        c = s.read(2048)
        if c:
            buf += c
            if len(buf) == len(c):
                print("[%s] first bytes: %r" % (tag, c[:120]), flush=True)
    s.close()
    return buf


def main():
    a = capture(115200, SEC_A, "A")
    b = b""
    if len(a) < 20:
        b = capture(74880, SEC_B, "B")
    else:
        print("[A] got %d bytes, skip 74880 phase" % len(a), flush=True)

    with open(RAW, "ab") as rf:
        rf.write(b"\n---115200---\n" + a + b"\n---74880---\n" + b)
    with open(LOG, "a", encoding="utf-8") as lf:
        lf.write("\n===== listen %s =====\n" % time.strftime("%H:%M:%S"))
        lf.write("--- @115200 (%d bytes) ---\n" % len(a))
        lf.write(a.decode("utf-8", "replace"))
        lf.write("\n--- @74880 (%d bytes) ---\n" % len(b))
        lf.write(b.decode("utf-8", "replace"))
    print("115200: %d bytes ; 74880: %d bytes" % (len(a), len(b)), flush=True)


if __name__ == "__main__":
    main()
