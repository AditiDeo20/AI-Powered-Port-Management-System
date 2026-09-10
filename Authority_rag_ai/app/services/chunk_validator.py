from collections import Counter


class ChunkValidator:

    def __init__(
        self,
        min_words: int = 30,
        max_words: int = 300,
    ):
        self.min_words = min_words
        self.max_words = max_words

    def validate(self, chunks: list[dict]):

        valid_chunks = []
        report = {
            "total_chunks": len(chunks),
            "valid_chunks": 0,
            "empty_chunks": 0,
            "small_chunks": 0,
            "large_chunks": 0,
            "duplicate_chunks": 0,
        }

        seen = Counter()

        for chunk in chunks:

            text = chunk["text"].strip()

            words = text.split()

            word_count = len(words)

            if not text:
                report["empty_chunks"] += 1
                continue

            if word_count < self.min_words:
                report["small_chunks"] += 1
                continue

            if word_count > self.max_words:
                report["large_chunks"] += 1
                continue

            seen[text] += 1

            if seen[text] > 1:
                report["duplicate_chunks"] += 1
                continue

            valid_chunks.append(chunk)

        report["valid_chunks"] = len(valid_chunks)

        return valid_chunks, report