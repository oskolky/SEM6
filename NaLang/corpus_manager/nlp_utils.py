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
    doc = nlp(text)
    tokens = []
    for sent_idx, sent in enumerate(doc.sents):
        for token in sent:
            tokens.append({
                "position": token.i,
                "wordform": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "tag": token.tag_,
                "dep": token.dep_,
                "is_alpha": token.is_alpha,
                "is_stop": token.is_stop,
                "sentence_idx": sent_idx,
            })
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
    elif ext == "rtf":
        try:
            from striprtf.striprtf import rtf_to_text
            return rtf_to_text(file_bytes.decode("utf-8", errors="replace"))
        except ImportError:
            raise ValueError("striprtf required: pip install striprtf")
    else:
        raise ValueError(f"Unsupported format: .{ext}")
