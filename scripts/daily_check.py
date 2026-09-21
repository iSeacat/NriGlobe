#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日更新的第一道闸：只在数据源免费窗口内放行抓取。

    python scripts/daily_check.py            # 检查是否在免费窗口
    python scripts/daily_check.py --wait     # 不在窗口内则等待到窗口开始（受 max_wait_minutes 限制）

返回码：
    0 = 放行（在免费窗口内，可以抓新闻/社媒）
    1 = 拦截（不在窗口内 / 等待超时，必须停止抓取）
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "content" / "free_window.json"
LOG_DIR = ROOT / "logs"
CST = timezone(timedelta(hours=8))


def load_cfg() -> dict:
    if not CFG_PATH.exists():
        return {"free_window": {"enabled": True, "start": "00:00", "end": "09:00"},
                "job": {"max_wait_minutes": 150}}
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S") + " " + msg
    with (LOG_DIR / "daily.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def parse_hm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def now_shanghai() -> datetime:
    return datetime.now(CST)


def in_window(now: datetime, cfg: dict) -> bool:
    w = cfg.get("free_window", {})
    if not w.get("enabled", True):
        return True
    sh, sm = parse_hm(w.get("start", "00:00"))
    eh, em = parse_hm(w.get("end", "09:00"))
    mins = now.hour * 60 + now.minute
    a, b = sh * 60 + sm, eh * 60 + em
    if a <= b:
        return a <= mins < b
    return mins >= a or mins < b  # 跨零点窗口，如 23:00-08:00


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", action="store_true", help="不在窗口内时等待到窗口开始")
    args = ap.parse_args()

    cfg = load_cfg()
    now = now_shanghai()
    w = cfg.get("free_window", {})

    if in_window(now, cfg):
        log("GATE PASS 中国时间 %s 在免费窗口 %s-%s 内，允许抓取"
            % (now.strftime("%Y-%m-%d %H:%M"), w.get("start"), w.get("end")))
        return 0

    if args.wait:
        sh, sm = parse_hm(w.get("start", "00:00"))
        target = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_s = (target - now).total_seconds()
        max_s = int(cfg.get("job", {}).get("max_wait_minutes", 150)) * 60
        if wait_s > max_s:
            log("GATE BLOCK 中国时间 %s 不在免费窗口，且需等待 %.0f 分钟 > 上限 %d 分钟，停止抓取"
                % (now.strftime("%Y-%m-%d %H:%M"), wait_s / 60, max_s / 60))
            return 1
        log("GATE WAIT 中国时间 %s 不在免费窗口，等待 %.0f 分钟到 %s"
            % (now.strftime("%Y-%m-%d %H:%M"), wait_s / 60, target.strftime("%H:%M")))
        time.sleep(wait_s)
        log("GATE PASS 已等到中国时间 %s，进入免费窗口" % now_shanghai().strftime("%Y-%m-%d %H:%M"))
        return 0

    log("GATE BLOCK 中国时间 %s 不在免费窗口 %s-%s，停止抓取（不消耗付费额度）"
        % (now.strftime("%Y-%m-%d %H:%M"), w.get("start"), w.get("end")))
    return 1


if __name__ == "__main__":
    sys.exit(main())
