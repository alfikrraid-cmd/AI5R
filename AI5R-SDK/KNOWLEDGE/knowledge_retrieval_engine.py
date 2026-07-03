from typing import List, Dict, Any

from .knowledge_chunking_engine import KnowledgeChunk


class KnowledgeRetrievalEngine:
    def score(self, chunk: KnowledgeChunk, query: str) -> int:
        query_terms = [
            term.lower()
            for term in query.split()
            if term.strip()
        ]

        content = chunk.content.lower()
        score = 0

        for term in query_terms:
            if term in content:
                score += 1

        return score

    def search(
        self,
        chunks: List[KnowledgeChunk],
        organization_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        results = []

        for chunk in chunks:
            if chunk.organization_id != organization_id:
                continue

            score = self.score(chunk, query)

            if score > 0:
                results.append({
                    "score": score,
                    "chunk": chunk,
                })

        results.sort(key=lambda item: item["score"], reverse=True)

        return results[:limit]
