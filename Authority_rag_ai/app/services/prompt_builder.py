class PromptBuilder:

    def build(self, question, retrieved_chunks):

        context = ""

        for index, chunk in enumerate(retrieved_chunks, start=1):

            chunk_text = chunk.get("child_text") or chunk.get("text") or chunk.get("parent_text", "")

            context += (
                f"Chunk {index}\n"
                f"{chunk_text}\n\n"
            )

        prompt = f"""
You are an AI assistant for the Port Land Management System.

Use ONLY the information provided in the context below.

If the answer is not available in the context, reply exactly:

"I could not find the answer in the provided documents."

Context
-------
{context}

Question
--------
{question}

Answer
------
"""

        return prompt