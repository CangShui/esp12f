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
os.makedirs(out, exist_ok=True)
rep = []

# ---- 1. stored config (EEPROM 0xFB000) decoded ----
rep.append('### 1. 芯片内已保存的配置（EEPROM 区 0xFB000，明文）\n')
eep = data[0xFB000:0xFB000+0x200]
for i in range(0, 0x200, 32):
    chunk = eep[i:i+32]
    if all(b == 0xFF for b in chunk) or all(b == 0 for b in chunk):
        continue
    txt = chunk.split(b'\x00')[0]
    try:
        s = txt.decode('utf-8')
    except Exception:
        s = txt.decode('latin-1')
    rep.append('  +0x%03X  %-60s | hex: %s' % (i, repr(s)[:60], chunk.hex(' ')))

rep.append('\n### 2. 应用 EEPROM 副本（0xFD000 / 0xFE000）\n')
for base in (0xFD000, 0xFE000):
    seg = data[base:base+0x200]
    for i in range(0, 0x200, 16):
        chunk = seg[i:i+16]
        if all(b in (0x00, 0xFF) for b in chunk):
            continue
        rep.append('  0x%05X+0x%03X  %s' % (base, i, chunk.hex(' ')))

# ---- 3. attack-capability keyword sweep over whole image ----
rep.append('\n### 3. 攻击能力关键词全镜像扫描（>=4 字符可打印串）\n')
attack_kw = ['deauth', 'disassoc', 'beacon', 'inject', 'promiscuous', 'sniff', 'monitor',
             'freedom', 'raw80211', 'wifi_send_pkt', 'ieee80211', 'wpa2', 'handshake',
             'pmkid', 'brute', 'flood', 'spoof', 'evil', 'twin', 'karma', 'attack',
             'hack', 'exploit', 'payload', 'shell', 'telnet', 'backdoor', 'reverse',
             'system(', 'execve', '/bin/', 'socket', 'connect to', 'port scan', 'nmap']
found = {}
for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
    s = m.group().decode('ascii')
    low = s.lower()
    for kw in attack_kw:
        if kw in low:
            found.setdefault(kw, []).append((m.start(), s))
if not found:
    rep.append('  未发现任何攻击类关键词\n')
for kw, hits in found.items():
    rep.append('  [%s] %d 处:' % (kw, len(hits)))
    for off, s in hits[:6]:
        rep.append('     0x%05X  %s' % (off, s[:120]))

# ---- 4. all network endpoints ----
rep.append('\n### 4. 固件中所有网络地址\n')
ep = sorted({s for _, s in [(m.start(), m.group().decode('ascii')) for m in re.finditer(rb'[\x20-\x7e]{4,}', data)]
             if re.search(r'https?://|[a-z0-9\-]+\.(top|com|cn|net|org|io|xyz|ru|info)\b', s, re.I)})
for s in ep:
    rep.append('  ' + s[:140])
if not ep:
    rep.append('  （无）')

# ---- 5. TLS / crypto ----
rep.append('\n### 5. 传输安全相关\n')
for kw in ['https://', 'BEGIN CERTIFICATE', 'mbedtls', 'SSL', 'bearssl', 'AES', 'signature', 'Signature', 'md5', 'MD5', 'sha256', 'SHA256']:
    c = data.count(kw.encode())
    rep.append('  %-22s 出现 %d 次' % (kw, c))

open(os.path.join(out, 'SECURITY_REPORT.md'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep))
