#!/usr/bin/env python3
import struct, collections, sys
from xl32r import all_l32r, d, foff_of, SEGS

refs = all_l32r()
by_lit = collections.defaultdict(list)
for pc, t, tgt in refs:
    by_lit[tgt].append(pc)

# value ranges
APPSTR_LO, APPSTR_HI = 0x3FFE8510, 0x3FFE9C10
rows = []
for lit, srcs in by_lit.items():
    fo = foff_of(lit)
    if fo is None:
        continue
    val = struct.unpack_from("<I", d, fo)[0]
    if APPSTR_LO <= val < APPSTR_HI:
        txt = d[foff_of(val):foff_of(val) + 40].split(b"\x00")[0]
        try:
            txt = txt.decode()
        except Exception:
            txt = repr(txt)
        rows.append((val, lit, sorted(srcs), txt))
rows.sort()

# 输出到 <repo>/build/appstr_refs.txt（而不是当前工作目录，避免污染仓库）
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
OUT = _os.path.join(_ROOT, "build", "appstr_refs.txt")
_os.makedirs(_os.path.dirname(OUT), exist_ok=True)

out = open(OUT, "w", encoding="utf-8")
for val, lit, srcs, txt in rows:
    out.write("0x%08X lit@0x%08X code=%s  %r\n" % (val, lit, " ".join("0x%08X" % x for x in srcs), txt[:70]))
out.close()
print("literals->appstrings:", len(rows))
print("输出 ->", OUT)
# where is the referencing code?
codeaddrs = collections.Counter()
for val, lit, srcs, txt in rows:
    for s in srcs:
        codeaddrs[s] += 1
lo = min(codeaddrs); hi = max(codeaddrs)
print("code addr range 0x%08X - 0x%08X" % (lo, hi))
for seg in SEGS:
    f, v, sz = seg
    inside = [a for a in codeaddrs if v <= a < v + sz]
    if inside:
        print("  segment vma 0x%08X size 0x%X : %d refs, 0x%08X..0x%08X" % (v, sz, len(inside), min(inside), max(inside)))
print(open(OUT, encoding="utf-8").read()[:4000])
