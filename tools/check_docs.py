#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档与目录对齐检查：校验所有 markdown 链接指向的文件真实存在。

用法:  python tools/check_docs.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

docs = [os.path.join(ROOT, "README.md")]
for sub in ("docs", "tools"):
    for dp, dn, fn in os.walk(os.path.join(ROOT, sub)):
        docs += [os.path.join(dp, f) for f in fn if f.endswith(".md")]

LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)\)")
bad, ok = [], 0
for doc in docs:
    base = os.path.dirname(doc)
    for m in LINK.finditer(open(doc, encoding="utf-8").read()):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:")):
            continue
        t2 = t.replace("\\", "/")
        if (os.path.exists(os.path.normpath(os.path.join(base, t2)))
                or os.path.exists(os.path.normpath(os.path.join(ROOT, t2)))):
            ok += 1
        else:
            bad.append((os.path.relpath(doc, ROOT), t))

print("检查了 %d 个 markdown 文件" % len(docs))
print("链接有效: %d" % ok)
print("链接失效: %d" % len(bad))
for d, t in bad:
    print("   %-30s -> %s" % (d, t))
if bad:
    sys.exit(1)
print("\n文档与目录完全对齐 OK")
