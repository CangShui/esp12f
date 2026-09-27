#!/usr/bin/env python3
"""Xtensa (ESP8266 LX106) minimal disassembler for firmware analysis.
All field layouts fitted against xtensa-lx106-elf-objdump output (see fit16.py/fit24.py/fitbr.py).
"""
import struct, sys, collections
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_os.path.dirname(_HERE))
_DEFAULT_BIN = _os.path.join(_ROOT, "backup", "es12f_firmware_backup_1MB.bin")

def _resolve_bin(idx=1):
    """从命令行取 dump 路径；缺省用 backup/ 下的原厂备份。"""
    if len(_sys.argv) > idx and _os.path.exists(_sys.argv[idx]):
        return _sys.argv[idx]
    if not _os.path.exists(_DEFAULT_BIN):
        _sys.exit("找不到 dump 文件。\n用法: python %s <dump.bin>\n缺省路径 %s 也不存在。"
                  % (_os.path.basename(_sys.argv[0]), _DEFAULT_BIN))
    return _DEFAULT_BIN


BIN = _resolve_bin()
D = open(BIN, "rb").read()

SEGS = [
    (0x1010, 0x40201010, 0x47BD8),
    (0x48BF0, 0x40100000, 0x13C),
    (0x48D34, 0x4010013C, 0x6A28),
    (0x4F764, 0x3FFE8000, 0x508),
    (0x4FC74, 0x3FFE8510, 0x1700),
]

def foff(v):
    for f, va, s in SEGS:
        if va <= v < va + s:
            return f + v - va
    return None

def vma(fo):
    for f, va, s in SEGS:
        if f <= fo < f + s:
            return va + fo - f
    return None

def u32(v):
    fo = foff(v)
    return struct.unpack_from("<I", D, fo)[0] if fo is not None else None

def s8(x):  return x - 0x100 if x & 0x80 else x
def s12(x): return x - 0x1000 if x & 0x800 else x
def s18(x):
    x &= 0x3FFFF
    return x - 0x40000 if x & 0x20000 else x
def s7(x):  return x - 0x80 if x & 0x40 else x

R = ["a%d" % i for i in range(16)]

def decode(pc):
    fo = foff(pc)
    if fo is None:
        return None
    b0, b1, b2 = D[fo], D[fo + 1], D[fo + 2]
    V = b0 | (b1 << 8) | (b2 << 16)
    op0 = V & 0xF
    if op0 >= 8:
        # ---- 16-bit ----
        if V == 0xF00D: return dict(n=2, mnem="ret.n", text="ret.n")
        if V == 0xF03D: return dict(n=2, mnem="nop.n", text="nop.n")
        if V == 0xF06D: return dict(n=2, mnem="ill.n", text="ill.n")
        if V == 0xF0ED: return dict(n=2, mnem="retw.n", text="retw.n")
        if op0 == 0xC:
            t = (V >> 8) & 0xF
            if V & 0x80:  # branch RI6
                op1 = (V >> 6) & 1
                imm = ((V >> 12) & 0xF) | (((V >> 4) & 0x3) << 4)
                imm = imm - 0x40 if imm & 0x20 else imm
                tgt = pc + 4 + imm
                mn = "bnez.n" if op1 else "beqz.n"
                return dict(n=2, mnem=mn, tgt=tgt, text="%s %s, 0x%08X" % (mn, R[t], tgt))
            imm = ((V >> 12) & 0xF) | (((V >> 4) & 0x7) << 4)
            return dict(n=2, mnem="movi.n", t=t, imm=s7(imm), text="movi.n %s, %d" % (R[t], s7(imm)))
        if op0 == 0xD:
            return dict(n=2, mnem="mov.n", t=(V >> 4) & 0xF, s=(V >> 8) & 0xF,
                        text="mov.n %s, %s" % (R[(V >> 4) & 0xF], R[(V >> 8) & 0xF]))
        if op0 == 0x8:
            return dict(n=2, mnem="l32i.n", t=(V >> 4) & 0xF, s=(V >> 8) & 0xF, off=((V >> 12) & 0xF) * 4,
                        text="l32i.n %s, %s, %d" % (R[(V >> 4) & 0xF], R[(V >> 8) & 0xF], ((V >> 12) & 0xF) * 4))
        if op0 == 0x9:
            return dict(n=2, mnem="s32i.n", t=(V >> 4) & 0xF, s=(V >> 8) & 0xF, off=((V >> 12) & 0xF) * 4,
                        text="s32i.n %s, %s, %d" % (R[(V >> 4) & 0xF], R[(V >> 8) & 0xF], ((V >> 12) & 0xF) * 4))
        if op0 == 0xA:
            return dict(n=2, mnem="add.n", t=(V >> 12) & 0xF, s=(V >> 8) & 0xF, r=(V >> 4) & 0xF,
                        text="add.n %s, %s, %s" % (R[(V >> 12) & 0xF], R[(V >> 8) & 0xF], R[(V >> 4) & 0xF]))
        if op0 == 0xB:
            return dict(n=2, mnem="addi.n", t=(V >> 12) & 0xF, s=(V >> 8) & 0xF, imm=(V >> 4) & 0xF,
                        text="addi.n %s, %s, %d" % (R[(V >> 12) & 0xF], R[(V >> 8) & 0xF], (V >> 4) & 0xF))
        return dict(n=2, mnem="?", text=".byte16 0x%04X" % V)
    # ---- 24-bit ----
    if op0 == 0x1:
        t = (V >> 4) & 0xF
        tgt = ((pc + 3) & ~3) - ((0x10000 - ((V >> 8) & 0xFFFF)) << 2)
        return dict(n=3, mnem="l32r", t=t, tgt=tgt, text="l32r %s, 0x%08X" % (R[t], tgt))
    if op0 == 0x5:
        tgt = ((pc & ~3) + 4 + s18(V >> 6) * 4) & 0xFFFFFFFF
        return dict(n=3, mnem="call0", tgt=tgt, text="call0 0x%08X" % tgt)
    if op0 == 0x6:
        a = ((pc & ~3) + 4 + s12(V >> 12)) & 0xFFFFFFFF
        b = (pc + 4 + s8(V >> 16)) & 0xFFFFFFFF
        ok_a = foff(a) is not None
        ok_b = foff(b) is not None
        tgt = a if (ok_a and not ok_b) else (b if ok_b else a)
        return dict(n=3, mnem="br6", tgt=tgt, text="br6 0x%08X (alt 0x%08X)  V=%06X" % (tgt, b if tgt == a else a, V))
    if op0 == 0x7:
        tgt = (pc + 4 + s8(V >> 16)) & 0xFFFFFFFF
        return dict(n=3, mnem="br7", tgt=tgt, text="br7 0x%08X  V=%06X" % (tgt, V))
    if op0 == 0x0:
        s = (V >> 8) & 0xF
        if ((V >> 4) & 0xF) == 0xC and ((V >> 16) & 0xF) == 0:
            return dict(n=3, mnem="callx0", s=s, text="callx0 %s" % R[s])
        return dict(n=3, mnem="rrr", text="rrr V=%06X (s=%s)" % (V, R[s]))
    if op0 == 0x2:
        t = (V >> 4) & 0xF; s = (V >> 8) & 0xF; r = (V >> 12) & 0xF; imm8 = (V >> 16) & 0xFF
        if r == 0xA:
            imm = (((V >> 8) & 0xF) << 8) | imm8
            return dict(n=3, mnem="movi", t=t, imm=s12(imm), text="movi %s, %d" % (R[t], s12(imm)))
        if r == 0xC:
            return dict(n=3, mnem="addi", t=t, s=s, imm=s8(imm8), text="addi %s, %s, %d" % (R[t], R[s], s8(imm8)))
        return dict(n=3, mnem="rri8", text="rri8 r=%X t=%s s=%s imm=%d" % (r, R[t], R[s], s8(imm8)))
    if op0 == 0x3:
        return dict(n=3, mnem="op3", text="op3 V=%06X" % V)
    if op0 == 0x4:
        return dict(n=3, mnem="op4", text="op4 V=%06X" % V)
    return dict(n=3, mnem="?", text=".byte24 0x%06X" % V)

def literal_slots():
    slots = set()
    for f, va, sz in SEGS[:3]:
        p = f
        while p < f + sz - 2:
            if (D[p] & 0xF) == 0x1:
                V = D[p] | (D[p + 1] << 8) | (D[p + 2] << 16)
                pc = va + (p - f)
                tgt = ((pc + 3) & ~3) - ((0x10000 - ((V >> 8) & 0xFFFF)) << 2)
                if foff(tgt) is not None:
                    slots.add(tgt & ~3)
            p += 1
    return slots

SLOTS = literal_slots()

def sweep(start, end, skip_pools=True):
    pc = start
    while pc < end:
        if skip_pools and pc in SLOTS:
            n = 1
            while (pc + n * 4) in SLOTS:
                n += 1
            yield ("POOL", pc, n * 4, " ".join("0x%08X" % u32(pc + i * 4) for i in range(n)))
            pc += n * 4
            continue
        ins = decode(pc)
        if ins is None:
            return
        yield (ins.get("mnem"), pc, ins["n"], ins["text"])
        pc += ins["n"]

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("用法: python xdis.py <起始地址> <结束地址>\n"
                 "例:   python xdis.py 0x402039EC 0x40203A90\n"
                 "dump 缺省用 backup/es12f_firmware_backup_1MB.bin")
    start = int(sys.argv[1], 0); end = int(sys.argv[2], 0)
    for mnem, pc, n, text in sweep(start, end):
        print("%08X:\t%s" % (pc, text))
