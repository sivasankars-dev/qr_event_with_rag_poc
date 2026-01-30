import os
import chromadb
from chromadb.config import Settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "..", "chroma_data")

chroma_client = chromadb.Client(
    settings=Settings(
        persist_directory=CHROMA_DIR
    )
)

collection = chroma_client.get_or_create_collection(
    name="event_submissions",
)