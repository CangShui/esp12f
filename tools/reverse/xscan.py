#!/usr/bin/env python3
"""Minimal Xtensa scanner: find l32r instructions and their targets, plus
32-bit literal-pool values that point into DRAM/IRAM/rodata."""
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


SRC = _resolve_bin()
d = open(SRC, "rb").read()

# image segments (file_off, vma, size)
SEGS = [
    (0x1010, 0x40201010, 0x47BD8),
    (0x48BF0, 0x40100000, 0x13C),
    (0x48D34, 0x4010013C, 0x6A28),
    (0x4F764, 0x3FFE8000, 0x508),
    (0x4FC74, 0x3FFE8510, 0x1700),
]

def vma_of(foff):
    for fo, va, sz in SEGS:
        if fo <= foff < fo + sz:
            return va + (foff - fo)
    return None

def foff_of(vma):
    for fo, va, sz in SEGS:
        if va <= vma < va + sz:
            return fo + (vma - va)
    return None

def l32r_refs(foff_start, foff_end):
    """yield (insn_foff, insn_vma, literal_foff, literal_vma)"""
    out = []
    for p in range(foff_start, foff_end - 2):
        b0 = d[p]
        if (b0 & 0x0F) != 0x01:
            continue
        t = b0 >> 4
        imm16 = d[p + 1] | (d[p + 2] << 8)
        va = vma_of(p)
        if va is None:
            continue
        target = ((va + 3) & ~3) - (imm16 << 2)
        lf = foff_of(target)
        if lf is None:
            continue
        out.append((p, va, lf, target))
    return out

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "strings"
    if mode == "strings":
        # find 32-bit literals in irom0 pointing into DRAM rodata (0x3FFE8510..)
        lo, hi = 0x3FFE8510, 0x3FFE9C10
        refs = l32r_refs(0x1010, 0x48BE8)
        by_lit = collections.defaultdict(list)
        for p, va, lf, tgt in refs:
            by_lit[tgt].append(va)
        # which literals are in the string range?
        print("== l32r references into DRAM rodata (string pool) ==")
        rows = []
        for tgt, srcs in sorted(by_lit.items()):
            if lo <= tgt < hi:
                s = d[foff_of(tgt):foff_of(tgt) + 48]
                s = s.split(b"\x00")[0]
                try:
                    txt = s.decode()
                except Exception:
                    txt = repr(s)
                rows.append((tgt, srcs, txt))
        for tgt, srcs, txt in rows:
            print("0x%08X  <- %s   %r" % (tgt, " ".join("0x%08X" % x for x in srcs[:6]), txt[:60]))
        print("total", len(rows))
