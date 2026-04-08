"""
main.py — FastAPI backend for English syntactic analysis via spaCy.

Run:
    uvicorn main:app --reload --port 8000

Endpoints:
    GET  /              → serve index.html
    POST /analyze       → analyse text, return JSON
    POST /upload        → upload file (PDF/DOCX/TXT/HTML/RTF), return JSON
    GET  /health        → health check
    GET  /docs          → Swagger UI (auto)
"""

from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional

import spacy
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Load spaCy model ──────────────────────────────────────────────────────────
# Install: python -m spacy download en_core_web_sm
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError(
        "spaCy model not found.\n"
        "Run:  python -m spacy download en_core_web_sm"
    )

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="English Syntactic Analyser",
    description="Automatic POS tagging, lemmatization and dependency parsing via spaCy.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent

# Serve static files if directory exists
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str
    model_config = {"json_schema_extra": {"example": {"text": "The quick brown fox jumps over the lazy dog."}}}


class TokenOut(BaseModel):
    index: int
    text: str
    lemma: str
    pos: str          # Universal POS (spaCy .pos_)
    tag: str          # Fine-grained tag (spaCy .tag_)
    dep: str          # Dependency label
    head_index: int
    head_text: str
    is_stop: bool
    morph: str        # Morphological features


class SentenceOut(BaseModel):
    sentence_index: int
    original: str
    root_text: str
    root_lemma: str
    subject: Optional[str]
    predicate: Optional[str]
    obj: Optional[str]
    modifiers: List[str]
    tokens: List[TokenOut]
    tree: dict        # recursive tree structure


class AnalyzeResponse(BaseModel):
    text_length: int
    sentence_count: int
    token_count: int
    sentences: List[SentenceOut]


# ── NLP helpers ───────────────────────────────────────────────────────────────

def _build_tree(token: spacy.tokens.Token, sent_start: int) -> dict:
    """Recursively build dependency tree dict from a spaCy token."""
    return {
        "index": token.i - sent_start,
        "text": token.text,
        "lemma": token.lemma_,
        "pos": token.pos_,
        "dep": token.dep_,
        "children": [_build_tree(child, sent_start) for child in token.children],
    }


def _extract_roles(sent: spacy.tokens.Span):
    """Extract subject, predicate, object, modifiers from a sentence span."""
    subject = predicate = obj = None
    modifiers = []

    root = sent.root
    predicate = root.text

    for tok in sent:
        if tok.dep_ in ("nsubj", "nsubjpass") and tok.head == root:
            # include compound / det / amod attached to subject
            subtree_words = [t.text for t in tok.subtree
                             if t.dep_ in ("det", "amod", "compound", "nummod") or t == tok]
            subject = " ".join(subtree_words) if subtree_words else tok.text
        elif tok.dep_ in ("dobj", "attr", "oprd") and tok.head == root:
            subtree_words = [t.text for t in tok.subtree
                             if t.dep_ in ("det", "amod", "compound") or t == tok]
            obj = " ".join(subtree_words) if subtree_words else tok.text
        elif tok.dep_ in ("advmod", "amod", "npadvmod") and tok.head == root:
            modifiers.append(tok.text)

    return subject, predicate, obj, modifiers


def analyse_text(text: str) -> AnalyzeResponse:
    doc = nlp(text)
    sentences_out = []

    for sent_idx, sent in enumerate(doc.sents):
        root = sent.root
        sent_start = sent.start

        tokens_out = []
        for tok in sent:
            tokens_out.append(TokenOut(
                index=tok.i - sent_start,
                text=tok.text,
                lemma=tok.lemma_,
                pos=tok.pos_,
                tag=tok.tag_,
                dep=tok.dep_,
                head_index=tok.head.i - sent_start,
                head_text=tok.head.text,
                is_stop=tok.is_stop,
                morph=str(tok.morph),
            ))

        subject, predicate, obj, modifiers = _extract_roles(sent)

        sentences_out.append(SentenceOut(
            sentence_index=sent_idx,
            original=sent.text.strip(),
            root_text=root.text,
            root_lemma=root.lemma_,
            subject=subject,
            predicate=predicate,
            obj=obj,
            modifiers=modifiers,
            tokens=tokens_out,
            tree=_build_tree(root, sent_start),
        ))

    return AnalyzeResponse(
        text_length=len(text),
        sentence_count=len(sentences_out),
        token_count=len(doc),
        sentences=sentences_out,
    )


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return content.decode("utf-8", errors="replace")

    elif ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            pass
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except ImportError:
            raise HTTPException(400, "Install pdfplumber or pypdf to process PDF files.")

    elif ext in (".html", ".htm"):
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(content, "html.parser").get_text(separator=" ")
        except ImportError:
            raw = content.decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", raw)

    elif ext == ".rtf":
        try:
            from striprtf.striprtf import rtf_to_text
            return rtf_to_text(content.decode("utf-8", errors="replace"))
        except ImportError:
            raw = content.decode("utf-8", errors="replace")
            return re.sub(r"\{[^}]*\}|\\[a-z]+\d*\s?", "", raw)

    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if "word/document.xml" in z.namelist():
                    xml = z.read("word/document.xml").decode("utf-8", errors="replace")
                    return re.sub(r"<[^>]+>", " ", xml)
            raise HTTPException(400, "Install python-docx to process DOCX files.")

    else:
        return content.decode("utf-8", errors="replace")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = BASE_DIR / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>English Syntactic Analyser API</h1><p>Open /docs</p>")


@app.get("/health")
async def health():
    return {"status": "ok", "spacy_model": nlp.meta["name"]}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not req.text.strip():
        raise HTTPException(400, "Text cannot be empty.")
    if len(req.text) > 50_000:
        raise HTTPException(400, "Text too long (max 50 000 characters).")
    return analyse_text(req.text)


@app.post("/upload", response_model=AnalyzeResponse)
async def upload(file: UploadFile = File(...)):
    allowed = {".txt", ".pdf", ".html", ".htm", ".rtf", ".doc", ".docx"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10 MB).")
    text = extract_text(file.filename, content)
    if not text.strip():
        raise HTTPException(400, "Could not extract text from file.")
    return analyse_text(text)
