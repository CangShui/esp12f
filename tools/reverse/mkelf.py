#!/usr/bin/env python3
"""Rebuild an ELF32/xtensa from the ESP8266 app image inside a full flash dump,
so that xtensa-lx106-elf-objdump / radare2 / ghidra can disassemble it."""
import struct, sys, os
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_os.path.dirname(_HERE))
_DEFAULT_BIN = _os.path.join(_ROOT, "backup", "es12f_firmware_backup_1MB.bin")

SRC = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_BIN
IMG_OFF = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x1000
OUT = sys.argv[3] if len(sys.argv) > 3 else _os.path.join(_ROOT, "build", "app.elf")

data = open(SRC, "rb").read()

# --- parse image header ---
magic, nseg, csum = struct.unpack_from("<BBH", data, IMG_OFF)
assert magic == 0xE9, hex(magic)
p = IMG_OFF + 8
segs = []
for i in range(nseg):
    addr, sz = struct.unpack_from("<II", data, p)
    segs.append((addr, data[p + 8:p + 8 + sz]))
    p += 8 + sz
entry = struct.unpack_from("<I", data, p)[0]
print("segments:")
for a, b in segs:
    print("  0x%08X  %d bytes" % (a, len(b)))
print("entry raw = 0x%08X" % entry)

# ESP8266: entry stored at end is 0 for SDK-built images; real entry is in the
# boot header (first image) -> use the app image's own reset vector convention.
if entry == 0:
    entry = 0x40080E18  # placeholder; SDK calls user_init from irom

# --- build ELF ---
def align(x, a):
    return (x + a - 1) & ~(a - 1)

names = []
for i, (a, b) in enumerate(segs):
    if 0x40200000 <= a < 0x40300000:
        names.append(".irom0.text%d" % i)
    elif 0x40100000 <= a < 0x40110000:
        names.append(".iram1.%d" % i)
    elif 0x3FFE8000 <= a < 0x40000000:
        names.append(".dram0.data%d" % i)
    else:
        names.append(".seg%d" % i)

shstr = b"\x00"
name_off = []
for n in [".shstrtab"] + names:
    name_off.append(len(shstr))
    shstr += n.encode() + b"\x00"

# layout: ehdr | shdrs | section data | shstrtab
ehsize = 52
shnum = 2 + len(segs)  # null, shstrtab + segs
shoff = ehsize
data_off = align(shoff + shnum * 40, 16)

offsets = []
cur = data_off
for a, b in segs:
    offsets.append(cur)
    cur = align(cur + len(b), 16)
shstr_off = cur
cur += len(shstr)
total = cur

buf = bytearray(b"\x00" * total)

# ELF header
struct.pack_into("<4sBBBBB7x", buf, 0, b"\x7fELF", 1, 1, 1, 0, 0)
struct.pack_into("<HHIIIIIHHHHHH", buf, 16,
                 1,      # ET_REL (fine for objdump -D)
                 94,     # EM_XTENSA
                 1,      # version
                 entry,
                 0,      # phoff
                 shoff,
                 0,      # flags
                 ehsize,
                 0, 0,   # phentsize, phnum
                 40, shnum, 1 + len(segs))  # shentsize, shnum, shstrndx

for i, (a, b) in enumerate(segs):
    buf[offsets[i]:offsets[i] + len(b)] = b
buf[shstr_off:shstr_off + len(shstr)] = shstr

def put_sh(idx, name, typ, flags, addr, off, size, link=0, info=0, align_=4, entsize=0):
    struct.pack_into("<IIIIIIIIII", buf, shoff + idx * 40,
                     name, typ, flags, addr, off, size, link, info, align_, entsize)

put_sh(0, 0, 0, 0, 0, 0, 0)
for i, (a, b) in enumerate(segs):
    flags = 0x6 if not (0x3FFE8000 <= a < 0x40000000) else 0x3  # AX / WA
    if a >= 0x3FFE8000 and a < 0x40000000:
        flags = 0x2  # ALLOC only (data)
    put_sh(1 + i, name_off[1 + i], 1, flags, a, offsets[i], len(b), 0, 0, 16)
put_sh(1 + len(segs), name_off[0], 3, 0, 0, shstr_off, len(shstr), 0, 0, 1)

open(OUT, "wb").write(bytes(buf))
print("wrote", OUT, total, "bytes; sections:", names)
