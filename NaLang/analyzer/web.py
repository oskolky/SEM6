from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from analysis_engine import analyse_text, extract_text, nlp
from schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(
    title="English Syntactic + Semantic Analyser",
    description="POS tagging, dependency + constituency parsing, NER, SRL via spaCy.",
    version="2.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    p = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(p.read_text(encoding="utf-8") if p.exists() else "<h1>API running — open /docs</h1>")


@app.get("/health")
async def health():
    return {"status": "ok", "spacy_model": nlp.meta["name"], "version": "2.0.0"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not req.text.strip():
        raise HTTPException(400, "Text cannot be empty.")
    if len(req.text) > 50_000:
        raise HTTPException(400, "Text too long (max 50 000 chars).")
    return analyse_text(req.text)


@app.post("/upload", response_model=AnalyzeResponse)
async def upload(file: UploadFile = File(...)):
    allowed = {".txt", ".pdf", ".html", ".htm", ".rtf", ".doc", ".docx"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported: {ext}")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10 MB).")
    text = extract_text(file.filename, content)
    if not text.strip():
        raise HTTPException(400, "Could not extract text.")
    return analyse_text(text)
