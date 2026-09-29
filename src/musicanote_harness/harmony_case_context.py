"""On-demand score context page for a retrieved harmony case."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


VERSION = "harmony-case-context-0.1.0"


def write_harmony_case_context_html(
    case: dict[str, Any], ir: dict[str, Any], pages: list[str], destination: str | Path,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sound_by_id = {row["sounding_event_id"]: row for row in ir.get("sounding_events", [])}
    note_ids = sorted({note_id for sound_id in case["feature"]["current"]["sounding_event_ids"]
                       for note_id in sound_by_id.get(sound_id, {}).get("source_note_ids", [])})
    payload = json.dumps({"case": case, "note_ids": note_ids}, ensure_ascii=False).replace("</", "<\\/")
    engraved = "".join(f'<section class="page">{page}</section>' for page in pages)
    label = html.escape(case["label"]["raw"])
    page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} · Retrieved Harmony Case</title><style>
body{{margin:0;background:#eef1f5;color:#17202a;font:14px/1.45 system-ui,sans-serif}}header{{position:sticky;top:0;z-index:10;background:#101820;color:white;padding:12px 18px}}.notice{{margin-top:6px;color:#fde68a;font-size:12px}}main{{max-width:1200px;margin:auto;padding:16px}}.meta{{background:white;border:1px solid #d8dee8;border-radius:9px;padding:12px;margin-bottom:12px}}.page{{background:#fffef8;margin-bottom:16px;padding:12px;box-shadow:0 2px 8px #0002}}.page svg{{display:block;width:100%;height:auto}}g.note.case-span .notehead{{fill:#7c3aed!important;color:#7c3aed!important;stroke:#4c1d95!important;stroke-width:10px!important}}code{{font-size:11px}}
</style></head><body><header><strong>검색된 화성 사례 · {label}</strong><div class="notice">이 라벨은 다른 작품의 원자료 주석이며 현재 악보의 정답이 아닙니다.</div></header><main><div class="meta" id="meta"></div>{engraved}</main>
<script id="payload" type="application/json">{payload}</script><script>
const D=JSON.parse(document.getElementById('payload').textContent),c=D.case,f=c.feature,span=f.span,esc=s=>String(s??'').replace(/[&<>"']/g,x=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[x]));
document.getElementById('meta').innerHTML=`<strong>${{esc(c.label.raw)}}</strong> · ${{esc(c.label.taxonomy?.family||'unresolved')}}<br>구간 ${{span.start.numerator}}/${{span.start.denominator}}–${{span.end.numerator}}/${{span.end.denominator}} quarter [start,end)<br><span>출처: <code>${{esc(c.provenance.source_locator.path)}}:${{c.provenance.source_locator.line}}</code></span><br><small>보라색은 검색 사례 구간입니다. 모든 음이 화음 구성음이라는 뜻은 아닙니다.</small>`;
let first=null;for(const id of D.note_ids){{const g=document.querySelector(`g.note[data-id="${{id}}"]`);if(g){{g.classList.add('case-span');first??=g}}}}if(first)setTimeout(()=>first.scrollIntoView({{block:'center'}}),60);
</script></body></html>'''
    destination.write_text(page, encoding="utf-8")
    return destination
