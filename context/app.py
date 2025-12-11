from contextlib import asynccontextmanager
from base64 import urlsafe_b64decode, b64decode, b64encode
import binascii

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from . import chroma
from .model import SourceDocument, QueryResult

if TYPE_CHECKING:
    import chromadb.api.types as chroma_types

uptime_start = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # preload models
    chroma.get_tokenizer()
    chroma.EmbeddingFunction.get_model()

    chroma.init_collections(chroma.get_client())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def get_root():
    return {"uptime": (datetime.utcnow() - uptime_start).seconds}


class PutSourceDocument(BaseModel):
    content: str
    timestamp: int

    def into_sourcedocument(self, url: str) -> SourceDocument:
        return SourceDocument(
            url=url,
            timestamp=self.timestamp,
            content=self.content,
        )


@app.put("/index/{base64_url}")
async def put_source_document(base64_url: str, item: PutSourceDocument):
    try:
        url = urlsafe_b64decode(base64_url).decode("utf-8")
    except binascii.Error | UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Bad url path parameter")

    try:
        item.content = b64decode(item.content).decode("utf-8")
    except binascii.Error | UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Could not decode content: {e}")

    db_client = chroma.get_client()
    chroma.insert_document(db_client, item.into_sourcedocument(url), overwrite=True)


# TODO: Refactor this method to only return document metadata
@app.get("/index/{base64_url}")
def get_source_document(base64_url: str, no_content: bool = False) -> SourceDocument:
    try:
        url = urlsafe_b64decode(base64_url).decode("utf-8")
    except binascii.Error | UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Bad url path parameter")

    include: chroma_types.Include = ["metadatas"]
    if not no_content:
        include.append("documents")

    db_client = chroma.get_client()
    source_documents = db_client.get_collection(chroma.SOURCE_DOCUMENTS_COLLECTION)
    result = source_documents.get(where={"url": {"$eq": url}}, limit=1, include=include)

    if len(result["ids"]) == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    if TYPE_CHECKING:
        assert result["metadatas"] is not None

    metadata = result["metadatas"][0]
    content = ""

    if not no_content:
        if TYPE_CHECKING:
            assert result["documents"] is not None

        document: str = result["documents"][0]
        content = b64encode(document.encode("utf-8")).decode("utf-8")

    return SourceDocument(
        url=metadata["url"],
        timestamp=metadata["timestamp"],
        content=content,
    )


@app.get("/search")
def get_relevant_fragments(
    q: str, k: int = Query(10, gt=0, lt=100)
) -> list[QueryResult]:
    db_client = chroma.get_client()
    document_fragments = db_client.get_collection(chroma.DOCUMENT_FRAGMENTS_COLLECTION)

    q_result = document_fragments.query(
        query_texts=[q], n_results=k, include=["metadatas", "documents", "distances"]
    )

    if TYPE_CHECKING:
        assert q_result["documents"] is not None
        assert q_result["metadatas"] is not None
        assert q_result["distances"] is not None

    results: list[QueryResult] = []
    items = zip(
        q_result["documents"][0],
        q_result["metadatas"][0],
        q_result["distances"][0],
    )

    for item in items:
        results.append(
            QueryResult(
                content=item[0],
                url=item[1]["url"],
                distance=item[2],
            )
        )
    return results
