from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db
from nlp_utils import get_frequency_stats

router = APIRouter()


def _load_tokens(doc_id: Optional[int] = None):
    conn = get_db()
    if doc_id:
        rows = conn.execute(
            "SELECT * FROM tokens WHERE doc_id=? ORDER BY position", (doc_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tokens ORDER BY doc_id, position").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/frequency")
async def frequency_analysis(
    doc_id: Optional[int] = Query(None, description="Filter by document ID"),
    min_freq: int = Query(1, description="Minimum frequency threshold"),
    pos_filter: Optional[str] = Query(None, description="Filter by POS tag (NOUN, VERB, ADJ...)"),
    exclude_stopwords: bool = Query(False),
    limit: int = Query(50),
):
    """Frequency statistics for wordforms and lemmas."""
    tokens = _load_tokens(doc_id)
    if not tokens:
        raise HTTPException(status_code=404, detail="No tokens found")

    # Apply filters
    filtered = [t for t in tokens if t["is_alpha"]]
    if exclude_stopwords:
        filtered = [t for t in filtered if not t["is_stop"]]
    if pos_filter:
        filtered = [t for t in filtered if t["pos"] == pos_filter.upper()]

    from collections import Counter
    wordform_freq = Counter(t["wordform"].lower() for t in filtered)
    lemma_freq = Counter(t["lemma"].lower() for t in filtered)
    pos_freq = Counter(t["pos"] for t in filtered)

    return {
        "wordforms": [
            {"word": w, "freq": f} for w, f in wordform_freq.most_common(limit) if f >= min_freq
        ],
        "lemmas": [
            {"lemma": l, "freq": f} for l, f in lemma_freq.most_common(limit) if f >= min_freq
        ],
        "pos_distribution": dict(pos_freq),
        "total_tokens": len(filtered),
        "unique_wordforms": len(wordform_freq),
        "unique_lemmas": len(lemma_freq),
        "type_token_ratio": round(len(wordform_freq) / len(filtered), 4) if filtered else 0,
    }


@router.get("/morphology")
async def morphology_lookup(
    query: str = Query(..., description="Wordform or lemma to look up"),
    doc_id: Optional[int] = Query(None),
):
    """Get morphological characteristics of a word."""
    conn = get_db()
    sql = "SELECT DISTINCT wordform, lemma, pos, tag, dep, COUNT(*) as freq FROM tokens WHERE (LOWER(wordform)=? OR LOWER(lemma)=?) AND is_alpha=1"
    params = [query.lower(), query.lower()]
    if doc_id:
        sql += " AND doc_id=?"
        params.append(doc_id)
    sql += " GROUP BY wordform, lemma, pos, tag, dep ORDER BY freq DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No entries found for '{query}'")
    return [dict(r) for r in rows]


@router.get("/summary")
async def corpus_summary(doc_id: Optional[int] = Query(None)):
    """Overall corpus or document statistics."""
    conn = get_db()
    if doc_id:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        docs = [dict(doc)]
    else:
        docs = [dict(d) for d in conn.execute("SELECT * FROM documents").fetchall()]

    if not docs:
        conn.close()
        return {"message": "Corpus is empty"}

    tokens = _load_tokens(doc_id)
    alpha = [t for t in tokens if t["is_alpha"]]
    from collections import Counter
    wf = Counter(t["wordform"].lower() for t in alpha)
    lm = Counter(t["lemma"].lower() for t in alpha)
    pos = Counter(t["pos"] for t in alpha)

    conn.close()
    return {
        "document_count": len(docs),
        "total_tokens": len(alpha),
        "unique_wordforms": len(wf),
        "unique_lemmas": len(lm),
        "type_token_ratio": round(len(wf) / len(alpha), 4) if alpha else 0,
        "pos_distribution": dict(pos.most_common()),
        "documents": [{"id": d["id"], "title": d["title"], "word_count": d["word_count"]} for d in docs],
    }
