"""
GEO Guardian - FastAPI backend.

  GET  /api/presets          -> quick-start scan presets
  POST /api/process          -> start a visibility scan (brand/category/competitors)
  GET  /api/events/{job_id}  -> SSE: live probe results + final dashboard
  POST /api/brief            -> turn selected remediation actions into a content brief

Run:  python server.py   (http://127.0.0.1:8030)
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Form, Header
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agents_pipeline import GeoResult, make_brief, run_pipeline

load_dotenv()

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="GEO Guardian")
JOBS: dict[str, asyncio.Queue] = {}
KEY_LOCK = asyncio.Lock()

PRESETS = [
    {"name": "Acme Analytics", "brand": "Acme Analytics",
     "category": "product analytics tools for startups",
     "competitors": "Mixpanel, Amplitude, PostHog"},
    {"name": "NimbusPay", "brand": "NimbusPay",
     "category": "online payment gateways for SaaS companies",
     "competitors": "Stripe, Adyen, Braintree"},
    {"name": "FernRoast", "brand": "FernRoast",
     "category": "specialty coffee subscription boxes",
     "competitors": "Blue Bottle, Trade Coffee, Atlas Coffee"},
]


def friendly_error(e: Exception) -> str:
    low = str(e).lower()
    if "api key" in low or "api_key" in low:
        return "OpenAI API key missing or rejected. Add a key in the top bar or set OPENAI_API_KEY on the server."
    if "rate limit" in low or "quota" in low:
        return "OpenAI rate limit or quota reached. Add credit or retry later."
    return f"{type(e).__name__}: {e}"


def serialize(r: GeoResult) -> dict:
    return {
        "brand": r.brand, "category": r.category, "competitors": r.competitors,
        "probes": r.probes, "score": r.score, "remediation": r.remediation,
        "summary": r.summary,
        "audit_log": [asdict(e) for e in r.audit_log],
    }


def apply_key(key) -> None:
    if key:
        os.environ["OPENAI_API_KEY"] = key
        try:
            from agents import set_default_openai_key
            set_default_openai_key(key)
        except Exception:
            pass


async def run_job(job_id: str, brand: str, category: str, competitors: list[str], n: int, custom_probes=None, key=None) -> None:
    q = JOBS[job_id]

    def emit(etype: str, **kw) -> None:
        q.put_nowait({"type": etype, **kw})

    try:
        if not brand.strip() or not category.strip():
            emit("error", message="Brand and category are required.")
            return

        def on_progress(agent: str, status: str) -> None:
            q.put_nowait({"type": "progress", "agent": agent, "status": status})

        def on_probe(row: dict) -> None:
            q.put_nowait({"type": "probe", "data": {
                "query": row.get("query"), "mentioned": row.get("mentioned"),
                "rank": row.get("rank"), "sentiment": row.get("sentiment"),
            }})

        async with KEY_LOCK:
            apply_key(key)
            result = await run_pipeline(
                brand, category, competitors, n,
                custom_probes=custom_probes,
                on_progress=on_progress,
                on_probe=on_probe,
            )
        emit("result", data=serialize(result))
    except Exception as e:  # noqa: BLE001
        emit("error", message=friendly_error(e))
    finally:
        q.put_nowait(None)


@app.get("/api/presets")
async def presets() -> JSONResponse:
    return JSONResponse(PRESETS)


@app.post("/api/process")
async def process(
    brand: str = Form(""),
    category: str = Form(""),
    competitors: str = Form(""),
    probes: int = Form(4),
    questions: str = Form(""),
    x_openai_key: str = Header(None),
) -> JSONResponse:
    comp = [c.strip() for c in competitors.split(",") if c.strip()][:6]
    custom = [q.strip() for q in questions.splitlines() if q.strip()][:8]
    job_id = uuid.uuid4().hex
    JOBS[job_id] = asyncio.Queue()
    asyncio.create_task(run_job(job_id, brand, category, comp, probes, custom_probes=custom, key=x_openai_key))
    return JSONResponse({"job_id": job_id})


@app.post("/api/run")
async def run_now(
    brand: str = Form(""),
    category: str = Form(""),
    competitors: str = Form(""),
    probes: int = Form(4),
    questions: str = Form(""),
    x_openai_key: str = Header(None),
) -> JSONResponse:
    if not brand.strip() or not category.strip():
        return JSONResponse({"error": "Brand and category are required."}, status_code=200)
    comp = [c.strip() for c in competitors.split(",") if c.strip()][:6]
    custom = [q.strip() for q in questions.splitlines() if q.strip()][:8]
    try:
        async with KEY_LOCK:
            apply_key(x_openai_key)
            result = await run_pipeline(brand, category, comp, probes, custom_probes=custom)
        return JSONResponse({"data": serialize(result)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": friendly_error(e)}, status_code=200)


@app.get("/api/events/{job_id}")
async def events(job_id: str) -> StreamingResponse:
    async def stream():
        q = JOBS.get(job_id)
        if q is None:
            yield f"data: {json.dumps({'type': 'error', 'message': 'unknown job'})}\n\n"
            return
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            JOBS.pop(job_id, None)

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/brief")
async def brief(payload: dict = Body(...), x_openai_key: str = Header(None)) -> JSONResponse:
    actions = payload.get("actions") or []
    if not actions:
        return JSONResponse({"error": "Select at least one action."}, status_code=200)
    try:
        async with KEY_LOCK:
            apply_key(x_openai_key)
            result = await make_brief(payload.get("brand") or "", payload.get("category") or "", actions)
        return JSONResponse(result.model_dump())
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": friendly_error(e)}, status_code=200)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"openai_key": bool(os.getenv("OPENAI_API_KEY"))})


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8030"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
