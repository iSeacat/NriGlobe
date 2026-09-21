#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""社媒吐槽日报生成模板（中性示例）。

真实环境里，你的日报脚本通常由抓取/总结流程产出；这个模板只演示
「日报 HTML 长什么样」，即 `scripts/build.py` 能解析的最小输入结构。

输出结构与 content/social/*-sample.html 完全一致，可直接被 build.py 解析。

用法：
    python scripts/gen_social_daily_example.py                      # 写入 content/social
    python scripts/gen_social_daily_example.py --line 示例产品线A --out content/social
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 目标市场：build.py 会解析这一行作为该报告的默认市场
TARGET_MARKETS = "美国 / 日本"

# 每条痛点：(痛点类别, 影响产品, 目标国家, 严重度, 证据/来源文字, 来源链接)
ROWS: list[tuple[str, str, str, str, str, str]] = [
    ("充电接口规格不兼容", "示例产品线A 主机", "美国/日本", "🔴 高", "示例-无", "https://example.com/forum/101"),
    ("说明书缺少本地语言版本", "示例产品线A 整套", "日本", "🟡 中", "示例-无", "https://example.com/review/102"),
    ("包装在途破损", "示例产品线A 配件包", "美国", "🟢 低", "示例-无", "https://example.com/forum/103"),
]

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{line}社媒吐槽日报-{d}</title></head>
<body>
<h1>{line}社媒吐槽日报-{d}</h1>
<p>🎯 目标市场：{markets}</p>
<p>本文件为示例数据，内容为虚构演示。列名需与 build.py 的 COL_PATTERNS 对齐。</p>
<table>
  <tr>
    <th>痛点类别</th><th>影响产品</th><th>目标国家</th><th>严重度</th><th>历史关联条目</th><th>来源</th>
  </tr>
{rows}
</table>
</body>
</html>
"""

ROW = """  <tr>
    <td>{title}</td>
    <td>{product}</td>
    <td>{market}</td>
    <td>{severity}</td>
    <td>{evidence}</td>
    <td><a href="{url}">{url}</a></td>
  </tr>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", default="示例产品线A", help="产品线名（也是 build.py 从文件名取的 line）")
    ap.add_argument("--markets", default=TARGET_MARKETS)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--out", default=str(ROOT / "content" / "social"), help="输出目录")
    args = ap.parse_args()

    rows = "\n".join(
        ROW.format(title=t, product=p, market=m, severity=s, evidence=e, url=u)
        for t, p, m, s, e, u in ROWS
    )
    html = TEMPLATE.format(line=args.line, d=args.date, markets=args.markets, rows=rows)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{args.line}社媒吐槽日报-{args.date}.html"
    target.write_text(html, encoding="utf-8")
    print(f"✔ 写入 {target}")
    print(f"  下一步：python scripts/build.py --social {out_dir} --out data/dataset.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
