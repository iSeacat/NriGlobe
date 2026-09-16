# -*- coding: utf-8 -*-
"""NRI 情报地球：路径配置解析（与部署环境解耦）。

解析优先级（后者覆盖前者）：
    1. config.local.json  —— 本机私有配置，已在 .gitignore 中，禁止提交
    2. 环境变量 NRI_NEWS_DIR / NRI_SOCIAL_DIR / NRI_PUBLISH_DIR
    3. 相对默认（仓库内 content/news、content/social、publish）

本地私有配置示例（不要提交到仓库）：
{
  "news_dir":   "D:\\\\your\\\\news-folder",
  "social_dir": "D:\\\\your\\\\social-folder",
  "publish_dir": "D:\\\\your\\\\publish-folder"
}
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load() -> dict:
    cfg: dict = {}
    local = ROOT / "config.local.json"
    if local.is_file():
        try:
            cfg.update(json.loads(local.read_text(encoding="utf-8")))
        except Exception:
            pass
    for key in ("news_dir", "social_dir", "publish_dir"):
        env = os.environ.get("NRI_" + key.upper())
        if env:
            cfg[key] = env
    return cfg


_CFG = _load()


def _resolve(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p)


def news_dir() -> Path:
    return _resolve(_CFG.get("news_dir", "content/news"))


def social_dir() -> Path:
    return _resolve(_CFG.get("social_dir", "content/social"))


def publish_dir() -> Path:
    return _resolve(_CFG.get("publish_dir", "publish"))
