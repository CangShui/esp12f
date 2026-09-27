import re, os
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
out = _os.path.join(_ROOT, "build", "sec")

def region_dump(name, start, end, minlen=4):
    lines = []
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data[start:end]):
        lines.append('%06X  %s' % (start + m.start(), m.group().decode('ascii')))
    with open(os.path.join(out, name), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('%-28s %4d strings -> %s' % (name, len(lines), name))
    return lines

# app string table area (where app-specific strings live)
app = region_dump('app_strings_4F000_52000.txt', 0x4F000, 0x52000, 4)
print('\n===== app string table (0x4F000-0x52000) =====')
for l in app:
    print(' ', l[:150])

print('\n\n===== tail region 0xF0000-0x100000 =====')
tail = region_dump('tail_strings.txt', 0xF0000, 0x100000, 4)
for l in tail:
    print(' ', l[:150])

print('\n\n===== non-FF byte ranges in tail (0xF0000+) =====')
run = None
for i in range(0xF0000, len(data)):
    if data[i] != 0xFF:
        if run is None:
            run = i
    else:
        if run is not None:
            if i - run >= 4:
                print('  0x%05X - 0x%05X  (%d bytes)  head=%s' % (run, i-1, i-run, data[run:run+24].hex(' ')))
            run = None
if run is not None:
    print('  0x%05X - 0x%05X  (%d bytes)' % (run, len(data)-1, len(data)-run))
