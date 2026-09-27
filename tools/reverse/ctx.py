#!/usr/bin/env python3
"""Print annotated context around every GPIO/delay/pinMode call in a function."""
import sys
from xdis import decode, u32

DW_SLOT = 0x402039E8
DR_SLOT = 0x4020172C
PINMODE = 0x4020CDC0
DELAY = 0x4020CD08

def sweep(start, end):
    pc = start
    ins_list = []
    while pc < end:
        ins = decode(pc)
        if ins is None:
            break
        ins_list.append((pc, ins))
        pc += ins["n"]
    return ins_list

def annotate(start, end):
    ins_list = sweep(start, end)
    known = {}
    last_slot = None
    for i, (pc, ins) in enumerate(ins_list):
        m = ins["mnem"]
        if m in ("movi", "movi.n"):
            known[ins["t"]] = ins["imm"]
        elif m == "l32r":
            known[ins["t"]] = ("lit", ins["tgt"], u32(ins["tgt"]))
            last_slot = ins["tgt"]
        elif m == "mov.n":
            known[ins["t"]] = known.get(ins["s"], "?")
        elif m == "addi":
            b = known.get(ins["s"], "?")
            known[ins["t"]] = (b + ins["imm"]) if isinstance(b, int) else "?"
        elif m == "callx0":
            tag = None
            if last_slot == DW_SLOT:
                tag = ">> digitalWrite(pin=%s, val=%s)" % (known.get(2), known.get(3))
            elif last_slot == DR_SLOT:
                tag = ">> digitalRead(pin=%s)" % (known.get(2),)
            if tag:
                for j in range(max(0, i - 10), i + 1):
                    p2, i2 = ins_list[j]
                    print("  %08X: %-34s %s" % (p2, i2["text"], tag if j == i else ""))
                print()
            known = {}
        elif m == "call0":
            t = ins["tgt"]
            tag = None
            if t == DELAY:
                tag = ">> delay(%s)" % (known.get(2),)
            elif t == PINMODE:
                tag = ">> pinMode(pin=%s, mode=%s)" % (known.get(2), known.get(3))
            if tag:
                for j in range(max(0, i - 10), i + 1):
                    p2, i2 = ins_list[j]
                    print("  %08X: %-34s %s" % (p2, i2["text"], tag if j == i else ""))
                print()
            known = {}
        elif m == "ret.n":
            print("  %08X: ret" % pc)
            break

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("用法: python ctx.py <起始地址> <结束地址>\n"
                 "例:   python ctx.py 0x402039EC 0x40203A90\n"
                 "作用: 打印该地址范围内每条 GPIO/delay/pinMode 调用及其上下文")
    annotate(int(sys.argv[1], 0), int(sys.argv[2], 0))
