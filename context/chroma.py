import chromadb
from chromadb import PersistentClient, Embeddings, Documents
from chromadb.api import ClientAPI

from functools import lru_cache
from sentence_transformers import SentenceTransformer
from transformers import BertTokenizer, AutoTokenizer

from .model import SourceDocument
from . import markdown
# from .markdown import MarkdownSection

SOURCE_DOCUMENTS_COLLECTION = "source_documents"
DOCUMENT_FRAGMENTS_COLLECTION = "document_fragments"


@lru_cache(maxsize=1)
def get_client() -> ClientAPI:
    return PersistentClient(path="./.chroma")


@lru_cache(maxsize=1)
def get_tokenizer() -> BertTokenizer:
    return AutoTokenizer.from_pretrained(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )


class EmbeddingFunction(chromadb.EmbeddingFunction):
    @staticmethod
    @lru_cache(maxsize=1)
    def get_model():
        return SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

    def __call__(self, input: Documents) -> Embeddings:
        model = EmbeddingFunction.get_model()
        return model.encode(input)


def init_collections(client: ClientAPI):
    client.create_collection(SOURCE_DOCUMENTS_COLLECTION, get_or_create=True)
    client.create_collection(
        DOCUMENT_FRAGMENTS_COLLECTION,
        get_or_create=True,
        embedding_function=EmbeddingFunction(),
    )


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


def measure_token_length(text: str) -> int:
    tokenizer = get_tokenizer()
    return len(tokenizer.encode(text))


def chunk_document(client: ClientAPI, document: SourceDocument):
    document_fragments = client.get_collection(DOCUMENT_FRAGMENTS_COLLECTION)
    document_fragments.delete(ids=[document.url])

    meta = {
        "url": document.url,
        "timestamp": document.timestamp,
    }

    sections = markdown.split_by_sections(document.content)
    chunks = [
        chunk
        for section in sections
        for chunk in section.split_into_chunks(
            chunk_size=80, chunk_overlap=50, length_function=measure_token_length
        )
    ]

    BATCH_SIZE = 128

    for idx in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[idx : idx + BATCH_SIZE]
        right_idx = min(idx + BATCH_SIZE, idx + len(batch))

        document_fragments.add(
            # TODO: figure out better method of ids
            ids=[f"{id}:{document.url}" for id in range(idx, right_idx)],
            documents=batch,
            metadatas=[meta] * len(batch),
        )
