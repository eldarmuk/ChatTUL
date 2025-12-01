from pydantic import BaseModel


class SourceDocument(BaseModel):
    url: str
    timestamp: int
    content: str


class QueryResult(BaseModel):
    url: str
    content: str
    distance: float
