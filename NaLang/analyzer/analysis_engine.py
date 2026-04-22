from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import spacy
from fastapi import HTTPException

from schemas import (
    AnalyzeResponse,
    ConstituencyNodeOut,
    EntityOut,
    NounChunkOut,
    SemanticOut,
    SemanticRoleOut,
    SentenceOut,
    TokenOut,
)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError("Run:  python -m spacy download en_core_web_sm")


def _build_tree(token: spacy.tokens.Token, sent_start: int) -> Dict[str, Any]:
    return {
        "index": token.i - sent_start,
        "text": token.text,
        "lemma": token.lemma_,
        "pos": token.pos_,
        "dep": token.dep_,
        "children": [_build_tree(c, sent_start) for c in token.children],
    }


def _extract_roles(sent: spacy.tokens.Span):
    root = sent.root
    subject = predicate = obj = None
    modifiers: List[str] = []
    predicate = root.text
    for tok in sent:
        if tok.dep_ in ("nsubj", "nsubjpass") and tok.head == root:
            parts = [t.text for t in sorted(tok.subtree, key=lambda t: t.i)
                     if t.dep_ in ("det", "amod", "compound", "nummod") or t == tok]
            subject = " ".join(parts) or tok.text
        elif tok.dep_ in ("dobj", "obj", "attr", "oprd") and tok.head == root:
            parts = [t.text for t in sorted(tok.subtree, key=lambda t: t.i)
                     if t.dep_ in ("det", "amod", "compound") or t == tok]
            obj = " ".join(parts) or tok.text
        elif tok.dep_ in ("advmod", "amod", "npadvmod") and tok.head == root:
            modifiers.append(tok.text)
    return subject, predicate, obj, modifiers


_NER_DESC: Dict[str, str] = {
    "PERSON": "People, including fictional", "NORP": "Nationalities / political groups",
    "FAC": "Buildings, airports, bridges", "ORG": "Companies, agencies, institutions",
    "GPE": "Countries, cities, states", "LOC": "Non-GPE locations, bodies of water",
    "PRODUCT": "Objects, vehicles, foods", "EVENT": "Named events (wars, sports)",
    "WORK_OF_ART": "Titles of books, songs", "LAW": "Named legal documents",
    "LANGUAGE": "Any named language", "DATE": "Absolute or relative dates",
    "TIME": "Times smaller than a day", "PERCENT": "Percentage values",
    "MONEY": "Monetary values", "QUANTITY": "Measurements (weight, distance)",
    "ORDINAL": "First, second, etc.", "CARDINAL": "Other numerals",
}


def _extract_entities(sent: spacy.tokens.Span, sent_start: int) -> List[EntityOut]:
    return [
        EntityOut(
            text=e.text, label=e.label_,
            label_desc=_NER_DESC.get(e.label_, e.label_),
            start_char=e.start_char, end_char=e.end_char,
            start_token=e.start - sent_start,
            end_token=e.end - sent_start - 1,
        )
        for e in sent.ents
    ]


def _prep_phrase_text(tok: spacy.tokens.Token) -> Optional[str]:
    pobj = next((c for c in tok.children if c.dep_ in ("pobj", "obj")), None)
    if not pobj:
        return None
    return " ".join(t.text for t in sorted(pobj.subtree, key=lambda t: t.i))


def _extract_srl(sent: spacy.tokens.Span) -> List[SemanticRoleOut]:
    frames: List[SemanticRoleOut] = []
    predicates = [t for t in sent
                  if t.pos_ in ("VERB", "AUX") and t.dep_ in ("ROOT", "xcomp", "ccomp", "advcl")]
    for pred in predicates:
        agent = patient = instrument = location = time_arg = manner = purpose = None
        extra: List[str] = []
        for child in pred.children:
            dep = child.dep_
            if dep in ("nsubj", "nsubjpass"):
                agent = " ".join(t.text for t in sorted(child.subtree, key=lambda t: t.i))
            elif dep in ("dobj", "obj", "attr", "oprd"):
                patient = " ".join(t.text for t in sorted(child.subtree, key=lambda t: t.i))
            elif dep in ("prep", "agent"):
                prep = child.text.lower()
                phrase = _prep_phrase_text(child)
                if phrase is None:
                    continue
                full = f"{child.text} {phrase}"
                ent_labels = {t.ent_type_ for t in child.subtree if t.ent_type_}
                if dep == "agent" or prep in ("by", "using", "via") and dep != "agent":
                    if dep == "agent":
                        agent = phrase
                    else:
                        instrument = full
                elif prep in ("with",):
                    instrument = full
                elif prep in ("in", "at", "on", "near", "beside", "inside", "outside", "under", "above", "over", "across", "around"):
                    if ent_labels & {"DATE", "TIME"}:
                        time_arg = full
                    else:
                        location = full
                elif prep in ("since", "after", "before", "during", "until", "while"):
                    time_arg = full
                elif prep in ("for", "to"):
                    purpose = full
                else:
                    extra.append(full)
            elif dep == "advmod":
                manner = child.text
            elif dep not in ("aux", "auxpass", "punct", "cc", "mark", "det", "neg") and not child.is_stop:
                extra.append(child.text)

        frames.append(SemanticRoleOut(
            predicate=pred.text, predicate_lemma=pred.lemma_,
            agent=agent, patient=patient, instrument=instrument,
            location=location, time=time_arg, manner=manner,
            purpose=purpose, extra_args=extra,
        ))
    return frames


def _noun_chunks(sent: spacy.tokens.Span) -> List[NounChunkOut]:
    return [NounChunkOut(
        text=c.text, root_text=c.root.text,
        root_dep=c.root.dep_, root_head_text=c.root.head.text,
    ) for c in sent.noun_chunks]


def _keywords(sent: spacy.tokens.Span, top_n: int = 8) -> List[str]:
    priority = {"NOUN": 4, "PROPN": 4, "VERB": 3, "ADJ": 2, "ADV": 1}
    words = [(t.lemma_.lower(), priority.get(t.pos_, 0))
             for t in sent if not t.is_stop and not t.is_punct and t.pos_ in priority]
    seen: set = set()
    result: List[str] = []
    for w, _ in sorted(words, key=lambda x: -x[1]):
        if w not in seen:
            seen.add(w)
            result.append(w)
        if len(result) >= top_n:
            break
    return result


def _semantic(sent: spacy.tokens.Span, sent_start: int) -> SemanticOut:
    return SemanticOut(
        entities=_extract_entities(sent, sent_start),
        semantic_roles=_extract_srl(sent),
        noun_chunks=_noun_chunks(sent),
        keywords=_keywords(sent),
    )


def _span_text(tokens: List[spacy.tokens.Token]) -> str:
    return " ".join(t.text for t in sorted(tokens, key=lambda t: t.i))


def _build_constituency_tree(sent: spacy.tokens.Span) -> ConstituencyNodeOut:
    root = sent.root

    def mk(label: str, toks: List[spacy.tokens.Token], children: Optional[List[ConstituencyNodeOut]] = None) -> ConstituencyNodeOut:
        return ConstituencyNodeOut(
            label=label,
            text=_span_text(toks),
            children=children or [],
        )

    subj_nodes: List[ConstituencyNodeOut] = []
    vp_parts: List[ConstituencyNodeOut] = []

    for tok in sent:
        if tok.head != root:
            continue
        if tok.dep_ in ("nsubj", "nsubjpass", "csubj"):
            subj_nodes.append(mk("NP", list(tok.subtree)))
        elif tok.dep_ in ("dobj", "obj", "attr", "oprd", "iobj"):
            vp_parts.append(mk("NP", list(tok.subtree)))
        elif tok.dep_ in ("prep",):
            vp_parts.append(mk("PP", list(tok.subtree)))
        elif tok.dep_ in ("advmod", "npadvmod", "advcl"):
            vp_parts.append(mk("ADVP", list(tok.subtree)))

    root_vp_tokens = [t for t in sent if t == root or t.head == root and t.dep_ in ("aux", "auxpass", "neg", "prt")]
    vp_children = [mk("V", [root])] + vp_parts
    vp_node = mk("VP", root_vp_tokens if root_vp_tokens else [root], vp_children)

    sentence_children = subj_nodes + [vp_node] if subj_nodes else [vp_node]
    return mk("S", list(sent), sentence_children)


def analyse_text(text: str) -> AnalyzeResponse:
    doc = nlp(text)
    sentences_out: List[SentenceOut] = []

    for sent_idx, sent in enumerate(doc.sents):
        root = sent.root
        sent_start = sent.start
        tokens_out = [TokenOut(
            index=t.i - sent_start, text=t.text, lemma=t.lemma_,
            pos=t.pos_, tag=t.tag_, dep=t.dep_,
            head_index=t.head.i - sent_start, head_text=t.head.text,
            is_stop=t.is_stop, morph=str(t.morph),
        ) for t in sent]
        subject, predicate, obj, modifiers = _extract_roles(sent)
        sentences_out.append(SentenceOut(
            sentence_index=sent_idx, original=sent.text.strip(),
            root_text=root.text, root_lemma=root.lemma_,
            subject=subject, predicate=predicate, obj=obj,
            modifiers=modifiers, tokens=tokens_out,
            tree=_build_tree(root, sent_start),
            constituency_tree=_build_constituency_tree(sent),
            semantic=_semantic(sent, sent_start),
        ))

    seen: set = set()
    doc_ents: List[EntityOut] = []
    for s in sentences_out:
        for e in s.semantic.entities:
            key = (e.text, e.label)
            if key not in seen:
                seen.add(key)
                doc_ents.append(e)

    return AnalyzeResponse(
        text_length=len(text),
        sentence_count=len(sentences_out),
        token_count=len(doc),
        sentences=sentences_out,
        doc_entities=doc_ents,
    )


def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        return content.decode("utf-8", errors="replace")
    elif ext == ".pdf":
        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            pass
        try:
            from pypdf import PdfReader  # type: ignore
            return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
        except ImportError:
            raise HTTPException(400, "Install pdfplumber or pypdf.")
    elif ext in (".html", ".htm"):
        try:
            from bs4 import BeautifulSoup  # type: ignore
            return BeautifulSoup(content, "html.parser").get_text(separator=" ")
        except ImportError:
            return re.sub(r"<[^>]+>", " ", content.decode("utf-8", errors="replace"))
    elif ext == ".rtf":
        try:
            from striprtf.striprtf import rtf_to_text  # type: ignore
            return rtf_to_text(content.decode("utf-8", errors="replace"))
        except ImportError:
            return re.sub(r"\{[^}]*\}|\\[a-z]+\d*\s?", "", content.decode("utf-8", errors="replace"))
    elif ext in (".docx", ".doc"):
        try:
            import docx  # type: ignore
            return "\n".join(p.text for p in docx.Document(io.BytesIO(content)).paragraphs)
        except ImportError:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if "word/document.xml" in z.namelist():
                    return re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8", errors="replace"))
            raise HTTPException(400, "Install python-docx.")
    return content.decode("utf-8", errors="replace")
