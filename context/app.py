from fastapi import FastAPI, HTTPException, Query
from contextlib import asynccontextmanager
from base64 import urlsafe_b64decode, b64decode, b64encode, binascii
from datetime import datetime

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


@app.put("/index/{base64_url}")
def put_source_document(base64_url: str, item: SourceDocument):
    if item.url is not None:
        raise HTTPException(status=400, detail="Unexpected `url` field")

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
    source_documents = db_client.get_collection(chroma.SOURCE_DOCUMENTS_COLLECTION)

    q_result = source_documents.query(
        query_texts=[q], n_results=k, include=["metadatas", "documents", "distances"]
    )
    results: list[QueryResult] = []

    for i in range(len(q_result["documents"][0])):
        document = q_result["documents"][0][i]
        metadata = q_result["metadatas"][0][i]
        distance = q_result["distances"][0][i]

        results.append(
            QueryResult(url=metadata["url"], content=document, distance=distance)
        )
    return results
