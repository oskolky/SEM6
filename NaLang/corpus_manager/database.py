import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "corpus.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            content TEXT NOT NULL,
            language TEXT DEFAULT 'en',
            genre TEXT,
            author TEXT,
            year INTEGER,
            source TEXT,
            word_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            wordform TEXT NOT NULL,
            lemma TEXT,
            pos TEXT,
            tag TEXT,
            dep TEXT,
            is_alpha BOOLEAN,
            is_stop BOOLEAN,
            sentence_idx INTEGER,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()

init_db()
