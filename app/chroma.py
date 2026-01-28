import chromadb
from chromadb.config import Settings

chroma_client = chromadb.Client(
    settings=Settings(
        persist_directory="./chroma_data"
    )
)

collection = chroma_client.get_or_create_collection(
    name="event_submissions",
)