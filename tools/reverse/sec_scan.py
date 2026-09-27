import re, os, json
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

# ---------- 1. all printable strings ----------
strs = []
for m in re.finditer(rb'[\x20-\x7e]{5,}', data):
    strs.append((m.start(), m.group().decode('ascii')))
with open(os.path.join(out, 'strings_all.txt'), 'w', encoding='utf-8') as f:
    for off, s in strs:
        f.write('%06X  %s\n' % (off, s))
print('total strings >=5:', len(strs))

# ---------- 2. network endpoints ----------
urls = sorted({s for _, s in strs if re.search(r'https?://|wss?://|ftp://', s)})
ips  = sorted({s for _, s in strs if re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', s)})
doms = sorted({s for _, s in strs if re.search(r'\b[a-z0-9][a-z0-9\-]{1,40}\.(com|cn|net|org|io|top|xyz|ru|info|cc|tk|pw|me|de|jp|app|dev|link|online|site|club|shop)\b', s, re.I)})

def dump(name, items):
    with open(os.path.join(out, name), 'w', encoding='utf-8') as f:
        for x in items:
            f.write(x + '\n')
    print('\n=== %s (%d) ===' % (name, len(items)))
    for x in items[:60]:
        print('  ', x[:160])

dump('urls.txt', urls)
dump('ip_like.txt', ips)
dump('domains.txt', doms)

# ---------- 3. high-risk keywords ----------
cats = {
 'backdoor/shell': ['system(', '/bin/sh', 'exec', 'shell', 'telnet', 'backdoor', 'root:', 'admin', 'passwd', 'password', 'secret', 'token', 'api_key', 'apikey'],
 'attack/wifi':    ['deauth', 'disassoc', 'promiscuous', 'sniffer', 'sniff', 'beacon', 'handshake', 'pmkid', 'wpa', 'inject', 'freedom', 'monitor mode', 'jam', 'flood', 'spoof', 'attack', 'hack', 'exploit', 'brute'],
 'ota/update':     ['OTA', 'ota', 'Update', 'update', 'firmware', 'espota', '3232', 'upgrade', 'flash'],
 'command/proto':  ['cmd', 'command', 'AT+', 'gpio', 'GPIO', 'relay', 'switch', 'state', 'set', 'get', 'write', 'read'],
 'mqtt':           ['mqtt', 'MQTT', 'broker', 'topic', 'publish', 'subscribe'],
 'http/routes':    ['/', '.php', '.html', '.cgi', '/api', '/config', '/update', '/set', 'GET ', 'POST '],
}
report = []
for cat, kws in cats.items():
    report.append('\n########## %s ##########' % cat)
    for kw in kws:
        hits = [(o, s) for o, s in strs if kw in s]
        if hits:
            report.append('--- keyword %r : %d hits' % (kw, len(hits)))
            for o, s in hits[:25]:
                report.append('   %06X  %s' % (o, s[:150]))
with open(os.path.join(out, 'keywords_report.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))
print('\nkeyword report ->', os.path.join(out, 'keywords_report.txt'))
print('strings dump  ->', os.path.join(out, 'strings_all.txt'))
