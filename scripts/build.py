#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「每日新闻」的 Markdown 与「每日社媒」的 HTML 日报，编译成地球打点数据。

内容（源）-> 校验 -> data/dataset.js（前端消费，禁止手改）

用法：
    python scripts/build.py                                      # 用 config.local.json / 环境变量 / 相对默认
    python scripts/build.py --news <dir> --social <dir>          # 显式指定源目录
    python scripts/build.py --out data/dataset.example.js        # 指定输出文件（便于生成示例数据）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts"))   # 允许 import nri_config
import nri_config  # noqa: E402

DEFAULT_NEWS = nri_config.news_dir()
DEFAULT_SOCIAL = nri_config.social_dir()

CJK = re.compile(r"[\u4e00-\u9fff]")


# ---------------------------------------------------------------- 市场解析
class MarketResolver:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.by_id = {m["id"]: m for m in cfg["markets"]}
        self.by_name = {m["name"]: m for m in cfg["markets"]}
        # token 精确匹配：别名任意长度均可
        self.token_index: dict[str, str] = {}
        # 子串扫描：只放行中文别名(>=2字) 或 长度>=4 的英文别名，避免 "IT"/"IN"/"NO" 误命中
        self.scan_alias: list[tuple[str, str]] = []
        for m in cfg["markets"]:
            for al in m["aliases"]:
                self.token_index.setdefault(al.strip().lower(), m["id"])
                if len(al) >= 2 and CJK.search(al):
                    self.scan_alias.append((al, m["id"]))
                elif len(al) >= 4 and not CJK.search(al):
                    self.scan_alias.append((al.lower(), m["id"]))
        self.scan_alias.sort(key=lambda x: -len(x[0]))
        self.unknown_tokens: dict[str, int] = {}

    def from_token(self, tok: str):
        key = tok.strip().lower()
        return self.by_id.get(self.token_index.get(key, ""))

    def split_tokens(self, text: str) -> list[str]:
        parts = re.split(r"[/／、,，;；|]+", text)
        return [p.strip() for p in parts if p.strip()]

    def resolve(self, text: str, allow_scan: bool = True) -> list[str]:
        """返回 market id 列表（保持顺序去重）"""
        out: list[str] = []

        def add(mid):
            if mid and mid not in out:
                out.append(mid)

        for tok in self.split_tokens(text):
            m = self.from_token(tok)
            if m:
                add(m["id"])
        if allow_scan:
            low = text.lower()
            for alias, mid in self.scan_alias:
                if alias in low:
                    add(mid)
        return out

    def note_unknown(self, tok: str):
        tok = tok.strip()
        if tok:
            self.unknown_tokens[tok] = self.unknown_tokens.get(tok, 0) + 1


# ---------------------------------------------------------------- 工具
def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&amp;", "&").replace("&nbsp;", " ")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
                .replace("&#39;", "'").replace("\u3000", " "))
    return re.sub(r"\s+", " ", text).strip()


def strip_md_links(text: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def md_links(text: str) -> list[dict]:
    return [{"name": n.strip(), "url": u.strip()}
            for n, u in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)]


def html_links(cell_html: str) -> list[dict]:
    out = []
    for url, name in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', cell_html, re.S):
        out.append({"name": clean(name)[:60] or url[:60], "url": url})
    for url in re.findall(r'(https?://[^\s"\'<>]+)', clean(cell_html)):
        out.append({"name": url[:60], "url": url})
    return out


def freq_defaults(text: str, res: "MarketResolver", top: int = 3, min_count: int = 1) -> list[str]:
    """报告没有 🎯 目标市场行时，用全文国家词频兜底推断该报告覆盖的市场"""
    counts: dict[str, int] = {}
    for m in res.cfg["markets"]:
        if m["id"] in ("ZZ", "CN"):
            continue
        c = 0
        for al in m["aliases"]:
            if len(al) >= 2 and CJK.search(al):
                c += text.count(al)
        if c >= min_count:
            counts[m["id"]] = c
    ranked = sorted(counts.items(), key=lambda x: -x[1])[:top]
    return [k for k, _ in ranked]


def parse_severity(text: str) -> str:
    if "🔴" in text or "高" in text:
        return "high"
    if "🟡" in text or "中" in text:
        return "mid"
    if "🟢" in text or "低" in text:
        return "low"
    return "unknown"


def short_id(prefix: str, text: str) -> str:
    return prefix + "_" + hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


# ---------------------------------------------------------------- 新闻解析
NEWS_RE = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*\s*$")


def parse_news(path: Path, res: MarketResolver) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    items: list[dict] = []
    cur: dict | None = None
    section = ""

    def flush():
        nonlocal cur
        if cur and cur.get("title"):
            items.append(cur)
        cur = None

    for raw in text.splitlines():
        line = raw.rstrip()
        h = line.strip()
        if h.startswith("## "):
            flush()
            section = h[3:].strip()
            continue
        m = NEWS_RE.match(h)
        if m:
            flush()
            cur = {"no": int(m.group(1)), "title": strip_md_links(m.group(2)),
                   "section": section, "category": "", "summary": "", "links": []}
            continue
        if cur is None:
            continue
        if h.startswith("分类："):
            cur["category"] = strip_md_links(h[3:].strip())
        elif h.startswith("摘要："):
            cur["summary"] = strip_md_links(h[3:].strip())
        elif h.startswith("来源："):
            cur["links"] = md_links(h[3:])
        elif h and cur["summary"]:
            cur["summary"] += " " + strip_md_links(h)
    flush()

    out = []
    for it in items:
        markets = res.resolve(it["category"])
        markets += [m for m in res.resolve(it["title"]) if m not in markets]
        if not markets:
            markets = list(res.cfg.get("global_expand", []))
            derived = True
        else:
            derived = False
        out.append({
            "id": short_id("nw", it["title"]),
            "date": date_of_path(path),
            "type": "news",
            "line": "每日新闻",
            "title": it["title"],
            "category": it["category"],
            "summary": it["summary"],
            "severity": "unknown",
            "markets": markets,
            "global": derived,
            "links": it["links"],
            "source_file": path.name,
        })
    return out


def date_of_name(name: str) -> str:
    """文件名优先取日期，格式不对返回空串（由 date_of_path 继续兜底）"""
    m = re.fullmatch(r".*?(\d{4}-\d{2}-\d{2}).*", name)
    return m.group(1) if m else ""


def date_of_path(path: Path) -> str:
    """文件名 -> 正文首屏日期 -> 文件修改时间，三级兜底"""
    d = date_of_name(path.name)
    if d:
        return d
    head = path.read_text(encoding="utf-8", errors="ignore")[:400]
    m = re.search(r"(\d{4}-\d{2}-\d{2})", head)
    if m:
        return m.group(1)
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- 社媒吐槽解析
COL_PATTERNS = {
    "title": ["痛点类别", "二级痛点", "类别", "吐槽摘要", "吐槽标题", "信号", "归因类别"],
    "product": ["影响产品", "产品", "品类", "适用产品"],
    "market": ["目标国家", "目标市场", "国家", "市场", "地区"],
    "severity": ["严重度"],
    "evidence": ["吐槽原句摘要", "客户原话", "原文信号", "典型证据", "摘要", "历史关联条目", "含义", "依据"],
    "source": ["来源", "链接", "出处"],
}
SKIP_ROW_WORDS = ["今日无新增", "无新增", "无符合", "无可确认", "空", "—", "-", "无"]


def col_index(header: list[str]) -> dict[str, int]:
    idx: dict[str, int] = {}
    for i, cell in enumerate(header):
        for key, pats in COL_PATTERNS.items():
            if key in idx:
                continue
            for p in pats:
                if p in cell:
                    idx[key] = i
                    break
    return idx


def cell_plain(row_html: str) -> list[str]:
    tds = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)
    return [clean(td) for td in tds]


def parse_social(path: Path, res: MarketResolver) -> tuple[list[dict], list[str]]:
    html = path.read_text(encoding="utf-8")
    date = date_of_path(path)
    name = path.name
    line = re.split(r"社媒吐槽日报|社媒日报", name)[0].strip() or "社媒"

    # 报告头部的 🎯 目标市场，找不到就按全文国家词频兜底
    plain_all = clean(re.sub(r"<script.*?</script>", "", html, flags=re.S))
    default_ids: list[str] = []
    m = re.search(r"🎯\s*([^<\n|]+)", html)
    if m:
        default_ids = res.resolve(clean(m.group(1)))
    if not default_ids:
        m3 = re.search(r"三国[:：]\s*([^<\n|]{0,40})", plain_all)
        if m3:
            default_ids = res.resolve(m3.group(1))
    if not default_ids:
        default_ids = freq_defaults(plain_all, res)
    if not default_ids:
        default_ids = list(res.cfg.get("line_default_markets", {}).get(line, []))

    items: list[dict] = []
    warnings: list[str] = []
    for table in re.findall(r"<table.*?</table>", html, re.S):
        rows = re.findall(r"<tr.*?</tr>", table, re.S)
        if len(rows) < 2:
            continue
        hdr = cell_plain(rows[0])
        if not any(hdr):
            continue
        has_th = "<th" in rows[0].lower()
        idx = col_index(hdr)
        if not has_th and "market" not in idx:
            continue
        if "title" not in idx:
            continue
        body = rows[1:] if has_th else rows[1:]
        for r in body:
            cells = cell_plain(r)
            if len(cells) < 2:
                continue
            cells += [""] * (max(idx.values()) + 1 - len(cells)) if max(idx.values()) + 1 > len(cells) else []

            def get(key: str) -> str:
                i = idx.get(key)
                return cells[i] if i is not None and i < len(cells) else ""

            title = get("title").strip("# ").strip()
            if not title or len(title) < 3:
                continue
            if any(w in title for w in SKIP_ROW_WORDS) and len(title) < 12:
                continue
            raw_market = get("market")
            markets = res.resolve(raw_market) if raw_market else []
            if not markets:
                # 国家列缺失时，从标题/证据/产品里找国家线索
                guess = " ".join([title, get("evidence"), get("product")])
                markets = res.resolve(guess)
            if not markets:
                markets = list(default_ids)
                if not markets:
                    warnings.append(f"{name}：行「{title[:20]}」未识别国家或缺少默认市场，已跳过")
                    continue
            products = get("product")
            ev = get("evidence")
            links = html_links(r)
            items.append({
                "id": short_id("pp", f"{line}|{title}"),
                "date": date,
                "type": "pain",
                "line": line,
                "title": title,
                "category": line,
                "summary": ev,
                "product": products,
                "severity": parse_severity(get("severity")),
                "markets": markets,
                "global": False,
                "links": links[:4],
                "source_file": name,
            })
    return items, warnings


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--news", default=str(DEFAULT_NEWS))
    ap.add_argument("--social", default=str(DEFAULT_SOCIAL))
    ap.add_argument("--out", default=str(DATA / "dataset.js"),
                    help="输出路径，默认 data/dataset.js")
    args = ap.parse_args()

    cfg = json.loads((CONTENT / "markets.json").read_text(encoding="utf-8"))
    res = MarketResolver(cfg)

    news_dir, social_dir = Path(args.news), Path(args.social)
    errors: list[str] = []

    news_items: list[dict] = []
    if news_dir.is_dir():
        for p in sorted(news_dir.glob("*.md")):
            news_items.extend(parse_news(p, res))
    else:
        errors.append(f"找不到新闻目录：{news_dir}")

    social_items: list[dict] = []
    if social_dir.is_dir():
        for p in sorted(social_dir.glob("*.html")):
            got, warns = parse_social(p, res)
            social_items.extend(got)
            errors.extend(warns)
    else:
        errors.append(f"找不到社媒目录：{social_dir}")

    # 去重：标题 + 摘要指纹（新闻两个同名文件 -> 合并日期）
    merged: dict[str, dict] = {}
    for it in news_items + social_items:
        fp = hashlib.md5(f"{it['type']}|{it['line']}|{it['title']}|{it['summary']}".encode()).hexdigest()
        if fp in merged:
            tgt = merged[fp]
            if it["date"] not in tgt["dates"]:
                tgt["dates"].append(it["date"])
            for nk in it["markets"]:
                if nk not in tgt["markets"]:
                    tgt["markets"].append(nk)
            continue
        it["dates"] = [it["date"]]
        it["fp"] = fp
        merged[fp] = it

    items = list(merged.values())
    for it in items:
        it["dates"].sort()
        # 「全球」不是一个坐标点：落到核心市场，并打 global 标记做视觉区分
        if "ZZ" in it["markets"]:
            it["markets"] = [m for m in it["markets"] if m != "ZZ"]
            for gid in res.cfg.get("global_expand", []):
                if gid not in it["markets"]:
                    it["markets"].append(gid)
            it["global"] = True

    # 校验
    for it in items:
        if not it["markets"]:
            errors.append(f"条目无市场归属：{it['title'][:30]}")
        for mid in it["markets"]:
            if mid not in res.by_id:
                errors.append(f"未知市场 id {mid}：{it['title'][:30]}")

    if any(e.startswith("条目无市场归属") or e.startswith("未知市场") for e in errors):
        for e in errors:
            print("[FATAL]", e)
        return 1

    dates = sorted({d for it in items for d in it["dates"]})
    used_ids = sorted({m for it in items for m in it["markets"]})
    markets_out = []
    for mid in used_ids:
        mk = res.by_id[mid]
        markets_out.append({"id": mk["id"], "name": mk["name"], "en": mk["en"],
                            "lat": mk["lat"], "lon": mk["lon"], "region": mk["region"]})

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta": cfg["meta"],
        "core_markets": cfg["core_markets"],
        "global_expand": cfg["global_expand"],
        "product_lines": {k: v for k, v in cfg["product_lines"].items()},
        "sources": {"news": "每日新闻 (*.md)", "social": "每日社媒 (*.html)"},
        "dates": dates,
        "markets": markets_out,
        "items": items,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.NRI_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")

    news_n = sum(1 for i in items if i["type"] == "news")
    pain_n = sum(1 for i in items if i["type"] == "pain")
    print(f"✔ 写入 {out}  ({out.stat().st_size/1024:.1f} KB)")
    print(f"  条目 {len(items)}（新闻 {news_n} / 痛点 {pain_n}） | 日期 {len(dates)} 天 {dates[0] if dates else ''}~{dates[-1] if dates else ''} | 市场 {len(markets_out)} 个")
    for w in dict.fromkeys(errors):
        print("  提示：", w)
    if res.unknown_tokens:
        top = sorted(res.unknown_tokens.items(), key=lambda x: -x[1])[:12]
        print("  未能识别的 token：", "、".join(f"{t}({c})" for t, c in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
