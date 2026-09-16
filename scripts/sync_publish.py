#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把编译好的成品同步到共享盘展示层（同事双击就能看）。

    python scripts/sync_publish.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))   # 允许 import nri_config
import nri_config  # noqa: E402

DEST = nri_config.publish_dir()

PARTS = ["index.html", "lib", "data"]


def main() -> int:
    if not DEST.parent.exists():
        print(f"跳过同步：共享盘目录不存在 {DEST.parent}")
        return 0
    DEST.mkdir(parents=True, exist_ok=True)
    for p in PARTS:
        src = ROOT / p
        dst = DEST / p
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print("  同步", p, "->", dst)
    print("✔ 成品已同步到", DEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
