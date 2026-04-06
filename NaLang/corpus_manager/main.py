from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import io
import os
import re
from collections import Counter
from contextlib import contextmanager

import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag

for pkg in ["punkt", "punkt_tab", "averaged_perceptron_tagger",
            "averaged_perceptron_tagger_eng", "wordnet", "stopwords"]:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

app = FastAPI(title="Corpus Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "corpus.db"

POS_MAP = {
    "NN": "Noun", "NNS": "Noun (plural)", "NNP": "Proper noun", "NNPS": "Proper noun (pl.)",
    "VB": "Verb (base)", "VBD": "Verb (past)", "VBG": "Verb (gerund)",
    "VBN": "Verb (past part.)", "VBP": "Verb (present)", "VBZ": "Verb (3rd sg.)",
    "JJ": "Adjective", "JJR": "Adjective (comp.)", "JJS": "Adjective (superl.)",
    "RB": "Adverb", "RBR": "Adverb (comp.)", "RBS": "Adverb (superl.)",
    "PRP": "Pronoun", "PRP$": "Pronoun (poss.)", "DT": "Determiner",
    "IN": "Preposition/Conj.", "CC": "Coord. conj.", "CD": "Cardinal",
    "MD": "Modal", "UH": "Interjection",
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT,
                author TEXT,
                year INTEGER,
                genre TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

init_db()

lemmatizer = WordNetLemmatizer()


def analyze_text(text: str) -> dict:
    sentences = sent_tokenize(text)
    tokens_raw = word_tokenize(text)
    tokens = [t for t in tokens_raw if re.match(r"[a-zA-Z]", t)]
    tokens_lower = [t.lower() for t in tokens]
    tagged = pos_tag(tokens)
    lemmas = [lemmatizer.lemmatize(t.lower()) for t in tokens]

    wordform_freq = Counter(tokens_lower)
    lemma_freq = Counter(lemmas)
    pos_freq = Counter(tag for _, tag in tagged)

    morph = [
        {
            "wordform": tok,
            "lemma": lemmatizer.lemmatize(tok.lower()),
            "pos_tag": tag,
            "pos_label": POS_MAP.get(tag, tag),
        }
        for tok, tag in tagged
    ]

    return {
        "num_sentences": len(sentences),
        "num_tokens": len(tokens),
        "num_types": len(set(tokens_lower)),
        "type_token_ratio": round(len(set(tokens_lower)) / len(tokens), 4) if tokens else 0,
        "wordform_freq": wordform_freq.most_common(50),
        "lemma_freq": lemma_freq.most_common(50),
        "pos_freq": {POS_MAP.get(k, k): v for k, v in pos_freq.most_common(20)},
        "morphology": morph[:300],
    }


def build_concordance(text: str, query: str, window: int = 5) -> list:
    tokens = word_tokenize(text)
    q = query.lower()
    results = []
    for i, tok in enumerate(tokens):
        if tok.lower() == q:
            left = tokens[max(0, i - window): i]
            right = tokens[i + 1: i + window + 1]
            results.append({
                "left": " ".join(left),
                "keyword": tok,
                "right": " ".join(right),
                "position": i,
            })
    return results


def extract_text_from_file(upload: UploadFile) -> str:
    content = upload.file.read()
    fn = upload.filename.lower()
    if fn.endswith(".txt"):
        return content.decode("utf-8", errors="replace")
    if fn.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            raise HTTPException(400, "Install pdfplumber: pip install pdfplumber")
    if fn.endswith((".docx", ".doc")):
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise HTTPException(400, "Install python-docx: pip install python-docx")
    if fn.endswith(".rtf"):
        text = content.decode("utf-8", errors="replace")
        text = re.sub(r"\{[^{}]*\}", "", text)
        text = re.sub(r"\\[a-z]+\d*\s?", "", text)
        return text.strip()
    raise HTTPException(400, f"Unsupported format: {fn}")


class DocumentCreate(BaseModel):
    title: str
    source: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    content: str

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    content: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse("static/index.html")

@app.get("/api/documents")
def list_documents(search: Optional[str] = None, genre: Optional[str] = None, author: Optional[str] = None):
    with get_db() as conn:
        q = "SELECT id, title, source, author, year, genre, created_at FROM documents WHERE 1=1"
        params = []
        if search:
            q += " AND (title LIKE ? OR content LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        if genre:
            q += " AND genre = ?"
            params.append(genre)
        if author:
            q += " AND author LIKE ?"
            params.append(f"%{author}%")
        return [dict(r) for r in conn.execute(q, params).fetchall()]

@app.post("/api/documents", status_code=201)
def create_document(doc: DocumentCreate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO documents (title, source, author, year, genre, content) VALUES (?,?,?,?,?,?)",
            (doc.title, doc.source, doc.author, doc.year, doc.genre, doc.content)
        )
        conn.commit()
        return {"id": cur.lastrowid, "message": "Created"}

@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return dict(row)

@app.put("/api/documents/{doc_id}")
def update_document(doc_id: int, doc: DocumentUpdate):
    fields = {k: v for k, v in doc.dict().items() if v is not None}
    if not fields:
        raise HTTPException(400, "Nothing to update")
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_db() as conn:
        conn.execute(f"UPDATE documents SET {set_clause} WHERE id=?", (*fields.values(), doc_id))
        conn.commit()
        return {"message": "Updated"}

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        conn.commit()
        return {"message": "Deleted"}

@app.post("/api/upload", status_code=201)
def upload_file(
    file: UploadFile = File(...),
    title: str = Query(default=""),
    author: str = Query(default=""),
    source: str = Query(default=""),
    genre: str = Query(default=""),
):
    text = extract_text_from_file(file)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO documents (title, source, author, genre, content) VALUES (?,?,?,?,?)",
            (title or file.filename, source, author, genre, text)
        )
        conn.commit()
        return {"id": cur.lastrowid, "chars": len(text), "message": "Uploaded"}

@app.get("/api/documents/{doc_id}/analyze")
def analyze_document(doc_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT content FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return analyze_text(row["content"])

@app.post("/api/analyze")
def analyze_raw(body: dict):
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(400, "No text")
    return analyze_text(text)

@app.get("/api/documents/{doc_id}/concordance")
def concordance_document(doc_id: int, query: str, window: int = 5):
    with get_db() as conn:
        row = conn.execute("SELECT content FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        results = build_concordance(row["content"], query, window)
        return {"query": query, "hits": len(results), "concordance": results}

@app.post("/api/concordance")
def concordance_raw(body: dict):
    text = body.get("text", "")
    query = body.get("query", "")
    window = int(body.get("window", 5))
    if not text or not query:
        raise HTTPException(400, "Need text and query")
    results = build_concordance(text, query, window)
    return {"query": query, "hits": len(results), "concordance": results}

@app.get("/api/corpus/stats")
def corpus_stats():
    with get_db() as conn:
        rows = conn.execute("SELECT content FROM documents").fetchall()
        all_text = " ".join(r["content"] for r in rows)
        count = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]
        if not all_text.strip():
            return {"num_documents": count, "message": "Corpus is empty"}
        stats = analyze_text(all_text)
        stats["num_documents"] = count
        return stats

app.mount("/static", StaticFiles(directory="static"), name="static")
