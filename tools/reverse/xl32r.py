#!/usr/bin/env python3
"""Xtensa/ESP8266 firmware static helper.
Decodes l32r (validated against objdump) so we can find xrefs to any address."""
import re, struct, collections, sys
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
DIS = _os.path.join(_ROOT, "build", "app.dis")
d = open(BIN, "rb").read()

SEGS = [
    (0x1010, 0x40201010, 0x47BD8),
    (0x48BF0, 0x40100000, 0x13C),
    (0x48D34, 0x4010013C, 0x6A28),
    (0x4F764, 0x3FFE8000, 0x508),
    (0x4FC74, 0x3FFE8510, 0x1700),
]

def vma_of(fo):
    for f, v, s in SEGS:
        if f <= fo < f + s:
            return v + fo - f
    return None

def foff_of(v):
    for f, va, s in SEGS:
        if va <= v < va + s:
            return f + v - va
    return None

def decode_l32r(pc, b0, b1, b2):
    """returns (reg, target_vma)"""
    t = b0 >> 4
    imm16 = b1 | (b2 << 8)
    off_words = 0x10000 - imm16
    return t, (((pc + 3) & ~3) - (off_words << 2))

def validate():
    n = bad = 0
    if not _os.path.exists(DIS):
        print("跳过自校验：找不到 %s" % DIS)
        print("（该文件是 objdump 的反汇编输出，仓库内未保留；")
        print("  需要时用 mkelf.py 重建 ELF 后自行 objdump -d > build/app.dis）")
        return
    for line in open(DIS, encoding="utf-8", errors="replace"):
        m = re.match(r"^\s*([0-9a-f]{8}):\t([0-9a-f]{6})\s+l32r\s+a(\d+), 0x([0-9a-f]{8})", line)
        if not m:
            continue
        pc = int(m.group(1), 16); raw = m.group(2); t = int(m.group(3)); tgt = int(m.group(4), 16)
        b = [int(raw[4:6], 16), int(raw[2:4], 16), int(raw[0:2], 16)]  # memory order
        rt, tt = decode_l32r(pc, b[0], b[1], b[2])
        n += 1
        if rt != t or tt != tgt:
            bad += 1
            if bad < 6:
                print("MISMATCH pc=%08X raw=%s got a%d/0x%08X want a%d/0x%08X" % (pc, raw, rt, tt, t, tgt))
    print("validated %d l32r, %d mismatches" % (n, bad))

def all_l32r():
    out = []
    for f, v, s in SEGS[:3]:
        p = f
        while p < f + s - 2:
            if (d[p] & 0x0F) == 0x01:
                pc = v + (p - f)
                t, tgt = decode_l32r(pc, d[p], d[p+1], d[p+2])
                out.append((pc, t, tgt))
            p += 1
    return out

if __name__ == "__main__":
    validate()
