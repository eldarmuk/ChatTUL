from pydantic import BaseModel


class SourceDocument(BaseModel):
    url: str | None = None
    timestamp: int
    content: str  # TODO: should this be a list? to accommodate multimodal content...


class QueryResult(BaseModel):
    url: str
    content: str
    distance: float
