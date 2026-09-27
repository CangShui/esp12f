#!/usr/bin/env python3
"""Linear sweep that reports GPIO / delay / pinMode call sites with argument values."""
import sys
from xdis import decode, foff, u32

DW_SLOT = 0x402039E8
DR_SLOT = 0x4020172C
PINMODE = 0x4020CDC0
DELAY = 0x4020CD08

def run(start, end):
    pc = start
    # track simple register constants
    known = {}
    last_slot = None
    while pc < end:
        ins = decode(pc)
        if ins is None:
            break
        m = ins["mnem"]
        txt = ins["text"]
        if m == "movi":
            known[ins["t"]] = ins["imm"]
        elif m == "movi.n":
            known[ins["t"]] = ins["imm"]
        elif m == "l32r":
            v = u32(ins["tgt"])
            known[ins["t"]] = ("lit", ins["tgt"], v)
            last_slot = ins["tgt"]
        elif m == "mov.n":
            known[ins["t"]] = known.get(ins["s"], "?")
        elif m == "addi":
            b = known.get(ins["s"], "?")
            known[ins["t"]] = (b + ins["imm"]) if isinstance(b, int) else "?"
        elif m == "callx0":
            if last_slot == DW_SLOT:
                print("%08X  digitalWrite(pin=%s, val=%s)" % (pc, known.get(2), known.get(3)))
            elif last_slot == DR_SLOT:
                print("%08X  digitalRead(pin=%s) -> %s" % (pc, known.get(2), ins["s"]))
            else:
                print("%08X  callx0 %s  (slot=%s)" % (pc, ins["s"], hex(last_slot) if last_slot else None))
            known = {}
        elif m == "call0":
            t = ins["tgt"]
            if t == DELAY:
                print("%08X  delay(%s)" % (pc, known.get(2)))
            elif t == PINMODE:
                print("%08X  pinMode(pin=%s, mode=%s)" % (pc, known.get(2), known.get(3)))
            elif t == 0x40208DFC:
                print("%08X  pub(obj=%s, cmd=%s, val=%s)" % (pc, known.get(2), known.get(3), known.get(4)))
            known = {}
        elif m in ("ret.n",):
            print("%08X  ret" % pc)
            break
        pc += ins["n"]

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("用法: python gpio.py <起始地址> <结束地址>\n"
                 "例:   python gpio.py 0x402039EC 0x40204080\n"
                 "作用: 解析该范围内的 digitalWrite/digitalRead，输出引脚号+电平+延时表")
    a = int(sys.argv[1], 0); b = int(sys.argv[2], 0)
    run(a, b)
