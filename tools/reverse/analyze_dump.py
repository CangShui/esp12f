import struct, re, sys, hashlib, os
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


path = _resolve_bin()
data = open(path, 'rb').read()
print('file:', os.path.basename(path))
print('size:', len(data), '(0x%X)' % len(data))
print('sha256:', hashlib.sha256(data).hexdigest().upper())
print()

print('=== first 64 bytes ===')
print(data[:64].hex(' '))
print()
print('boot magic @0x00000:', '0x%02X' % data[0], '(ESP8266 image = 0xE9)' if data[0] == 0xE9 else '(NOT an image header)')
for off in (0x1000, 0x2000, 0x8000, 0x10000, 0x7C000, 0xFC000):
    print('byte @0x%05X = 0x%02X' % (off, data[off]))

print()
print('=== ESP8266 image headers (0xE9) ===')
for off in range(0, len(data) - 8, 0x1000):
    if data[off] == 0xE9:
        segs, spi_mode, spi_sz_freq = data[off+1], data[off+2], data[off+3]
        entry = struct.unpack('<I', data[off+4:off+8])[0]
        print('  0x%05X: segments=%d spi=0x%02X entry=0x%08X' % (off, segs, spi_sz_freq, entry))

print()
print('=== partition table candidates (magic 0xAA50) ===')
for off in range(0, len(data) - 32, 0x1000):
    if data[off] == 0xAA and data[off+1] == 0x50:
        print('  table @0x%05X' % off)
        for i in range(8):
            e = data[off + i*32: off + i*32 + 32]
            if len(e) < 32 or e[:2] != b'\xaa\x50':
                break
            t, st, so, ss = e[2], e[3], struct.unpack('<I', e[4:8])[0], struct.unpack('<I', e[8:12])[0]
            label = e[12:28].rstrip(b'\x00').decode('ascii', 'replace')
            print('    type=%d sub=%d off=0x%05X size=0x%05X %s' % (t, st, so, ss, label))

print()
print('=== printable strings (len>=6) ===')
seen = set()
for m in re.finditer(rb'[\x20-\x7e]{6,}', data):
    s = m.group().decode('ascii')
    if s not in seen:
        seen.add(s)
        print('  0x%05X  %s' % (m.start(), s[:110]))
    if len(seen) > 120:
        print('  ... (truncated)')
        break
