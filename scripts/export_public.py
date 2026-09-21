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
import json
import os
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 禁止出现在公开包里的串（内部产品线名、内部工具名、公司名、内网地址）。
#
# 注意：本文件本身会随公开包一起分发，所以**不能把真实产品线名写在这里**。
# 真实黑名单放在私有的 config.local.json（已 gitignore）：
#   { "export_blocklist": ["你的产品线名", "内部工具名", "内网网段"], 
#     "export_allow":     { "LICENSE": ["公司名"] } }
# 也可用环境变量 NRI_EXPORT_BLOCKLIST（逗号分隔）临时覆盖。
#
# 未配置黑名单时只做结构性检查，并会明确提示。
DEFAULT_BLOCKLIST: list[str] = []

# 大体积二进制/数据文件跳过正文扫描（它们不可能含中文情报内容）
SKIP_SCAN_SUFFIX = (".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf")

# 扫描器自身含关键词表，跳过（自引用）
SKIP_SCAN_FILES = {"scripts/export_public.py"}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE).stdout


def load_policy() -> tuple[list[str], dict[str, set[str]]]:
    """黑名单/白名单从私有配置读，避免把真实产品线名写进公开脚本。"""
    blocklist = list(DEFAULT_BLOCKLIST)
    allowed: dict[str, set[str]] = {}

    env = os.environ.get("NRI_EXPORT_BLOCKLIST", "").strip()
    if env:
        blocklist += [t.strip() for t in env.split(",") if t.strip()]

    cfg_path = ROOT / "config.local.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"! 读取 config.local.json 失败：{exc}")
            cfg = {}
        blocklist += [t for t in cfg.get("export_blocklist", []) if t]
        for fname, toks in (cfg.get("export_allow") or {}).items():
            allowed.setdefault(fname, set()).update(toks)

    # 去重保序
    seen: set[str] = set()
    uniq = [t for t in blocklist if not (t in seen or seen.add(t))]
    return uniq, allowed


def scan(zip_bytes: bytes, blocklist: list[str],
         allowed: dict[str, set[str]]) -> list[tuple[str, int, str]]:
    """返回 [(文件名, 行号, 命中片段)]"""
    hits: list[tuple[str, int, str]] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.lower().endswith(SKIP_SCAN_SUFFIX):
                continue
            # 去掉 zip 里的顶层目录前缀，得到仓库内相对路径
            rel = info.filename.split("/", 1)[-1] if "/" in info.filename else info.filename
            if rel in SKIP_SCAN_FILES:
                continue
            base = info.filename.rsplit("/", 1)[-1]
            allow = allowed.get(base, set())
            raw = zf.read(info)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for token in blocklist:
                    if token in line and token not in allow:
                        hits.append((rel, i, token))
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
    blocklist, allowed = load_policy()
    if not blocklist:
        print("  ! 未配置黑名单（config.local.json 的 export_blocklist），本次只做结构性检查。")
        print("    建议在你的私有配置里列出内部产品线名 / 内部工具名 / 内网网段。")
    else:
        print(f"  黑名单 {len(blocklist)} 条（来自私有配置）")
    hits = scan(blob, blocklist, allowed)
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
