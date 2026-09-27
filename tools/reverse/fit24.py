import re
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

def num(s):
    s = s.strip()
    if s.lower().startswith(("-0x", "0x")):
        return int(s, 16)
    return int(s, 10)

def reg(s):
    m = re.match(r"a(\d+)$", s.strip())
    return int(m.group(1)) if m else None

def fit(name, nfields, parse, limit=None):
    samples = []
    unparsed = []
    for pc, raw, mn, ops in rows:
        if mn != name:
            continue
        p = parse(ops)
        if p is None:
            if len(unparsed) < 4:
                unparsed.append(ops)
            continue
        samples.append((raw,) + tuple(p))
        if limit and len(samples) >= limit:
            break
    print("== %s samples=%d unparsed=%s" % (name, len(samples), unparsed))
    if not samples:
        return
    for fi in range(nfields):
        vals = [s[fi + 1] for s in samples]
        mx = max(vals)
        nb = max(1, mx.bit_length())
        res = []
        for bit in range(nb):
            cands = [p for p in range(24)
                     if all(((v >> bit) & 1) == ((raw >> p) & 1) for raw, v in [(s[0], s[fi + 1]) for s in samples])]
            res.append(cands)
        print("   field%d max=%d -> V bits %s" % (fi, mx, res))

R3 = r"(a\d+),\s*(a\d+),\s*(a\d+)"
R2 = r"(a\d+),\s*(a\d+)"

fit("movi", 2, lambda o: (lambda m: (reg(m.group(1)), num(m.group(2))))(re.match(r"(a\d+),\s*(-?(?:0x)?[0-9a-fA-F]+)$", o)) if re.match(r"(a\d+),\s*(-?(?:0x)?[0-9a-fA-F]+)$", o) else None)
fit("addi", 3, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2)), num(m.group(3))))(re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o)) if re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o) else None)
fit("add", 3, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2)), reg(m.group(3))))(re.match(R3 + "$", o)) if re.match(R3 + "$", o) else None)
fit("callx0", 1, lambda o: (reg(o),) if reg(o) is not None else None)
fit("call0", 1, lambda o: (int(o, 16),) if re.match(r"0x[0-9a-f]+$", o) else None)
fit("j", 1, lambda o: (int(o, 16),) if re.match(r"0x[0-9a-f]+$", o) else None)
