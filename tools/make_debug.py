#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成无头浏览器验证用的调试页（在 index.html 基础上注入诊断与自动化动作）。

    python tools/make_debug.py select:JP   ->  _debug.html（4 秒后自动选中日本并飞行）
    python tools/make_debug.py today       ->  _debug.html（4 秒后切到"只看今天"）
    python tools/make_debug.py none        ->  _debug.html（仅诊断，无动作）
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / "index.html").read_text(encoding="utf-8")

action = sys.argv[1] if len(sys.argv) > 1 else "none"
if action.startswith("select:"):
    act = "window.NRI_DEBUG.select(%r, true);" % action.split(":", 1)[1]
elif action == "today":
    act = "window.NRI_DEBUG.state.mode='today'; window.NRI_DEBUG.refresh();"
else:
    act = ""

inject = """<script>
window.__errs=[];
window.addEventListener('error',function(e){window.__errs.push((e.message||'err')+' @'+(e.filename||'')+':'+(e.lineno||''));});
var __diag=document.createElement('pre');
__diag.style.cssText='position:fixed;left:50%;top:6px;transform:translateX(-50%);z-index:999;background:rgba(0,0,0,.85);color:#4f6;padding:8px 12px;font-size:12px;border:1px solid #4f6;max-width:82vw;white-space:pre-wrap';
document.addEventListener('DOMContentLoaded',function(){document.body.appendChild(__diag);});
var __n=0;
(function tick(){
  __n++;
  var st=document.getElementById('stats');
  var det=document.getElementById('detail');
  __diag.textContent='ERRS: '+JSON.stringify(window.__errs)+
    '\\nSTATS: '+(st?st.innerText.replace(/\\n/g,' | '):'(no stats)')+
    '\\nDETAIL: '+(det?det.innerText.slice(0,120).replace(/\\n/g,' | '):'(no detail)');
  if(__n===24){""" + act + """}
  setTimeout(tick,250);
})();
</script>
"""

out = src.replace('<script src="lib/three.min.js"></script>', inject + '<script src="lib/three.min.js"></script>', 1)
(ROOT / "_debug.html").write_text(out, encoding="utf-8")
print("生成 _debug.html（动作: %s）" % action)
