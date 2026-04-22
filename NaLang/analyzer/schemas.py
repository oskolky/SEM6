from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    text: str
    model_config = {"json_schema_extra": {"example": {"text": "Apple is buying a U.K. startup for $1 billion."}}}


class TokenOut(BaseModel):
    index: int
    text: str
    lemma: str
    pos: str
    tag: str
    dep: str
    head_index: int
    head_text: str
    is_stop: bool
    morph: str


class EntityOut(BaseModel):
    text: str
    label: str
    label_desc: str
    start_char: int
    end_char: int
    start_token: int
    end_token: int


class SemanticRoleOut(BaseModel):
    predicate: str
    predicate_lemma: str
    agent: Optional[str]
    patient: Optional[str]
    instrument: Optional[str]
    location: Optional[str]
    time: Optional[str]
    manner: Optional[str]
    purpose: Optional[str]
    extra_args: List[str]


class NounChunkOut(BaseModel):
    text: str
    root_text: str
    root_dep: str
    root_head_text: str


class SemanticOut(BaseModel):
    entities: List[EntityOut]
    semantic_roles: List[SemanticRoleOut]
    noun_chunks: List[NounChunkOut]
    keywords: List[str]


class ConstituencyNodeOut(BaseModel):
    label: str
    text: str
    children: List["ConstituencyNodeOut"] = []


ConstituencyNodeOut.model_rebuild()


class SentenceOut(BaseModel):
    sentence_index: int
    original: str
    root_text: str
    root_lemma: str
    subject: Optional[str]
    predicate: Optional[str]
    obj: Optional[str]
    modifiers: List[str]
    tokens: List[TokenOut]
    tree: Dict[str, Any]
    constituency_tree: ConstituencyNodeOut
    semantic: SemanticOut


class AnalyzeResponse(BaseModel):
    text_length: int
    sentence_count: int
    token_count: int
    sentences: List[SentenceOut]
    doc_entities: List[EntityOut]
