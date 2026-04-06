from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db
from nlp_utils import get_concordance

router = APIRouter()


@router.get("/search")
async def concordance_search(
    query: str = Query(..., description="Word or phrase to search"),
    doc_id: Optional[int] = Query(None, description="Limit to a specific document"),
    window: int = Query(5, description="Context window size (tokens each side)"),
    pos_filter: Optional[str] = Query(None, description="Filter by POS tag"),
    limit: int = Query(100),
):
    """Return concordance (KWIC) lines for a query."""
    conn = get_db()
    if doc_id:
        sql = "SELECT * FROM tokens WHERE doc_id=? ORDER BY position"
        rows = conn.execute(sql, (doc_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tokens ORDER BY doc_id, position").fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No tokens found")

    tokens = [dict(r) for r in rows]
    results = get_concordance(tokens, query, window=window)

    if pos_filter:
        results = [r for r in results if r["pos"] == pos_filter.upper()]

    total = len(results)
    results = results[:limit]

    # Attach document info
    conn = get_db()
    doc_map = {d["id"]: d["title"] for d in conn.execute("SELECT id, title FROM documents").fetchall()}
    conn.close()

    for r in results:
        # Find which doc this token belongs to by matching position
        pass  # positions are unique per doc; we need doc_id attached

    return {
        "query": query,
        "total_matches": total,
        "shown": len(results),
        "window": window,
        "results": results,
    }


@router.get("/search_phrase")
async def phrase_search(
    phrase: str = Query(..., description="Multi-word phrase to find"),
    doc_id: Optional[int] = Query(None),
    window: int = Query(5),
):
    """Search for an exact multi-word phrase in the corpus."""
    conn = get_db()
    words = phrase.lower().split()
    n = len(words)

    if doc_id:
        rows = conn.execute("SELECT * FROM tokens WHERE doc_id=? ORDER BY position", (doc_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tokens ORDER BY doc_id, position").fetchall()
    conn.close()

    tokens = [dict(r) for r in rows]
    results = []
    for i in range(len(tokens) - n + 1):
        chunk = tokens[i:i+n]
        if all(chunk[j]["wordform"].lower() == words[j] for j in range(n)):
            left_tokens = tokens[max(0, i-window):i]
            right_tokens = tokens[i+n:min(len(tokens), i+n+window)]
            results.append({
                "left": " ".join(t["wordform"] for t in left_tokens),
                "keyword": " ".join(t["wordform"] for t in chunk),
                "right": " ".join(t["wordform"] for t in right_tokens),
                "position": tokens[i]["position"],
            })
    return {"phrase": phrase, "total_matches": len(results), "results": results}
