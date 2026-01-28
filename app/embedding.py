import numpy as np
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("API_KEY"))

def generate_embedding(text: str):
    response = client.embeddings.create(
        input=[text.replace("\n", " ")],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# def cosine_similarity(vec1, vec2):
#     dot_product = np.dot(vec1, vec2)
#     norm_vec1 = np.linalg.norm(vec1)
#     norm_vec2 = np.linalg.norm(vec2)
#     if norm_vec1 == 0 or norm_vec2 == 0:
#         return 0.0
#     return dot_product / (norm_vec1 * norm_vec2)
