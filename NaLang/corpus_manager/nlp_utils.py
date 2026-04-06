import spacy
import nltk
from collections import Counter
from typing import List, Dict, Any

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
    nlp = spacy.load("en_core_web_sm")


def process_text(text: str) -> List[Dict[str, Any]]:
    """
    Process raw text with spaCy.

    spaCy has a hard limit on input length (`nlp.max_length`). For very long
    documents we process the text in chunks to avoid ValueError [E088].
    """

    text = text or ""
    if not text.strip():
        return []

    def process_doc(doc, token_offset: int, sentence_offset: int) -> tuple[list[dict], int, int]:
        tokens_local: list[dict] = []
        sent_count = 0
        for sent_idx, sent in enumerate(doc.sents):
            sent_count = sent_idx + 1
            for token in sent:
                tokens_local.append({
                    "position": token_offset + token.i,
                    "wordform": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "dep": token.dep_,
                    "is_alpha": token.is_alpha,
                    "is_stop": token.is_stop,
                    "sentence_idx": sentence_offset + sent_idx,
                })
        return tokens_local, sent_count, len(doc)

    # Fast path for "normal" inputs.
    if len(text) <= nlp.max_length:
        doc = nlp(text)
        tokens, _, _ = process_doc(doc, token_offset=0, sentence_offset=0)
        return tokens

    # Chunking path for long inputs.
    # We keep chunking in *characters* because `nlp.max_length` is in characters.
    chunk_chars = max(200_000, int(nlp.max_length) - 1_000)

    tokens: list[dict] = []
    start = 0
    token_offset = 0
    sentence_offset = 0

    while start < len(text):
        end = min(start + chunk_chars, len(text))

        if end < len(text):
            # Try to break on a boundary near the end of the chunk.
            window = text[start:end]
            last_newline = window.rfind("\n")
            last_space = window.rfind(" ")
            last_punct = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
            last_break = max(last_newline, last_space, last_punct)

            # If we didn't find anything good, keep the original end.
            if last_break > 0 and last_break > len(window) - 2_000:
                end = start + last_break + 1  # include boundary char

        chunk = text[start:end]
        doc = nlp(chunk)
        chunk_tokens, sent_count, doc_token_count = process_doc(
            doc,
            token_offset=token_offset,
            sentence_offset=sentence_offset,
        )
        tokens.extend(chunk_tokens)

        token_offset += doc_token_count
        sentence_offset += sent_count
        start = end

    return tokens


def get_frequency_stats(tokens: List[Dict]) -> Dict:
    alpha_tokens = [t for t in tokens if t["is_alpha"]]
    wordform_freq = Counter(t["wordform"].lower() for t in alpha_tokens)
    lemma_freq = Counter(t["lemma"].lower() for t in alpha_tokens)
    pos_freq = Counter(t["pos"] for t in alpha_tokens)
    tag_freq = Counter(t["tag"] for t in alpha_tokens)
    content_tokens = [t for t in alpha_tokens if not t["is_stop"]]
    content_freq = Counter(t["lemma"].lower() for t in content_tokens)
    return {
        "wordform_freq": dict(wordform_freq.most_common(50)),
        "lemma_freq": dict(lemma_freq.most_common(50)),
        "pos_freq": dict(pos_freq.most_common()),
        "tag_freq": dict(tag_freq.most_common(30)),
        "content_freq": dict(content_freq.most_common(30)),
        "total_tokens": len(alpha_tokens),
        "unique_wordforms": len(wordform_freq),
        "unique_lemmas": len(lemma_freq),
        "type_token_ratio": round(len(wordform_freq) / len(alpha_tokens), 4) if alpha_tokens else 0,
    }


def get_concordance(tokens: List[Dict], query: str, window: int = 5) -> List[Dict]:
    query = query.lower().strip()
    results = []
    for i, token in enumerate(tokens):
        if token["wordform"].lower() == query or token["lemma"].lower() == query:
            left_start = max(0, i - window)
            right_end = min(len(tokens), i + window + 1)
            left_ctx = " ".join(t["wordform"] for t in tokens[left_start:i])
            right_ctx = " ".join(t["wordform"] for t in tokens[i + 1:right_end])
            results.append({
                "left": left_ctx,
                "keyword": token["wordform"],
                "right": right_ctx,
                "position": token["position"],
                "sentence_idx": token["sentence_idx"],
                "lemma": token["lemma"],
                "pos": token["pos"],
                "tag": token["tag"],
            })
    return results


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "txt":
        return file_bytes.decode("utf-8", errors="replace")
    elif ext == "pdf":
        import io
        try:
            import pdfminer.high_level as pdfminer
            return pdfminer.extract_text(io.BytesIO(file_bytes))
        except ImportError:
            raise ValueError("pdfminer.six required: pip install pdfminer.six")
    elif ext == "docx":
        import io
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise ValueError("python-docx required: pip install python-docx")
    elif ext == "doc":
        # Legacy DOC requires external parser; textract is the most practical fallback.
        try:
            import tempfile
            import textract
            with tempfile.NamedTemporaryFile(suffix=".doc", delete=True) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                text = textract.process(tmp.name)
            return text.decode("utf-8", errors="replace")
        except ImportError:
            raise ValueError("Legacy .doc requires textract: pip install textract")
    elif ext == "rtf":
        try:
            from striprtf.striprtf import rtf_to_text
            return rtf_to_text(file_bytes.decode("utf-8", errors="replace"))
        except ImportError:
            raise ValueError("striprtf required: pip install striprtf")
    else:
        raise ValueError(f"Unsupported format: .{ext}")
