from pydantic import BaseModel


class PutSourceDocumentModel(BaseModel):
    timestamp: int
    content: str


class SourceDocument(BaseModel):
    url: str
    timestamp: int
    content: str  # TODO: should this be a list? to accommodate multimodal content...


class QueryResult(BaseModel):
    url: str
    content: str
    distance: float
