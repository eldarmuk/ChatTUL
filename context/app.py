from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from contextlib import asynccontextmanager
from base64 import b64decode, b64encode, binascii
from datetime import datetime

from . import chroma


class SourceDocument(BaseModel):
    url: str | None
    timestamp: int
    content: str  # TODO: should this be a list? to accommodate multimodal content...


class QueryResult(BaseModel):
    url: str
    content: str
    distance: float


uptime_start = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    chroma.init_collections(chroma.get_client())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def get_root():
    return {"uptime": (datetime.utcnow() - uptime_start).seconds}


@app.put("/index/{base64_url}")
def put_source_document(base64_url: str, item: SourceDocument):
    try:
        url = b64decode(base64_url).decode("utf-8")
    except binascii.Error | UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Bad url path parameter")

    try:
        item.content = b64decode(item.content)
    except binascii.Error as e:
        raise HTTPException(status_code=400, detail=f"Could not decode content: {e}")

    if item.url != url:
        raise HTTPException(
            status_code=400,
            detail="url path parameter and url of document to be inserted don't match",
        )

    # TODO: chunk documents
    db_client = chroma.get_client()
    source_documents = db_client.get_collection(chroma.SOURCE_DOCUMENTS_COLLECTION)
    source_documents.add(
        ids=[url],  # TODO: make this more smarter
        documents=[item.content],
        metadatas=[
            {
                "url": url,
                "timestamp": item.timestamp,
            }
        ],
    )
    pass


@app.get("/index/{base64_url}")
def get_source_document(base64_url: str) -> SourceDocument:
    try:
        url = b64decode(base64_url).decode("utf-8")
    except binascii.Error | UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Bad url path parameter")

    db_client = chroma.get_client()
    source_documents = db_client.get_collection(chroma.SOURCE_DOCUMENTS_COLLECTION)
    result = source_documents.get(where={"url": {"$eq": url}}, limit=1)
    if len(result["documents"]) == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    document: str = result["documents"][0]
    metadata: dict = result["metadata"][0]
    return SourceDocument(
        url=metadata["url"],
        timestamp=metadata["timestamp"],
        content=b64encode(document.encode("utf-8").decode("utf-8")),
    )


@app.get("/search")
def get_relevant_fragments(q: str, k: int = Query(10, gt=0)) -> list[QueryResult]:
    db_client = chroma.get_client()
    source_documents = db_client.get_collection(chroma.SOURCE_DOCUMENTS_COLLECTION)

    q_result = source_documents.query(
        query_texts=[q], n_results=k, include=["metadatas", "documents", "distances"]
    )
    results: list[QueryResult] = []

    for i in range(len(q_result["documents"])):
        document = q_result["documents"][i]
        metadata = q_result["metadatas"][i]
        distance = q_result["distances"][i]

        results.append(
            QueryResult(url=metadata["url"], content=document, distance=distance)
        )
    return results
