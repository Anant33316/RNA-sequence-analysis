"""
REST API + static frontend.

Built on Starlette (the ASGI toolkit FastAPI itself is built on) with
Pydantic v2 request models and uvicorn as the server. Every endpoint:

  1. validates the JSON body with a Pydantic model     -> 422 on failure
  2. calls the engine in a worker thread (CPU work must not block the loop)
  3. maps EngineError to 400 / 404 / 413 with a consistent error body:

       {"error": {"code": "...", "message": "...", "field": "...", "details": [...]}}

Unexpected exceptions return 500 with a generic message and are logged;
they are never turned into a fake success.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, ValidationError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from engine import advanced, conversions, equivalence, examples, minimize, rna, simulate
from engine.errors import EngineError

from . import history
from .schemas import (AutomatonOnly, BoundedRequest, CompareRequest, FoldRequest, HairpinRequest,
                      MotifCompileRequest, OrfTraceRequest,
                      PairRequest, RnaAnalyzeRequest, RunRequest, SubsetRequest)

log = logging.getLogger("rna_toc.api")

VERSION = "2.0.0"
MAX_BODY_BYTES = 3 * 1024 * 1024
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
UPLOAD_EXTENSIONS = {".fa", ".fasta", ".fna", ".ffn", ".frn", ".txt", ".seq", ".rna"}
STARTED = time.time()

STATUS_FOR_CODE = {"not_found": 404, "too_large": 413}


# ----------------------------------------------------------------- helpers

def error_response(status: int, code: str, message: str, field: str | None = None, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "field": field}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status)


async def read_json(request: Request):
    ctype = request.headers.get("content-type", "")
    if "application/json" not in ctype:
        raise HTTPException(415, "Content-Type must be application/json")
    raw = await request.body()
    try:
        return json.loads(raw or b"null")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EngineError(f"request body is not valid JSON: {exc}", None, code="invalid_json") from exc


def endpoint(model: type[BaseModel], handler, history_kind: str | None = None, summarize=None):
    """Build a POST endpoint: JSON -> model -> handler (threadpool) -> JSON."""
    async def _endpoint(request: Request):
        body = await read_json(request)
        req = model.model_validate(body)
        result = await run_in_threadpool(handler, req)
        if history_kind and getattr(req, "save", False) and summarize:
            title, summary = summarize(req, result)
            entry_id = await run_in_threadpool(history.add, history_kind, title, summary,
                                               req.model_dump(by_alias=True, exclude_none=True))
            result = dict(result, history_id=entry_id)
        return JSONResponse(result)
    return _endpoint


# ----------------------------------------------------------------- handlers

def _health(_request):
    return JSONResponse({"status": "ok", "version": VERSION, "uptime_seconds": round(time.time() - STARTED, 1),
                         "python": sys.version.split()[0], "history_db": str(history.db_path().name)})


async def _examples(_request):
    return JSONResponse({"examples": examples.list_examples()})


async def _example(request: Request):
    return JSONResponse(examples.get_example(request.path_params["key"]))


async def _motif_library(_request):
    return JSONResponse({"motifs": rna.MOTIF_LIBRARY, "limits": {"max_sequence": rna.MAX_SEQUENCE_LENGTH,
                                                                 "max_fold": advanced.MAX_FOLD_LENGTH,
                                                                 "max_hairpin_scan": advanced.MAX_HAIRPIN_SCAN,
                                                                 "max_tm": advanced.MAX_TM_LENGTH,
                                                                 "max_upload_bytes": MAX_UPLOAD_BYTES}})


def _rna_summary(req, res):
    if not res.get("valid"):
        return "Invalid sequence", {"valid": False, "error": res.get("error")}
    return (f"RNA {res['record_id']} · {res['length']} nt",
            {"valid": True, "length": res["length"], "gc_percent": res["composition"]["gc_percent"],
             "orfs": len(res["orfs"]), "motif_hits": sum(m["count"] for m in res["motifs"])})


def _rna_analyze(req: RnaAnalyzeRequest):
    return rna.analyze_sequence(req.text, convert_t=req.convert_t, record_index=req.record_index,
                                min_orf_codons=req.min_orf_codons,
                                custom_motifs=[m.model_dump() for m in req.motifs], filename=req.filename)


async def _rna_upload(request: Request):
    ctype = request.headers.get("content-type", "")
    if "multipart/form-data" not in ctype:
        raise HTTPException(415, "upload must be multipart/form-data with a 'file' field")
    async with request.form(max_files=1, max_fields=5) as form:
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise EngineError("no file field named 'file' in the upload", "file")
        name = Path(upload.filename or "upload.txt").name
        ext = Path(name).suffix.lower()
        if ext not in UPLOAD_EXTENSIONS:
            raise EngineError(f"unsupported file type '{ext or '(none)'}'; allowed: "
                              f"{', '.join(sorted(UPLOAD_EXTENSIONS))}", "file", code="unsupported_file")
        data = await upload.read(MAX_UPLOAD_BYTES + 1)  # never written to disk
    if len(data) > MAX_UPLOAD_BYTES:
        raise EngineError(f"file is larger than {MAX_UPLOAD_BYTES // 1024} KiB", "file", code="too_large")
    if b"\x00" in data:
        raise EngineError("the file looks binary (contains NUL bytes); upload a FASTA or plain-text file", "file",
                          code="unsupported_file")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise EngineError(f"the file is not UTF-8 text (byte {exc.start})", "file", code="unsupported_file") from exc
    parsed = await run_in_threadpool(rna.parse_sequence_text, text, name)
    records = []
    for r in parsed["records"][:200]:
        norm = rna.normalize_sequence(r["raw"], True)
        records.append({"id": r["id"], "description": r["description"], "length": norm["length_including_invalid"],
                        "valid": norm["valid"], "invalid_count": norm["invalid_count"]})
    return JSONResponse({"filename": name, "format": parsed["format"], "record_count": len(parsed["records"]),
                         "records": records, "text": text})


def _auto_summary(req, res):
    a = getattr(req, "automaton", None) or getattr(req, "a", None)
    return (a.name or a.type) if a else "automaton", {}


def _run_summary(req, res):
    return (f"Run {req.automaton.name or req.automaton.type}",
            {"accepted": res["accepted"], "input_length": len(res["input"])})


def _min_summary(req, res):
    return (f"Minimize {req.automaton.name or 'DFA'}", res["counts"])


def _subset_summary(req, res):
    return (f"Subset construction {req.automaton.name or 'NFA'}", res["counts"])


def _eq_summary(req, res):
    return (f"Equivalence {req.a.name or 'A'} vs {req.b.name or 'B'}",
            {"equivalent": res["equivalent"], "counterexample": res.get("counterexample_text")})


def _fold_summary(req, res):
    return (f"CFG fold · {len(res['sequence'])} nt", {"pairs": res["pair_count"], "structure": res["structure"][:80]})


async def _history_list(request: Request):
    try:
        limit = max(1, min(500, int(request.query_params.get("limit", 100))))
    except ValueError:
        raise EngineError("limit must be an integer", "limit")
    kind = request.query_params.get("kind") or None
    return JSONResponse({"entries": await run_in_threadpool(history.list_entries, limit, kind)})


def _history_id(request: Request) -> int:
    try:
        return int(request.path_params["entry_id"])
    except ValueError:
        raise EngineError("history id must be an integer", "id", code="not_found")


async def _history_get(request: Request):
    entry = await run_in_threadpool(history.get, _history_id(request))
    if entry is None:
        raise EngineError("history entry not found", "id", code="not_found")
    return JSONResponse(entry)


async def _history_delete(request: Request):
    if not await run_in_threadpool(history.delete, _history_id(request)):
        raise EngineError("history entry not found", "id", code="not_found")
    return Response(status_code=204)


async def _history_clear(_request):
    return JSONResponse({"deleted": await run_in_threadpool(history.clear)})


# ----------------------------------------------------------------- error handlers

async def _engine_error(_request, exc: EngineError):
    return error_response(STATUS_FOR_CODE.get(exc.code, 400), exc.code, exc.message, exc.field)


async def _validation_error(_request, exc: ValidationError):
    details = [{"loc": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()[:20]]
    first = details[0] if details else {"loc": None, "message": "invalid request"}
    return error_response(422, "validation_error", f"{first['loc']}: {first['message']}", first["loc"], details)


async def _http_error(_request, exc: HTTPException):
    code = {404: "not_found", 405: "method_not_allowed", 413: "too_large", 415: "unsupported_media_type"}.get(
        exc.status_code, "http_error")
    return error_response(exc.status_code, code, str(exc.detail))


async def _server_error(request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)
    return error_response(500, "internal_error", "An unexpected server error occurred. The request was not completed.")


# ----------------------------------------------------------------- middleware (pure ASGI)

class LimitAndHeaders:
    """Rejects bodies over MAX_BODY_BYTES (413) and adds security headers."""

    CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
           "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers") or [])
        length = headers.get(b"content-length")
        if length is not None:
            try:
                too_big = int(length) > MAX_BODY_BYTES
            except ValueError:
                too_big = True
            if too_big:
                resp = error_response(413, "too_large", f"request body exceeds {MAX_BODY_BYTES // (1024 * 1024)} MiB")
                return await resp(scope, receive, send)

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise HTTPException(413, "request body too large")
            return message

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                h = list(message.get("headers", []))
                h += [(b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer"),
                      (b"content-security-policy", self.CSP.encode())]
                if scope["path"].startswith("/api/"):
                    h.append((b"cache-control", b"no-store"))
                message["headers"] = h
            await send(message)

        await self.app(scope, limited_receive, send_with_headers)


# ----------------------------------------------------------------- app

api_routes = [
    Route("/health", _health, methods=["GET"]),
    Route("/examples", _examples, methods=["GET"]),
    Route("/examples/{key}", _example, methods=["GET"]),
    Route("/automata/validate", endpoint(AutomatonOnly, lambda r: simulate.describe_spec(r.automaton.spec())),
          methods=["POST"]),
    Route("/automata/run", endpoint(RunRequest, lambda r: simulate.run_spec(r.automaton.spec(), r.input),
                                        "run", _run_summary), methods=["POST"]),
    Route("/automata/epsilon-eliminate",
          endpoint(AutomatonOnly, lambda r: conversions.epsilon_eliminate_spec(r.automaton.spec())), methods=["POST"]),
    Route("/automata/subset",
          endpoint(SubsetRequest, lambda r: conversions.subset_spec(r.automaton.spec(), r.include_dead_state),
                   "subset", _subset_summary), methods=["POST"]),
    Route("/automata/minimize", endpoint(AutomatonOnly, lambda r: minimize.minimize_spec(r.automaton.spec()),
                                             "minimize", _min_summary), methods=["POST"]),
    Route("/automata/equivalence",
          endpoint(PairRequest, lambda r: equivalence.check_equivalence(r.a.spec(), r.b.spec()),
                   "equivalence", _eq_summary), methods=["POST"]),
    Route("/automata/bounded-test",
          endpoint(BoundedRequest, lambda r: equivalence.bounded_test(r.a.spec(), r.b.spec(), r.max_length,
                                                                      r.random_count, r.random_max_length, r.seed)),
          methods=["POST"]),
    Route("/automata/compare",
          endpoint(CompareRequest, lambda r: equivalence.compare(r.a.spec(), r.b.spec(), r.input)), methods=["POST"]),
    Route("/rna/motifs", _motif_library, methods=["GET"]),
    Route("/rna/analyze", endpoint(RnaAnalyzeRequest, _rna_analyze, "rna", _rna_summary), methods=["POST"]),
    Route("/rna/upload", _rna_upload, methods=["POST"]),
    Route("/rna/orf-trace", endpoint(OrfTraceRequest, lambda r: rna.orf_trace(r.sequence, r.frame)),
          methods=["POST"]),
    Route("/motif/compile", endpoint(MotifCompileRequest, lambda r: rna.compile_motif_spec(r.pattern)),
          methods=["POST"]),
    Route("/advanced/fold", endpoint(FoldRequest, lambda r: advanced.fold_spec(r.sequence, r.min_loop),
                                         "fold", _fold_summary), methods=["POST"]),
    Route("/advanced/hairpins",
          endpoint(HairpinRequest, lambda r: advanced.hairpin_scan_spec(r.sequence, r.min_len, r.max_len, r.allow_center)),
          methods=["POST"]),
    Route("/history", _history_list, methods=["GET"]),
    Route("/history", _history_clear, methods=["DELETE"]),
    Route("/history/{entry_id}", _history_get, methods=["GET"]),
    Route("/history/{entry_id}", _history_delete, methods=["DELETE"]),
]

# The API is its own sub-router so unknown endpoints give 404 and a wrong HTTP
# method on a real endpoint gives 405 (instead of falling through to the
# static file server).
routes = [
    Mount("/api", routes=api_routes),
    Mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web"),
]

exception_handlers = {EngineError: _engine_error, ValidationError: _validation_error,
                      HTTPException: _http_error, Exception: _server_error}

app = LimitAndHeaders(Starlette(routes=routes, exception_handlers=exception_handlers))
