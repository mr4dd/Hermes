from sentence_transformers import SentenceTransformer
import numpy as np

def generate_embedding(description: str) -> bytes:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    vector = model.encode(description)
    return vector.astype('float32').tobytes()
