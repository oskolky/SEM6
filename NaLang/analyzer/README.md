# SynParser — English Syntactic Analyser
**FastAPI + spaCy + Modern Web UI**

## Быстрый старт

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Скачать языковую модель spaCy
python -m spacy download en_core_web_sm

# 3. Запустить сервер
uvicorn main:app --reload --port 8000

# 4. Открыть браузер
# http://localhost:8000
```

## Структура проекта

```
synparser/
├── main.py              ← FastAPI бэкенд + NLP пайплайн
├── requirements.txt     ← зависимости
├── templates/
│   └── index.html       ← веб-интерфейс (SPA)
└── static/              ← статика (если нужна)
```

## API Endpoints

| Method | URL        | Description                              |
|--------|------------|------------------------------------------|
| GET    | `/`        | Веб-интерфейс                            |
| GET    | `/health`  | Статус сервера + версия модели           |
| POST   | `/analyze` | Анализ текста (JSON body)                |
| POST   | `/upload`  | Загрузка файла (multipart form)          |
| GET    | `/docs`    | Swagger UI (автоматически)              |
| GET    | `/redoc`   | ReDoc документация                       |

### POST /analyze
```json
// Request
{ "text": "The quick brown fox jumps over the lazy dog." }

// Response
{
  "text_length": 44,
  "sentence_count": 1,
  "token_count": 10,
  "sentences": [
    {
      "sentence_index": 0,
      "original": "The quick brown fox jumps over the lazy dog.",
      "root_text": "jumps",
      "root_lemma": "jump",
      "subject": "fox",
      "predicate": "jumps",
      "obj": "dog",
      "modifiers": ["over"],
      "tokens": [
        {
          "index": 0, "text": "The", "lemma": "the",
          "pos": "DET", "tag": "DT", "dep": "det",
          "head_index": 3, "head_text": "fox",
          "is_stop": true, "morph": "Definite=Def|PronType=Art"
        },
        ...
      ],
      "tree": { ... }
    }
  ]
}
```

## Поддерживаемые форматы
- **TXT** — обычный текст
- **PDF** — через pdfplumber / pypdf
- **HTML** — через BeautifulSoup
- **RTF** — через striprtf
- **DOC / DOCX** — через python-docx

## Использование другой модели spaCy

```python
# В main.py замените:
nlp = spacy.load("en_core_web_sm")   # маленькая (13 MB)
# на:
nlp = spacy.load("en_core_web_md")   # средняя (40 MB) — лучше
nlp = spacy.load("en_core_web_lg")   # большая (560 MB) — лучшая точность
nlp = spacy.load("en_core_web_trf")  # трансформер (GPU)

# Скачать:
# python -m spacy download en_core_web_md
```
