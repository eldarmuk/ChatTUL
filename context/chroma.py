from chromadb import PersistentClient, ClientAPI
from functools import lru_cache

from .model import SourceDocument
from . import markdown

SOURCE_DOCUMENTS_COLLECTION = "source_documents"
DOCUMENT_FRAGMENTS_COLLECTION = "document_fragments"


@lru_cache(maxsize=1)
def get_client() -> ClientAPI:
    return PersistentClient(path="./.chroma")


def init_collections(client: ClientAPI):
    client.create_collection(SOURCE_DOCUMENTS_COLLECTION, get_or_create=True)
    client.create_collection(DOCUMENT_FRAGMENTS_COLLECTION, get_or_create=True)


def insert_document(
    client: ClientAPI, document: SourceDocument, overwrite: bool = False
) -> bool:
    source_documents = client.get_collection(SOURCE_DOCUMENTS_COLLECTION)

    results = source_documents.get([document.url], include=[])
    if len(results["ids"]) != 0 and not overwrite:
        return False

    source_documents.upsert(
        ids=[document.url],
        documents=[document.content],
        metadatas=[
            {
                "url": document.url,
                "timestamp": document.timestamp,
            }
        ],
    )

    if len(document.content.rstrip()) != 0:
        chunk_document(client, document)

    return True


def chunk_document(client: ClientAPI, document: SourceDocument):
    document_fragments = client.get_collection(DOCUMENT_FRAGMENTS_COLLECTION)
    document_fragments.delete(ids=[document.url])

    meta = {
        "url": document.url,
        "timestamp": document.timestamp,
    }

    sections = markdown.split_by_sections(document.content)
    document_fragments.add(
        # TODO: figure out better method of ids
        ids=[f"{idx}:{document.url}" for idx in range(len(sections))],
        documents=[str(section) for section in sections],
        metadatas=[meta] * len(sections),
    )
