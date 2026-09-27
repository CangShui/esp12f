#!/usr/bin/env python3
"""Locate and disassemble the sketch functions that touch GPIO."""
import struct, sys, collections
from xdis import D, foff, vma, u32, decode, SEGS, R

DW_SLOT = 0x402039E8   # literal slot holding __digitalWrite (0x40100334)
DR_SLOT = 0x4020172C   # literal slot holding __digitalRead  (0x40100398)
PINMODE = 0x4020CDC0   # __pinMode
DELAY = 0x4020CD08     # delay(ms)

def find_l32r_to(slot):
    """scan every byte offset; return list of instruction addresses whose l32r targets slot"""
    out = []
    for f, va, sz in SEGS[:3]:
        p = f
        while p < f + sz - 2:
            if (D[p] & 0xF) == 0x1:
                V = D[p] | (D[p + 1] << 8) | (D[p + 2] << 16)
                pc = va + (p - f)
                tgt = ((pc + 3) & ~3) - ((0x10000 - ((V >> 8) & 0xFFFF)) << 2)
                if tgt == slot:
                    out.append(pc)
            p += 1
    return sorted(out)

def is_prologue(pc):
    fo = foff(pc)
    if fo is None:
        return False
    return D[fo] == 0x12 and D[fo + 1] == 0xC1

def find_func_start(pc, limit=0x400):
    p = pc & ~3
    while p > pc - limit:
        if is_prologue(p):
            # ensure it's a plausible start: previous 4 bytes are data/padding or a ret/jump
            return p
        p -= 4
    return None

def dis_func(start, maxlen=0x600):
    """sweep, stopping at ret.n/ret at depth 0 (approximate: first ret.n after the prologue)"""
    out = []
    pc = start
    end = start + maxlen
    while pc < end:
        ins = decode(pc)
        if ins is None:
            break
        out.append((pc, ins))
        pc += ins["n"]
        if ins.get("mnem") in ("ret.n",) or (ins.get("mnem") == "ret"):
            # keep going a little for trailing literals
            break
        if ins.get("mnem") == "call0" and ins.get("tgt") == 0:
            break
    return out

if __name__ == "__main__":
    dw = find_l32r_to(DW_SLOT)
    dr = find_l32r_to(DR_SLOT)
    print("digitalWrite call sites (%d): %s" % (len(dw), " ".join("0x%08X" % x for x in dw)))
    print("digitalRead  call sites (%d): %s" % (len(dr), " ".join("0x%08X" % x for x in dr)))
    starts = sorted(set(filter(None, [find_func_start(x) for x in dw + dr])))
    print("enclosing function starts: %s" % " ".join("0x%08X" % x for x in starts))
