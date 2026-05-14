"""Minimal stub for fastembed to allow tests to collect."""

class TextEmbedding:
    def __init__(self, *args, **kwargs):
        pass
    def embed(self, texts, batch_size=1):
        import numpy as np
        for text in texts:
            yield np.zeros(768, dtype=np.float32)

class SparseTextEmbedding:
    def __init__(self, *args, **kwargs):
        pass
    def embed(self, texts, batch_size=1):
        import numpy as np
        for text in texts:
            yield type('SparseVector', (), {'indices': np.array([0,1,2], dtype=np.int32), 'values': np.array([0.1,0.2,0.3], dtype=np.float32)})
    def query_embed(self, text):
        import numpy as np
        yield type('SparseVector', (), {'indices': np.array([0,1,2], dtype=np.int32), 'values': np.array([0.1,0.2,0.3], dtype=np.float32)})
