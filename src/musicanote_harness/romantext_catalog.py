"""Searchable, lazy visual-review catalog for audited RomanText/score pairs."""

from __future__ import annotations

import json
import mimetypes
import re
import threading
from dataclasses import dataclass
from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .engraving import render_musicxml_pages
from .harmony_overlay_artifact import VERSION as OVERLAY_VERSION
from .romantext_import import prepare_romantext, write_romantext_package
from .romantext_context_evidence import VERSION as CONTEXT_EVIDENCE_VERSION
from .romantext_evidence import VERSION as EVIDENCE_VERSION
from .romantext_review import REVIEW_VERSION, write_romantext_review_html
from .romantext_review_store import append_review, load_latest
from .harmony_case_retrieval import load_case_records, load_prepared_package, retrieve_cases
from .harmony_case_review_store import append_case_review, load_latest as load_latest_case_reviews
from .harmony_case_context import VERSION as CASE_CONTEXT_VERSION, write_harmony_case_context_html
from .harmony_dataset_manifest import load_manifest_index


def _pretty(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip()


def _normalize(value: str) -> str:
    return re.sub(r"[^\w]+", " ", value.replace("_", " ").casefold()).strip()


def _display_parts(path: Path, corpus: str) -> tuple[str, str]:
    folders = list(path.parent.parts)
    marker = "scores" if corpus == "openscore-lieder" else "Corpus"
    try:
        tail = folders[folders.index(marker) + 1 :]
    except ValueError:
        tail = folders[-4:]
    if corpus == "openscore-lieder" and len(tail) >= 2:
        return _pretty(tail[0]), " / ".join(_pretty(value) for value in tail[1:])
    if corpus == "when-in-rome" and len(tail) >= 3:
        return _pretty(tail[1]), " / ".join(_pretty(value) for value in tail[2:])
    return "", " / ".join(_pretty(value) for value in tail) or _pretty(path.stem)


def load_evidence_records(records_path: str | Path | None) -> dict[str, dict[str, Any]]:
    if records_path is None:
        return {}
    path = Path(records_path)
    if not path.is_file():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        analysis_sha256 = row.get("analysis_sha256")
        if analysis_sha256:
            records[str(analysis_sha256)] = row
    return records


def load_catalog(
    records_path: str | Path, evidence_records_path: str | Path | None = None
) -> list[dict[str, Any]]:
    records_path = Path(records_path)
    evidence_by_analysis = load_evidence_records(evidence_records_path)
    entries: list[dict[str, Any]] = []
    for row_number, line in enumerate(records_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        analysis_path = Path(row["analysis_path"])
        corpus = row.get("corpus") or "unknown"
        composer, title = _display_parts(analysis_path, corpus)
        exact = int(row.get("status_counts", {}).get("exact_coordinate", 0))
        ambiguous = int(row.get("status_counts", {}).get("ambiguous", 0))
        identity = sha256(
            f'{row.get("analysis_sha256", analysis_path)}|{row.get("score_sha256", row.get("score_path"))}'.encode()
        ).hexdigest()[:16]
        evidence_row = evidence_by_analysis.get(str(row.get("analysis_sha256")), {})
        support_counts = evidence_row.get("support_band_counts", {})
        support_key = {
            "strong": "strong_support",
            "moderate": "moderate_support",
            "mixed": "mixed_evidence",
            "weak": "weak_evidence",
            "unscorable": "unscorable",
        }
        entries.append(
            {
                "id": identity,
                "row_number": row_number,
                "corpus": corpus,
                "composer": composer,
                "title": title,
                "status": row.get("status", "unknown"),
                "exact": exact,
                "ambiguous": ambiguous,
                "events": int(row.get("roman_events", exact + ambiguous)),
                "measures": row.get("score_measures"),
                "analyst": row.get("analyst"),
                "automatic": bool(row.get("automatic_filename")),
                "analysis_path": str(analysis_path),
                "score_path": row.get("score_path"),
                "analysis_sha256": row.get("analysis_sha256"),
                "score_sha256": row.get("score_sha256"),
                "evidence_status": evidence_row.get("status", "not_audited"),
                "support_band_counts": {
                    band: int(support_counts.get(band, support_counts.get(support_key[band], 0)))
                    for band in ("strong", "moderate", "mixed", "weak", "unscorable")
                },
                "review_candidate_count": int(evidence_row.get("review_candidate_count", 0)),
                "search": _normalize(" ".join(
                    str(value) for value in (corpus, composer, title, row.get("analyst"), analysis_path) if value
                )),
            }
        )
    return entries


def search_catalog(
    entries: list[dict[str, Any]], query: str = "", corpus: str = "all", status: str = "all",
    evidence: str = "all", limit: int = 100
) -> list[dict[str, Any]]:
    needle = _normalize(query)
    result = []
    for entry in entries:
        if corpus != "all" and entry["corpus"] != corpus:
            continue
        if status != "all" and entry["status"] != status:
            continue
        bands = entry.get("support_band_counts", {})
        mixed = int(bands.get("mixed", 0))
        weak = int(bands.get("weak", 0))
        if evidence == "weak" and not weak:
            continue
        if evidence == "mixed_or_weak" and not (mixed or weak):
            continue
        if evidence == "strong_only" and (mixed or weak or entry.get("evidence_status") == "not_audited"):
            continue
        if needle and needle not in entry["search"]:
            continue
        result.append({key: value for key, value in entry.items() if key != "search"})
    result.sort(key=lambda item: (item["corpus"], item["composer"].casefold(), item["title"].casefold()))
    return result[: max(1, min(limit, 500))]


CATALOG_HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MUSICANOTE Harmony Source Catalog</title><style>
:root{--ink:#17202a;--muted:#64748b;--blue:#2563eb;--bg:#eef2f6}*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:18px 24px;background:#101820;color:white}header h1{font-size:20px;margin:0 0 4px}.wrap{max-width:1200px;margin:auto;padding:20px}.controls{display:grid;grid-template-columns:1fr 180px 180px 180px;gap:8px;margin-bottom:12px}input,select,button{font:inherit;padding:9px;border:1px solid #cbd5e1;border-radius:7px;background:white}.summary{color:var(--muted);margin:8px 0}.grid{display:grid;gap:9px}.row{background:white;border:1px solid #dce3eb;border-radius:9px;padding:12px;display:grid;grid-template-columns:1fr auto;gap:12px}.title{font-weight:700}.meta{font-size:12px;color:var(--muted)}.counts{font-size:12px;margin-top:5px}.evidence{font-size:12px;margin-top:4px;color:#334155}.open{align-self:center;background:var(--blue);color:white;border:0;cursor:pointer;min-width:120px}.open:disabled{background:#94a3b8}.notice{padding:10px;border-radius:8px;background:#fff7d6;color:#713f12;margin-bottom:12px}@media(max-width:820px){.controls{grid-template-columns:1fr}.row{grid-template-columns:1fr}}
</style></head><body><header><h1>MUSICANOTE · Harmony Source Catalog</h1><div>곡을 검색한 뒤 필요할 때만 Canonical IR과 악보 검토 화면을 생성합니다.</div></header><div class="wrap"><div class="notice">표시된 화성은 원자료 주석입니다. 증거 등급은 악보 표면과의 호환성이지 정답·오류 판정이나 human gold가 아닙니다.</div><div class="controls"><input id="q" placeholder="작곡가·작품·경로 검색"><select id="corpus"><option value="all">모든 코퍼스</option><option value="openscore-lieder">OpenScore Lieder</option><option value="when-in-rome">When in Rome</option></select><select id="status"><option value="all">모든 정렬 상태</option><option value="aligned_complete">완전 정렬</option><option value="aligned_partial">부분 정렬</option><option value="parse_or_alignment_error">오류</option></select><select id="evidence"><option value="all">모든 증거 분포</option><option value="weak">weak 포함</option><option value="mixed_or_weak">mixed/weak 포함</option><option value="strong_only">mixed/weak 없음</option></select></div><div id="summary" class="summary"></div><div id="list" class="grid"></div></div><script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let timer;
async function load(){const q=document.getElementById('q').value,c=document.getElementById('corpus').value,s=document.getElementById('status').value,e=document.getElementById('evidence').value;const r=await fetch(`/api/records?q=${encodeURIComponent(q)}&corpus=${encodeURIComponent(c)}&status=${encodeURIComponent(s)}&evidence=${encodeURIComponent(e)}&limit=100`),d=await r.json();document.getElementById('summary').textContent=`전체 ${d.total.toLocaleString()}곡 · 현재 ${d.records.length}곡 표시 (최대 100)`;const list=document.getElementById('list');list.innerHTML=d.records.map(x=>{const b=x.support_band_counts||{},evidence=x.evidence_status==='not_audited'?'증거 전수 검사 없음':`strong ${b.strong||0} · moderate ${b.moderate||0} · mixed ${b.mixed||0} · weak ${b.weak||0} · unscorable ${b.unscorable||0}`;return `<article class="row"><div><div class="title">${esc(x.composer)} · ${esc(x.title)}</div><div class="meta">${esc(x.corpus)} · ${esc(x.status)} · ${x.measures??'?'} measures</div><div class="counts">exact ${x.exact.toLocaleString()} · ambiguous ${x.ambiguous.toLocaleString()} · ${esc(x.analyst||'analyst unknown')}</div><div class="evidence">${evidence}</div></div><button class="open" data-id="${x.id}" ${x.exact?``:`disabled`}>악보로 보기</button></article>`}).join('')||'<div>검색 결과가 없습니다.</div>';list.querySelectorAll('.open').forEach(b=>b.onclick=()=>prepare(b))}
async function prepare(button){const original=button.textContent;button.disabled=true;button.textContent='생성 중…';try{const r=await fetch('/api/prepare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:button.dataset.id})}),d=await r.json();if(!r.ok)throw new Error(d.error||'생성 실패');window.open(d.url,'_blank')}catch(e){alert(e.message)}finally{button.disabled=false;button.textContent=original}}
for(const id of ['q','corpus','status','evidence'])document.getElementById(id).addEventListener(id==='q'?'input':'change',()=>{clearTimeout(timer);timer=setTimeout(load,180)});load();
</script></body></html>'''


@dataclass
class CatalogApplication:
    records_path: Path
    output: Path
    evidence_records_path: Path | None = None
    case_library_path: Path | None = None
    dataset_manifest_path: Path | None = None
    case_review_path: Path | None = None

    def __post_init__(self) -> None:
        self.entries = load_catalog(self.records_path, self.evidence_records_path)
        self.by_id = {entry["id"]: entry for entry in self.entries}
        self.by_score_sha256: dict[str, list[dict[str, Any]]] = {}
        for entry in self.entries:
            score_sha256 = entry.get("score_sha256")
            if score_sha256:
                self.by_score_sha256.setdefault(str(score_sha256), []).append(entry)
        self.output.mkdir(parents=True, exist_ok=True)
        self.review_lock = threading.Lock()
        self.prepare_lock = threading.Lock()
        self.case_lock = threading.Lock()
        all_cases = load_case_records(self.case_library_path) if self.case_library_path and self.case_library_path.is_file() else []
        self.harmony_cases_by_id = {case["case_id"]: case for case in all_cases
                                    if case.get("dataset_identity", {}).get("split") == "train"}
        self.harmony_case_list = list(self.harmony_cases_by_id.values())
        self.manifest_by_ir = load_manifest_index(self.dataset_manifest_path) if self.dataset_manifest_path and self.dataset_manifest_path.is_file() else {}
        self.case_review_path = self.case_review_path or (self.output / "harmony_case_reviews.jsonl")

    def reviews(self, identity: str) -> dict[str, dict[str, Any]]:
        if identity not in self.by_id:
            raise KeyError("Unknown catalog record")
        return load_latest(self.output / identity / "reviewer_annotations.jsonl")

    def save_review(self, identity: str, request: dict[str, Any]) -> dict[str, Any]:
        if identity not in self.by_id:
            raise KeyError("Unknown catalog record")
        destination = self.output / identity
        annotations_path = destination / "imported_annotations.jsonl"
        if not annotations_path.is_file():
            raise ValueError("Prepare the score review before saving reviewer annotations")
        annotation_ids = {
            json.loads(line).get("annotation_id")
            for line in annotations_path.read_text(encoding="utf-8").splitlines() if line.strip()
        }
        annotation_id = str(request.get("annotation_id", ""))
        if annotation_id not in annotation_ids:
            raise ValueError("Annotation does not belong to this score review")
        with self.review_lock:
            return append_review(
                destination / "reviewer_annotations.jsonl",
                score_review_id=identity,
                annotation_id=annotation_id,
                reason=str(request.get("reason", "")),
                note=str(request.get("note", ""))[:2000],
            )

    def retrieve_harmony_cases(self, identity: str, annotation_id: str, limit: int = 6) -> dict[str, Any]:
        if not self.harmony_case_list:
            raise ValueError("Harmony case library is not configured")
        self.prepare(identity)
        package = load_prepared_package(self.output / identity)
        annotation = next((row for row in package["annotations"] if row["annotation_id"] == annotation_id), None)
        alignment = next((row for row in package["alignments"] if row["annotation_id"] == annotation_id), None)
        if not annotation or not annotation.get("target") or not alignment or alignment.get("mapping_status") != "exact":
            raise ValueError("Only an exact score-linked harmony span can be queried")
        result = retrieve_cases(
            package["ir"], annotation["target"]["span"], self.harmony_case_list,
            limit=max(1, min(int(limit), 12)), per_score_limit=1,
            query_dataset_identity={"split": "holdout"},
        )
        latest = load_latest_case_reviews(self.case_review_path)
        result["reviews"] = {
            match["case_id"]: latest.get(f'{result["query"]["query_id"]}|{match["case_id"]}')
            for match in result["matches"]
            if latest.get(f'{result["query"]["query_id"]}|{match["case_id"]}')
        }
        result["ui_policy"] = {
            "candidate_split": "train",
            "structure_influence": "none",
            "feedback_changes_ranking_immediately": False,
        }
        return result

    def save_harmony_case_review(self, identity: str, request: dict[str, Any]) -> dict[str, Any]:
        annotation_id = str(request.get("annotation_id", ""))
        result = self.retrieve_harmony_cases(identity, annotation_id, 12)
        query_id = str(request.get("query_id", ""))
        case_id = str(request.get("case_id", ""))
        if query_id != result["query"]["query_id"] or case_id not in {row["case_id"] for row in result["matches"]}:
            raise ValueError("Case review does not match this score query")
        with self.case_lock:
            return append_case_review(
                self.case_review_path,
                query_id=query_id, case_id=case_id, engine_version=result["engine_version"],
                verdict=str(request.get("verdict", "")),
                axis_ratings=request.get("axis_ratings") or {}, note=str(request.get("note", ""))[:2000],
            )

    def prepare_harmony_case_context(self, case_id: str) -> dict[str, Any]:
        case = self.harmony_cases_by_id.get(case_id)
        if not case:
            raise KeyError("Unknown or non-train harmony case")
        entry = self.manifest_by_ir.get(case["ir_document_id"])
        if not entry:
            raise ValueError("Dataset manifest is required to render the source case")
        destination = self.output / "case-context" / case_id
        page_path = destination / "index.html"
        meta_path = destination / "context_meta.json"
        expected = {"case_id": case_id, "feature_version": case["feature"]["feature_version"],
                    "score_sha256": case["provenance"]["score_sha256"], "context_version": CASE_CONTEXT_VERSION}
        if page_path.is_file() and meta_path.is_file() and json.loads(meta_path.read_text(encoding="utf-8")) == expected:
            return {"url": f"/reviews/case-context/{case_id}/index.html", "cached": True}
        package = load_prepared_package(entry["package_path"])
        pages, _mapping = render_musicxml_pages(entry["score_source_path"], package["ir"])
        write_harmony_case_context_html(case, package["ir"], pages, page_path)
        meta_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"url": f"/reviews/case-context/{case_id}/index.html", "cached": False}

    def prepare(self, identity: str) -> dict[str, Any]:
        entry = self.by_id.get(identity)
        if not entry:
            raise KeyError("Unknown catalog record")
        if not entry["exact"] or not entry.get("score_path"):
            raise ValueError("This record has no exact score coordinates to review")
        destination = self.output / identity
        review_path = destination / "romantext-review.html"
        report_path = destination / "preparation_report.json"
        if review_path.is_file() and report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            hashes = report.get("source_sha256", {})
            if (hashes.get("analysis") == entry.get("analysis_sha256")
                    and hashes.get("score") == entry.get("score_sha256")
                    and report.get("evidence_version") == EVIDENCE_VERSION
                    and report.get("context_evidence_version") == CONTEXT_EVIDENCE_VERSION
                    and report.get("overlay_artifact_version") == OVERLAY_VERSION
                    and report.get("review_version") == REVIEW_VERSION):
                return {"url": f"/reviews/{identity}/romantext-review.html", "cached": True, "report": report}
        with self.prepare_lock:
            package = prepare_romantext(entry["analysis_path"], entry["score_path"])
            package["report"]["review_version"] = REVIEW_VERSION
            write_romantext_package(package, destination)
            pages, mapping = render_musicxml_pages(entry["score_path"], package["ir"])
            (destination / "engraving_id_mapping_report.json").write_text(
                json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            write_romantext_review_html(package, pages, review_path)
        return {"url": f"/reviews/{identity}/romantext-review.html", "cached": False, "report": package["report"]}

    def overlay_by_score_sha256(self, score_sha256: str) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", score_sha256):
            raise ValueError("score_sha256 must be 64 lowercase hexadecimal characters")
        matches = self.by_score_sha256.get(score_sha256, [])
        if not matches:
            raise KeyError("No audited harmony source matches this score hash")
        if len(matches) > 1:
            return {
                "match_status": "multiple",
                "score_sha256": score_sha256,
                "candidates": [
                    {
                        "id": entry["id"],
                        "corpus": entry["corpus"],
                        "composer": entry["composer"],
                        "title": entry["title"],
                        "analyst": entry.get("analyst"),
                        "analysis_sha256": entry.get("analysis_sha256"),
                    }
                    for entry in matches
                ],
            }
        entry = matches[0]
        prepared = self.prepare(entry["id"])
        artifact_path = self.output / entry["id"] / "harmony_overlay_artifact.json"
        return {
            "match_status": "unique",
            "score_sha256": score_sha256,
            "catalog_record": {
                "id": entry["id"],
                "corpus": entry["corpus"],
                "composer": entry["composer"],
                "title": entry["title"],
                "analyst": entry.get("analyst"),
            },
            "cached": prepared["cached"],
            "overlay": json.loads(artifact_path.read_text(encoding="utf-8")),
        }


def _handler(application: CatalogApplication) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                data = CATALOG_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if parsed.path == "/api/records":
                query = parse_qs(parsed.query)
                records = search_catalog(
                    application.entries,
                    query.get("q", [""])[0],
                    query.get("corpus", ["all"])[0],
                    query.get("status", ["all"])[0],
                    query.get("evidence", ["all"])[0],
                    int(query.get("limit", ["100"])[0]),
                )
                self._json({"total": len(application.entries), "records": records})
                return
            review_match = re.fullmatch(r"/api/reviews/([0-9a-f]{16})", parsed.path)
            if review_match:
                try:
                    self._json({"reviews": application.reviews(review_match.group(1))})
                except KeyError as exc:
                    self._json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            case_match = re.fullmatch(r"/api/harmony-cases/([0-9a-f]{16})", parsed.path)
            if case_match:
                query = parse_qs(parsed.query)
                try:
                    self._json(application.retrieve_harmony_cases(
                        case_match.group(1), query.get("annotation_id", [""])[0],
                        int(query.get("limit", ["6"])[0]),
                    ))
                except (KeyError, ValueError) as exc:
                    self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            overlay_match = re.fullmatch(r"/api/overlay/by-score-sha256/([0-9a-f]{64})", parsed.path)
            if overlay_match:
                try:
                    payload = application.overlay_by_score_sha256(overlay_match.group(1))
                    status = HTTPStatus.CONFLICT if payload["match_status"] == "multiple" else HTTPStatus.OK
                    self._json(payload, status)
                except KeyError as exc:
                    self._json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                except ValueError as exc:
                    self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            prefix = "/reviews/"
            if parsed.path.startswith(prefix):
                relative = parsed.path[len(prefix) :]
                candidate = (application.output / relative).resolve()
                root = application.output.resolve()
                if root not in candidate.parents or not candidate.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                data = candidate.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed_path = urlparse(self.path).path
            review_match = re.fullmatch(r"/api/reviews/([0-9a-f]{16})", parsed_path)
            case_review_match = re.fullmatch(r"/api/harmony-case-reviews/([0-9a-f]{16})", parsed_path)
            if parsed_path not in {"/api/prepare", "/api/harmony-case-context"} and not review_match and not case_review_match:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length) or b"{}")
                if review_match:
                    self._json(application.save_review(review_match.group(1), request))
                elif case_review_match:
                    self._json(application.save_harmony_case_review(case_review_match.group(1), request))
                elif parsed_path == "/api/harmony-case-context":
                    self._json(application.prepare_harmony_case_context(str(request.get("case_id", ""))))
                else:
                    self._json(application.prepare(str(request.get("id", ""))))
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # keep one bad corpus item from stopping the catalog
                self._json({"error": f"Preparation failed: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def serve_catalog(
    records_path: str | Path, output: str | Path, host: str = "127.0.0.1", port: int = 8766,
    evidence_records_path: str | Path | None = None,
    case_library_path: str | Path | None = None,
    dataset_manifest_path: str | Path | None = None,
    case_review_path: str | Path | None = None,
) -> None:
    application = CatalogApplication(
        Path(records_path), Path(output), Path(evidence_records_path) if evidence_records_path else None,
        Path(case_library_path) if case_library_path else None,
        Path(dataset_manifest_path) if dataset_manifest_path else None,
        Path(case_review_path) if case_review_path else None,
    )
    server = ThreadingHTTPServer((host, port), _handler(application))
    print(json.dumps({"url": f"http://{host}:{port}/", "records": len(application.entries)}, ensure_ascii=False))
    server.serve_forever()
