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
| DELETE | `/api/corpus/documents/{id}` | Delete document |
| GET | `/api/analysis/frequency` | Frequency stats |
| GET | `/api/analysis/morphology` | Morphological lookup |
| GET | `/api/analysis/summary` | Corpus summary |
| GET | `/api/concordance/search` | KWIC concordance |
