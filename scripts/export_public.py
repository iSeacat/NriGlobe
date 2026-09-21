#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出「可公开分发」的干净包：从 git 已跟踪文件导出，并做泄露扫描。

为什么不能直接压缩工作目录：工作目录里混着私有物 ——
  data/dataset.js（真实情报，几十万字符）、config.local.json（内网路径）、
  media/（含真实打点的截图）、logs/、.workbuddy/、scripts/gen_social_daily_*.py（真实产品线）。
这些都在 .gitignore 里，所以「从 git 导出」天然干净。

流程：git archive（已跟踪文件） -> 逐文件泄露扫描 -> 通过才落盘 zip。
扫描不通过时**不产出压缩包**（fail-closed），并列出命中行。

用法：
    python scripts/export_public.py                     # 版本号=当天日期
    python scripts/export_public.py --version 0.1.0
    python scripts/export_public.py --out dist
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 禁止出现在公开包里的串（内部产品线名、内部工具名、公司名、内网地址）
FORBIDDEN = [
    "示例产品线A", "示例产品线B", "示例产品线C", "海猫", "佛山",
    "AI 模型", "部署服务器",
    "内网地址", "VPN地址", "共享盘",
]

# 大体积二进制/数据文件跳过正文扫描（它们不可能含中文情报内容）
SKIP_SCAN_SUFFIX = (".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf")

# 白名单：这些文件里的这些串属正当署名（MIT 要求写明著作权人），不算泄露。
# 若不想公开公司名，把 LICENSE 第 3 行改成个人/中性名义，然后把下面这行清空即可。
ALLOWED: dict[str, set[str]] = {
    "LICENSE": {"佛山", "海猫"},
}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE).stdout


def scan(zip_bytes: bytes) -> list[tuple[str, int, str]]:
    """返回 [(文件名, 行号, 命中片段)]"""
    hits: list[tuple[str, int, str]] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.lower().endswith(SKIP_SCAN_SUFFIX):
                continue
            base = info.filename.rsplit("/", 1)[-1]
            allowed = ALLOWED.get(base, set())
            raw = zf.read(info)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for token in FORBIDDEN:
                    if token in line and token not in allowed:
                        hits.append((info.filename, i, token))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=date.today().isoformat())
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args()

    name = f"NriGlobe-{args.version}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{name}.zip"

    dirty = git("status", "--porcelain").decode("utf-8", "replace").strip()
    if dirty:
        print("! 工作区有未提交改动，导出的包 = 最后一次提交的内容，不含这些改动：")
        for line in dirty.splitlines():
            print("   ", line)
        print()

    print(f"→ 从 git 导出已跟踪文件（{name}）…")
    blob = git("archive", "--format=zip", f"--prefix={name}/", "HEAD")

    n_files = 0
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        n_files = sum(1 for i in zf.infolist() if not i.is_dir())
    print(f"  已跟踪文件 {n_files} 个，压缩后 {len(blob)/1024:.0f} KB")

    print("→ 泄露扫描…")
    hits = scan(blob)
    if hits:
        print(f"\n✖ 命中 {len(hits)} 处敏感串，**不产出压缩包**：")
        for f, line_no, token in hits[:40]:
            print(f"   [{token}] {f}:{line_no}")
        if len(hits) > 40:
            print(f"   …另有 {len(hits) - 40} 处")
        print("\n请先清理以上内容，再重新导出。")
        return 1

    target.write_bytes(blob)
    print(f"\n✔ 扫描通过，已产出：{target}")
    print(f"  {target.stat().st_size/1024:.0f} KB —— 可直接对外分发（仅示例数据，无真实情报）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
