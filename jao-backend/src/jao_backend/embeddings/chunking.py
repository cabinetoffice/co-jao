class ChunkingStrategy:
    def chunk(self, embedding_vectors):
        raise NotImplementedError

class MeanStrategy(ChunkingStrategy):
    def chunk(self, embedding_vectors):
        return np.mean(embedding_vectors, axis=0)