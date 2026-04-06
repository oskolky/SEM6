from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from routers import analysis, concordance, corpus

app = FastAPI(title="Corpus Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    # UI is a single HTML file (no build step).
    return FileResponse("templates/index.html")


app.include_router(corpus.router, prefix="/api/corpus", tags=["corpus"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(concordance.router, prefix="/api/concordance", tags=["concordance"])
