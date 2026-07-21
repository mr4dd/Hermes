from sentence_transformers import SentenceTransformer
import numpy as np

class Helper():
    def __init__(self):
        self.model = SentenceTransformer('all-mpnet-base-v2')

    def generate_embedding(self, description: str) -> bytes:
        # TODO: evaluate better embeddings models, im thinking all-mpnet-base-v2
        vector = self.model.encode(description)
        return vector.astype('float32').tobytes()


    def cosign_similarity_compare(self, embedding: bytes, compare: bytes) -> float:
        left_vector = np.frombuffer(embedding, dtype=np.float32)
        right_vector = np.frombuffer(compare, dtype=np.float32)

        if left_vector.size == 0 or right_vector.size == 0:
            return 0.0

        if left_vector.size != right_vector.size:
            return 0.0

        left_norm = np.linalg.norm(left_vector)
        right_norm = np.linalg.norm(right_vector)

        if left_norm == 0 or right_norm == 0:
            return 0.0

        similarity = np.dot(left_vector, right_vector) / (left_norm * right_norm)
        return float(similarity)
    