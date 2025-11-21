from chromadb import PersistentClient, ClientAPI

SOURCE_DOCUMENTS_COLLECTION = "source_documents"
_client: ClientAPI | None = None


def get_client() -> ClientAPI:
    global _client

    if _client is None:
        _client = PersistentClient(path="./.chroma")

    return _client


def init_collections(client: ClientAPI):
    client.create_collection(SOURCE_DOCUMENTS_COLLECTION, get_or_create=True)
