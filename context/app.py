from contextlib import asynccontextmanager
from base64 import urlsafe_b64decode, b64decode, b64encode, binascii
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from . import chroma
from .model import SourceDocument, QueryResult


uptime_start = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
            url=self.url,
            timestamp=self.timestamp,
            lang=self.lang,
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
        raise HTTPException(
            status_code=400, detail=f"Could not decode content: {e.reason}"
        )

    db_client = chroma.get_client()
    chroma.insert_document(db_client, item.into_sourcedocument(url), overwrite=True)


@app.get("/index/{base64_url}")
def get_source_document(base64_url: str, no_content: bool = False) -> SourceDocument:
    try:
        url = urlsafe_b64decode(base64_url).decode("utf-8")
    except binascii.Error | UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Bad url path parameter")

    include = ["metadatas"]
    if not no_content:
        include.append("documents")

    db_client = chroma.get_client()
    source_documents = db_client.get_collection(chroma.SOURCE_DOCUMENTS_COLLECTION)
    result = source_documents.get(where={"url": {"$eq": url}}, limit=1, include=include)
    if len(result["metadatas"]) == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    metadata: dict = result["metadatas"][0]

    if no_content:
        content = ""
    else:
        document: str = result["documents"][0]
        content = b64encode(document.encode("utf-8")).decode("utf-8")

    return SourceDocument(
        url=metadata["url"],
        timestamp=metadata["timestamp"],
        content=content,
    )


@app.get("/search")
def get_relevant_fragments(q: str, k: int = Query(10, gt=0)) -> list[QueryResult]:
    db_client = chroma.get_client()
    document_fragments = db_client.get_collection(chroma.DOCUMENT_FRAGMENTS_COLLECTION)

    q_result = document_fragments.query(
        query_texts=[q], n_results=k, include=["metadatas", "documents", "distances"]
    )

    # NOTE: the following fields were supposed to be retuned
    # by ChromaDB, the assertions should never trigger
    #
    # The assertions are information for the type checker
    assert q_result["documents"] is not None
    assert q_result["metadatas"] is not None
    assert q_result["distances"] is not None

    results: list[QueryResult] = []

    for i in range(len(q_result["documents"][0])):
        document = q_result["documents"][0][i]
        metadata = q_result["metadatas"][0][i]
        distance = q_result["distances"][0][i]

        results.append(
            QueryResult(
                url=metadata["url"],
                content=document,
                distance=distance,
            )
        )
    return results
