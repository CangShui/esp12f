import re, sys
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_DIS = _sys.argv[1] if len(_sys.argv) > 1 else _os.path.join(_ROOT, "build", "app.dis")
if not _os.path.exists(_DIS):
    _sys.exit("找不到反汇编文件 %s\n请先运行: python tools/reverse/xdis.py > build/app.dis" % _DIS)


rows = []
for line in open(_DIS, encoding="utf-8", errors="replace"):
    m = re.match(r"^\s*([0-9a-f]{8}):\t([0-9a-f]{4})\s+(\S+)\s*(.*)$", line.rstrip("\n"))
    if m:
        rows.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3), m.group(4).strip()))

def num(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith(("0x", "-0x")) else int(s, 10)

def reg(s):
    m = re.match(r"a(\d+)$", s.strip())
    return int(m.group(1)) if m else None

def fit(name, nfields, parse):
    samples = []
    unparsed = []
    for pc, raw, mn, ops in rows:
        if mn != name:
            continue
        p = parse(ops)
        if p is None:
            if len(unparsed) < 3:
                unparsed.append(ops)
            continue
        samples.append((raw,) + tuple(p))
    print("== %s  samples=%d unparsed=%s" % (name, len(samples), unparsed))
    if not samples:
        return
    for fi in range(nfields):
        vals = [s[fi + 1] for s in samples]
        mx = max(vals)
        nb = max(1, mx.bit_length())
        res = []
        for bit in range(nb):
            cands = [p for p in range(16)
                     if all(((v >> bit) & 1) == ((raw >> p) & 1) for raw, v in [(s[0], s[fi + 1]) for s in samples])]
            res.append(cands)
        print("   field%d max=%d -> V bits %s" % (fi, mx, res))

fit("movi.n", 2, lambda o: (lambda m: (reg(m.group(1)), num(m.group(2))))(re.match(r"(a\d+),\s*(-?(?:0x)?[0-9a-fA-F]+)$", o)) if re.match(r"(a\d+),\s*(-?(?:0x)?[0-9a-fA-F]+)$", o) else None)
fit("l32i.n", 3, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2)), num(m.group(3))))(re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o)) if re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o) else None)
fit("s32i.n", 3, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2)), num(m.group(3))))(re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o)) if re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o) else None)
fit("mov.n", 2, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2))))(re.match(r"(a\d+),\s*(a\d+)$", o)) if re.match(r"(a\d+),\s*(a\d+)$", o) else None)
fit("addi.n", 3, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2)), num(m.group(3))))(re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o)) if re.match(r"(a\d+),\s*(a\d+),\s*(-?\d+)$", o) else None)
fit("add.n", 3, lambda o: (lambda m: (reg(m.group(1)), reg(m.group(2)), reg(m.group(3))))(re.match(r"(a\d+),\s*(a\d+),\s*(a\d+)$", o)) if re.match(r"(a\d+),\s*(a\d+),\s*(a\d+)$", o) else None)
