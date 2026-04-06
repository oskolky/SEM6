# Corpus Manager

NLP corpus management system — FastAPI + spaCy + SQLite.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download spaCy English model
python -m spacy download en_core_web_sm

# 3. Run
python main.py

# 4. Open browser
#    App:  http://localhost:8000
#    Docs: http://localhost:8000/docs
```

## Features
- Upload TXT, PDF, DOCX, RTF files
- Auto NLP: tokenization, lemmatization, POS tagging (spaCy en_core_web_sm)
- Frequency analysis: wordforms, lemmas, POS distribution, TTR
- Concordance / KWIC search
- Morphological lookup
- Document metadata (author, genre, year, source)
- SQLite storage — no external DB needed

## Data Structures and Algorithms

### Storage model (SQLite)
- `documents` table:
  - bibliographic + typological metadata (`title`, `author`, `genre`, `year`, `source`, `filename`, `created_at`)
  - full text content (`content`)
  - precomputed size metric (`word_count`)
- `tokens` table:
  - token stream linked by `doc_id`
  - linguistic attributes: `wordform`, `lemma`, `pos`, `tag`, `dep`
  - processing flags: `is_alpha`, `is_stop`, `sentence_idx`, `position`

This schema supports corpus-level analytics and filtered per-document queries with minimal transformations.

### Core processing algorithms
- **NLP preprocessing**: spaCy tokenization + lemmatization + POS tagging (`process_text` in `nlp_utils.py`).
- **Frequency computation**: counters over filtered token subsets for wordforms, lemmas, POS classes.
- **Concordance (KWIC)**: linear scan of token sequence with context-window slicing around each match (by wordform or lemma).
- **Morphological lookup**: SQL aggregation (`GROUP BY`) over token attributes to produce unique morphological variants and frequencies.
- **Search and filtering**: SQL predicates over metadata and text (`LIKE`, exact genre match) with dynamic query composition.

## Project Structure
```
corpus_manager/
├── main.py            # FastAPI entry point
├── database.py        # SQLite init
├── nlp_utils.py       # NLP processing
├── requirements.txt
├── routers/
│   ├── corpus.py      # CRUD endpoints
│   ├── analysis.py    # Frequency & morphology
│   └── concordance.py # KWIC search
├── templates/index.html
├── static/
└── data/corpus.db     # auto-created
```

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/corpus/documents` | Upload document |
| GET | `/api/corpus/documents` | List documents |
| GET | `/api/corpus/documents?search=&genre=&author=` | Filter/search documents |
| PUT | `/api/corpus/documents/{id}` | Edit document metadata |
| DELETE | `/api/corpus/documents/{id}` | Delete document |
| GET | `/api/analysis/frequency` | Frequency stats |
| GET | `/api/analysis/morphology` | Morphological lookup |
| GET | `/api/analysis/summary` | Corpus summary |
| GET | `/api/concordance/search` | KWIC concordance |

## Requirement Coverage Checklist
- Input = natural-language query fragment (word/phrase): implemented via frequency/concordance/morphology query fields.
- Output = frequency, lemma, grammar/POS, morphology, metadata, concordance lists: implemented via `/api/analysis/*` and `/api/concordance/search`.
- GUI interaction (intuitive): single-page interface with tabs (Corpus, Upload, Frequency, Concordance, Morphology, Help).
- User help system: built-in Help tab with usage guidance and POS reference.
- Build/save/view/edit/extend/filter/search/document text: upload + persistent DB + metadata editing + deletion + filter/search in document list.
- Supported formats: TXT, RTF, PDF, DOCX, DOC (legacy DOC via `textract` fallback).
