#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ES12F 只读监控：轮询 /api/status，记录 GPIO14(state) / GPIO4(sense) 电平变化。
只发 GET /api/status，绝不发送 on/off/restart 任何动作命令。

用法: python monitor.py [IP] [分钟数]
"""
import json
import os
import sys
import time
import urllib.request

IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.4.221"
MINUTES = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
LOGDIR = os.path.join(ROOT, "logs")
os.makedirs(LOGDIR, exist_ok=True)
LOG = os.path.join(LOGDIR, "monitor.log")
URL = "http://%s/api/status" % IP


def say(msg):
    line = time.strftime("[%H:%M:%S] ") + msg
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def main():
    say("===== 只读监控开始 %s  持续 %.0f 分钟 =====" % (URL, MINUTES))
    say("（只发 GET /api/status，不会发送任何开关机命令）")
    prev = None
    t0 = time.time()
    fail = 0
    while time.time() - t0 < MINUTES * 60:
        try:
            with urllib.request.urlopen(URL, timeout=5) as r:
                d = json.loads(r.read().decode("utf-8"))
            fail = 0
            key = (d.get("state"), d.get("sense"), d.get("power"))
            if key != prev:
                if prev is None:
                    say("初始  state(GPIO14)=%s  sense(GPIO4)=%s  power=%s  rssi=%s"
                        % (d["state"], d["sense"], d["power"], d["rssi"]))
                else:
                    say("*** 变化 ***  state(GPIO14): %s -> %s   sense(GPIO4): %s -> %s"
                        "   power: %s -> %s   rssi=%s"
                        % (prev[0], d["state"], prev[1], d["sense"], prev[2], d["power"], d["rssi"]))
                prev = key
            else:
                say("稳定  state=%s  sense=%s  power=%s  rssi=%s  uptime=%s"
                    % (d["state"], d["sense"], d["power"], d["rssi"], d["uptime"]))
        except Exception as e:
            fail += 1
            if fail in (1, 5, 20):
                say("请求失败(%d): %s" % (fail, str(e)[:80]))
        time.sleep(2.0)
    say("===== 监控结束 =====")


if __name__ == "__main__":
    main()
