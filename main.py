import json
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agents
import tools

D = Path(__file__).parent
CACHE_FILE = D / "cache.json"
cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}

app = FastAPI()


class Ask(BaseModel):
    question: str
    plant_error: bool = False


@app.get("/")
def home():
    return FileResponse(D / "index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/map")
def map_data(year: int = 2024):
    return tools.map_data(year)


class Names(BaseModel):
    names: list[str]


@app.post("/resolve")
def resolve(body: Names):
    return tools.resolve(body.names[:200])


@app.post("/ask")
def ask(body: Ask):
    q = body.question.strip()[:500]
    if not q:
        return {"status": "error", "answer": "Type a question first.", "steps": [], "tables": [], "highlight": [], "issues": []}
    key = " ".join(re.sub(r"[^a-z0-9 ]", " ", q.lower()).split())
    if key in cache and not body.plant_error:
        return {**cache[key], "cached": True}
    try:
        out = agents.answer(q, plant=body.plant_error)
    except Exception as e:  # both models failed or are rate limited
        print("ask failed:", e)
        return {"status": "error", "steps": [], "tables": [], "highlight": [], "issues": [],
                "answer": "The AI services are busy right now. Please try again in a minute."}
    if not body.plant_error and out["status"] == "verified":  # keep only good answers, a refusal may be a one-off
        cache[key] = out
        try:
            CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # read-only disk on some hosts; the in-memory cache still works
    return out

# files in /data (put india-states.geojson here) are served as-is; check_dir=False so the app still starts without the folder
app.mount("/data", StaticFiles(directory=D / "data", check_dir=False))
