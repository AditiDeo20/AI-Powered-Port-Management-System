try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

import hashlib
import numpy as np


import os
from pathlib import Path

class EmbeddingService:

    def __init__(self):
        self.use_flag = False
        self.use_fallback = True

        # Fast check: Only attempt loading FlagEmbedding if explicitly enabled via USE_REAL_BGE=1
        use_real_bge = os.environ.get("USE_REAL_BGE", "0") == "1"
        hf_cache = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface/hub"))
        has_cached = False
        try:
            if os.path.exists(hf_cache):
                has_cached = any("bge-m3" in str(p).lower() for p in Path(hf_cache).glob("**/*") if p.is_file())
        except Exception:
            has_cached = False

        if use_real_bge and has_cached and TORCH_AVAILABLE:
            try:
                from FlagEmbedding import BGEM3FlagModel
                self.model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
                self.use_flag = True
                self.use_fallback = False
                print("[EmbeddingService] BGE-M3 model loaded from local cache.")
            except Exception as e:
                print(f"[EmbeddingService] Local FlagEmbedding load error ({e}). Using deterministic vector fallback.")
                self.use_fallback = True
        else:
            print("[EmbeddingService] Using fast 1024-dim deterministic vector fallback (no blocking internet download).")
            self.use_fallback = True


    def _hash_vector(self, text: str, dim: int = 1024) -> list[float]:
        """Generates a deterministic 1024-dimensional normalized float vector for text."""
        seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        seed_int = int.from_bytes(seed_bytes[:4], "big")
        rng = np.random.RandomState(seed_int)
        vec = rng.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def _embed_transformers(self, texts: list[str]):
        inputs = self.tokenizer(texts, padding=True, truncation=True, max_length=1024, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
            # CLS pooling + normalization (standard for BGE-M3 dense vectors)
            embeddings = outputs[0][:, 0]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            return embeddings.cpu().numpy().tolist()

    def embed_text(self, text: str):
        if self.use_fallback:
            return self._hash_vector(text)
        elif self.use_flag:
            result = self.model.encode(
                [text],
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False
            )
            return result["dense_vecs"][0].tolist()
        else:
            return self._embed_transformers([text])[0]

    def embed_chunks(self, chunks: list[dict], batch_size: int = 16, status_dict: dict = None):
        total_chunks = len(chunks)
        print(f"[EmbeddingService] Starting vector embedding generation for {total_chunks} chunks (batch_size={batch_size})...")
        
        all_vectors = []
        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk["text"] for chunk in batch_chunks]
            batch_num = (i // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            print(f"[EmbeddingService] Processing batch {batch_num}/{total_batches} ({len(batch_texts)} chunks, indices {i+1}-{min(i+batch_size, total_chunks)})...")

            if self.use_fallback:
                batch_vectors = [self._hash_vector(t) for t in batch_texts]
            elif self.use_flag:
                result = self.model.encode(
                    batch_texts,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False
                )
                batch_vectors = result["dense_vecs"]
            else:
                batch_vectors = self._embed_transformers(batch_texts)

            if hasattr(batch_vectors, "tolist"):
                batch_vectors = batch_vectors.tolist()

            all_vectors.extend(batch_vectors)

            processed_count = min(i + batch_size, total_chunks)
            print(f"[EmbeddingService] Completed batch {batch_num}/{total_batches} ({processed_count}/{total_chunks} chunks embedded).")

            if status_dict is not None:
                pct = 70 + int(20 * (processed_count / total_chunks))
                status_dict.update({
                    "step": f"Embedding chunks ({processed_count}/{total_chunks})...",
                    "progress": pct
                })

        embedded_chunks = []
        for chunk, vector in zip(chunks, all_vectors):
            chunk["embedding"] = vector if isinstance(vector, list) else vector.tolist()
            embedded_chunks.append(chunk)

        print(f"[EmbeddingService] Successfully generated embeddings for all {len(embedded_chunks)} chunks.")
        return embedded_chunks