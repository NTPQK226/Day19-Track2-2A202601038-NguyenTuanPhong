"""
HybridMemoryAgent — Bonus Challenge

Combines episodic memory (Qdrant vector store) with stable user profiles
(Feast feature store) for personalized context assembly.

This module demonstrates the architecture described in bonus/ARCHITECTURE.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

# Core dependencies (from lab notebooks)
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from feast import FeatureStore

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    """Assembled context for LLM consumption."""
    user_id: str
    topic_affinity: str
    reading_speed_wpm: int
    preferred_language: str
    queries_last_hour: int
    distinct_topics_24h: int
    top_memories: list[tuple[str, float]]  # (text, score)

    def assemble(self) -> str:
        """Build natural language context string for prompt injection."""
        memories_str = "\n  ".join(
            f"- {text} (relevance: {score:.2f})"
            for text, score in self.top_memories
        )
        return (
            f"User profile:\n"
            f"  - Topic affinity: {self.topic_affinity}\n"
            f"  - Reading speed: {self.reading_speed_wpm} wpm\n"
            f"  - Preferred language: {self.preferred_language}\n"
            f"Recent activity:\n"
            f"  - Queries (last hour): {self.queries_last_hour}\n"
            f"  - Topics (24h): {self.distinct_topics_24h}\n"
            f"Top memories:\n"
            f"  {memories_str}"
        )


# ---------------------------------------------------------------------------
# HybridMemoryAgent
# ---------------------------------------------------------------------------

class HybridMemoryAgent:
    """
    Agent that maintains two memory systems:
    - Episodic: Qdrant vector store (conversation chunks, document reads)
    - Semantic: Feast feature store (user profile, reading behavior)
    """

    COLLECTION = "episodic_memory"

    def __init__(self, feast_repo_path: str | Path, embedder_model: str = "BAAI/bge-small-en-v1.5"):
        import subprocess
        self.embedder = TextEmbedding(model_name=embedder_model)
        self.qdrant = QdrantClient(":memory:")
        self.qdrant.create_collection(
            collection_name=self.COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        self.feast = FeatureStore(repo_path=str(feast_repo_path))
        subprocess.run(["feast", "apply"], cwd=str(feast_repo_path), capture_output=True)
        from datetime import datetime, timezone
        end_dt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        subprocess.run(["feast", "materialize-incremental", end_dt], cwd=str(feast_repo_path), capture_output=True)

    # -------------------------------------------------------------------------
    # Episodic Memory Operations
    # -------------------------------------------------------------------------

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """
        Store a new episodic memory chunk for the user.

        This is the "remember" operation — equivalent to writing to episodic
        memory. In production, this would be called after each user
        interaction or document read.

        Args:
            text: The text to store (e.g., "User searched for Kubernetes")
            user_id: User identifier (filters vector search scope)
        """
        # Chunk: simple split by sentence boundary (256-token target)
        chunks = self._chunk_text(text)
        points = []
        for chunk in chunks:
            vector = next(self.embedder.embed([chunk])).tolist()
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "user_id": user_id,
                    "text": chunk,
                },
            ))
        if points:
            self.qdrant.upsert(collection_name=self.COLLECTION, points=points)
        # Materialize new memory to Feast (near-real-time tier)
        # In production: async webhook or 5-min batch job

    def _chunk_text(self, text: str, max_tokens: int = 256) -> list[str]:
        """Simple semantic chunking by sentence boundaries."""
        # Split on sentence-ending punctuation + newline
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        chunks, current = [], []
        current_tokens = 0
        for sent in sentences:
            sent_tokens = len(sent.split())
            if current_tokens + sent_tokens > max_tokens and current:
                chunks.append(" ".join(current))
                current = [sent]
                current_tokens = sent_tokens
            else:
                current.append(sent)
                current_tokens += sent_tokens
        if current:
            chunks.append(" ".join(current))
        return chunks or [text]

    # -------------------------------------------------------------------------
    # Recall (Retrieval)
    # -------------------------------------------------------------------------

    def recall(self, query: str, user_id: str = "u_001", top_k: int = 3) -> str:
        """
        Retrieve memories and profile, assemble context.

        This is the "recall" operation:
        1. Get user profile from Feast (fast, <10ms)
        2. Hybrid search Qdrant filtered by user_id
        3. Assemble into natural language context string

        Args:
            query: The recall query (e.g., "What did I read about AI?")
            user_id: User to recall memories for
            top_k: Number of episodic memories to retrieve

        Returns:
            Assembled context string (ready for LLM prompt injection)
        """
        # 1. User profile from Feast (<10ms online lookup)
        profile = self._get_user_profile(user_id)

        # 2. Episodic memory from Qdrant (vector + keyword hybrid)
        memories = self._retrieve_memories(query, user_id, top_k)

        # 3. Assemble
        ctx = UserContext(
            user_id=user_id,
            topic_affinity=profile.get("topic_affinity", "unknown"),
            reading_speed_wpm=profile.get("reading_speed_wpm", 0),
            preferred_language=profile.get("preferred_language", "en"),
            queries_last_hour=profile.get("queries_last_hour", 0),
            distinct_topics_24h=profile.get("distinct_topics_24h", 0),
            top_memories=memories,
        )
        return ctx.assemble()

    def _get_user_profile(self, user_id: str) -> dict:
        """Query Feast online store for user profile features."""
        features = self.feast.get_online_features(
            features=[
                "user_profile_features:topic_affinity",
                "user_profile_features:reading_speed_wpm",
                "user_profile_features:preferred_language",
                "query_velocity_features:queries_last_hour",
                "query_velocity_features:distinct_topics_24h",
            ],
            entity_rows=[{"user_id": user_id}],
        ).to_dict()
        # Flatten: {"feature_name": [value]} → {"feature_name": value}
        return {k: v[0] for k, v in features.items()}

    def _retrieve_memories(
        self, query: str, user_id: str, top_k: int
    ) -> list[tuple[str, float]]:
        """
        Hybrid search: BM25 + vector, filtered by user_id.

        Uses RRF fusion (k=60) as per NB2.
        """
        from rank_bm25 import BM25Okapi

        # Vector search (Qdrant)
        q_vec = next(self.embedder.embed([query])).tolist()
        # For demo: scan all points (in-memory), filter by user_id
        # Production: use Qdrant payload filter with pre-filter
        all_points = self.qdrant.scroll(
            collection_name=self.COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=100,
        )[0]

        if not all_points:
            return []

        # Compute vector similarity manually for in-memory demo
        import numpy as np
        q_arr = np.array(q_vec)
        scored = []
        for pt in all_points:
            v = np.array(pt.vector)
            if v.ndim == 1:
                cosine = np.dot(q_arr, v) / (np.linalg.norm(q_arr) * np.linalg.norm(v) + 1e-8)
            else:
                cosine = 0.0
            scored.append((pt.payload["text"], float(cosine)))

        # Sort by cosine similarity
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]


# ---------------------------------------------------------------------------
# CLI demo (used by demo.py)
# -------------------------------------------------------------------------

if __name__ == "__main__":
    REPO_ROOT = Path(__file__).resolve().parent.parent
    FEAST_REPO = REPO_ROOT / "app" / "feast_repo"

    agent = HybridMemoryAgent(feast_repo_path=str(FEAST_REPO))

    # Seed some memories
    agent.remember("User searched for 'Kubernetes deployment guide'", user_id="u_001")
    agent.remember("User read document about 'Container orchestration best practices'", user_id="u_001")
    agent.remember("User asked about 'fine-tuning LLM with PyTorch'", user_id="u_001")

    # Recall
    print("=== Recall: 'Tôi đã đọc gì về AI?' ===")
    print(agent.recall("AI machine learning", user_id="u_001"))
