from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
from nlp_utils import process_text, extract_text_from_file

router = APIRouter()


@router.get("/documents")
async def list_documents():
    """List all documents in the corpus."""
    conn = get_db()
    docs = conn.execute(
        "SELECT id, title, filename, language, genre, author, year, source, word_count, created_at FROM documents ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(d) for d in docs]


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int):
    """Get a single document with its metadata."""
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(doc)


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    genre: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    source: Optional[str] = Form(None),
):
    """Upload and process a new document."""
    file_bytes = await file.read()
    try:
        text = extract_text_from_file(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    tokens = process_text(text)
    word_count = sum(1 for t in tokens if t["is_alpha"])

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO documents (title, filename, content, language, genre, author, year, source, word_count)
           VALUES (?, ?, ?, 'en', ?, ?, ?, ?)""",
        (title, file.filename, text, genre, author, year, source, word_count)
    )
    doc_id = cursor.lastrowid

    cursor.executemany(
        """INSERT INTO tokens (doc_id, position, wordform, lemma, pos, tag, dep, is_alpha, is_stop, sentence_idx)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (doc_id, t["position"], t["wordform"], t["lemma"], t["pos"],
             t["tag"], t["dep"], t["is_alpha"], t["is_stop"], t["sentence_idx"])
            for t in tokens
        ]
    )
    conn.commit()
    conn.close()

    return {"id": doc_id, "title": title, "word_count": word_count, "tokens_processed": len(tokens)}


@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: int,
    title: Optional[str] = Form(None),
    genre: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    source: Optional[str] = Form(None),
):
    """Update document metadata."""
    conn = get_db()
    doc = conn.execute("SELECT id FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    updates = {}
    if title: updates["title"] = title
    if genre: updates["genre"] = genre
    if author: updates["author"] = author
    if year: updates["year"] = year
    if source: updates["source"] = source

    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE documents SET {set_clause} WHERE id=?", (*updates.values(), doc_id))
        conn.commit()
    conn.close()
    return {"updated": doc_id}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Delete a document and all its tokens."""
    conn = get_db()
    conn.execute("DELETE FROM tokens WHERE doc_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return {"deleted": doc_id}
