import re, collections
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_DIS = _sys.argv[1] if len(_sys.argv) > 1 else _os.path.join(_ROOT, "build", "app.dis")
if not _os.path.exists(_DIS):
    _sys.exit("找不到反汇编文件 %s\n请先运行: python tools/reverse/xdis.py > build/app.dis" % _DIS)


rows = []
for line in open(_DIS, encoding="utf-8", errors="replace"):
    m = re.match(r"^\s*([0-9a-f]{8}):\t([0-9a-f]{6})\s+(\S+)\s*(.*)$", line.rstrip("\n"))
    if m:
        rows.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3), m.group(4).strip()))

def s18(x):
    x &= 0x3FFFF
    return x - 0x40000 if x & 0x20000 else x

# collect (op0, V, pc, target) for branches with a final hex target
byop = collections.defaultdict(list)
for pc, V, mn, ops in rows:
    m = re.search(r"0x([0-9a-f]{8})$", ops)
    if not m:
        continue
    if mn in ("call0", "j"):
        continue
    t = int(m.group(1), 16)
    byop[V & 0xF].append((pc, V, mn, t))

for op0, lst in sorted(byop.items()):
    print("op0=%X  n=%d  mnemonics=%s" % (op0, len(lst), collections.Counter(x[2] for x in lst).most_common(6)))
    if len(lst) < 20:
        continue
    # try formulas
    for name, f in [
        ("PC+4+imm8", lambda pc, V: (pc + 4 + ((V >> 16) & 0xFF) - (0x100 if ((V >> 16) & 0x80) else 0))),
        ("PC+4+s18(V>>6)", lambda pc, V: (pc + 4 + s18(V >> 6))),
        ("PC+4+s18(V>>6)*4", lambda pc, V: (pc + 4 + s18(V >> 6) * 4)),
        ("PC+4+s16(V>>8)", lambda pc, V: (pc + 4 + (((V >> 8) & 0xFFFF) - (0x10000 if ((V >> 8) & 0x8000) else 0)))),
        ("PC+4+s12(V>>12)", lambda pc, V: (pc + 4 + (((V >> 12) & 0xFFF) - (0x1000 if ((V >> 12) & 0x800) else 0)))),
    ]:
        good = sum(1 for pc, V, mn, t in lst if f(pc, V) == t)
        if good:
            print("    %-20s %d/%d" % (name, good, len(lst)))
