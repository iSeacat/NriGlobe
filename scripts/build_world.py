#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 TopoJSON(countries-110m) 解码成极简 GeoJSON 环数据，供地球贴图矢量化绘制。

用法：
    python scripts/build_world.py <输入的 countries-110m.json> [输出 js 路径]

产物：data/world.js  ->  window.WORLD_LAND = {countries:[{name, rings:[[[lon,lat],...],...]}]}
"""
import json
import sys
from pathlib import Path


def decode_arcs(topology):
    """TopoJSON 增量编码 -> 绝对坐标列表"""
    transform = topology.get("transform")
    arcs = topology["arcs"]
    out = []
    if transform:
        sx, sy = transform["scale"]
        tx, ty = transform["translate"]
        for arc in arcs:
            x = y = 0
            pts = []
            for dx, dy in arc:
                x += dx
                y += dy
                pts.append([round(x * sx + tx, 3), round(y * sy + ty, 3)])
            out.append(pts)
    else:
        out = [[[round(p[0], 3), round(p[1], 3)] for p in arc] for arc in arcs]
    return out


def ring_from_arc(idxs, arcs):
    """拼接 arc 索引 -> 一个闭合坐标环。负索引表示反向（~i）。"""
    pts = []
    for i in idxs:
        if i >= 0:
            seg = arcs[i]
        else:
            seg = arcs[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def simplify(ring, keep=2):
    """按精度去重化简，保证首尾闭合"""
    seen = set()
    out = []
    for lon, lat in ring:
        key = (round(lon, keep), round(lat, keep))
        if key in seen:
            continue
        seen.add(key)
        out.append([round(lon, keep), round(lat, keep)])
    if len(out) > 2 and out[0] != out[-1]:
        out.append(out[0])
    return out


def bbox_span(ring):
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return max(lons) - min(lons), max(lats) - min(lats)


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "countries-110m.json")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "data/world.js")
    topo = json.loads(src.read_text(encoding="utf-8"))
    arcs = decode_arcs(topo)

    countries = []
    for geom in topo["objects"]["countries"]["geometries"]:
        name = (geom.get("properties") or {}).get("name", "")
        polys = []
        if geom["type"] == "Polygon":
            polys = [geom["arcs"]]
        elif geom["type"] == "MultiPolygon":
            polys = geom["arcs"]
        else:
            continue

        rings = []
        for poly in polys:
            for ring_idx in poly:
                raw = ring_from_arc(ring_idx, arcs)
                simp = simplify(raw)
                if len(simp) < 4:
                    continue
                w, h = bbox_span(simp)
                # 丢掉过小的碎岛，控制文件体积
                if max(w, h) < 0.7:
                    continue
                rings.append(simp)
        if rings:
            countries.append({"name": name, "rings": rings})

    dst.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"countries": countries}, ensure_ascii=False, separators=(",", ":"))
    dst.write_text("window.WORLD_LAND = " + payload + ";\n", encoding="utf-8")
    total_rings = sum(len(c["rings"]) for c in countries)
    print(f"写入 {dst}  | 国家/地区 {len(countries)} 个 | 环 {total_rings} 个 | {len(payload)/1024:.1f} KB")


if __name__ == "__main__":
    main()
