#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo.py — Bonus Challenge: 5-Query Hybrid Memory Demo

Run: python bonus/demo.py

This script demonstrates the HybridMemoryAgent from bonus/agent.py
with 5 representative queries covering different retrieval scenarios.
"""

import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from bonus.agent import HybridMemoryAgent

# ---------------------------------------------------------------------------
# Initialize agent
# ---------------------------------------------------------------------------

FEAST_REPO = REPO_ROOT / "app" / "feast_repo"
print("Initializing HybridMemoryAgent...")
agent = HybridMemoryAgent(feast_repo_path=str(FEAST_REPO))

# Seed episodic memories for demo user
print("Seeding episodic memories for u_001...\n")
agent.remember("User searched: 'Kubernetes deployment on cloud'", user_id="u_001")
agent.remember("User read: 'Docker container best practices — security hardening'", user_id="u_001")
agent.remember("User asked: 'How does RRF fusion work in hybrid search?'", user_id="u_001")
agent.remember("User read: 'Fine-tuning LLM with PyTorch — step by step'", user_id="u_001")
agent.remember("User searched: 'Vietnamese NLP with underthesea tokenizer'", user_id="u_001")
agent.remember("User asked: 'What is the difference between BM25 and dense vectors?'", user_id="u_001")
agent.remember("User read: 'Cloud security — IAM policies and least privilege'", user_id="u_001")

# ---------------------------------------------------------------------------
# Demo queries
# ---------------------------------------------------------------------------

QUERIES = [
    {
        "num": 1,
        "query": "Tôi đã đọc gì về Kubernetes?",
        "description": "Hỏi đơn giản — chỉ cần vector hit",
        "expected": "Vector search trả về doc liên quan Kubernetes",
    },
    {
        "num": 2,
        "query": "Recommend đọc gì tiếp",
        "description": "Cần profile context — topic_affinity từ Feast",
        "expected": "Profile cho thấy user thích AI/ML topic, gợi ý docs phù hợp",
    },
    {
        "num": 3,
        "query": "Tôi đang quan tâm gì gần đây?",
        "description": "Cần fresh activity — queries_last_hour từ Feast",
        "expected": "Tính năng velocity cho thấy activity patterns",
    },
    {
        "num": 4,
        "query": "Tài liệu về tự động mở rộng hạ tầng?",
        "description": "Paraphrase query — vector semantic thắng",
        "expected": "Không có từ 'cloud' nhưng vector tìm được đúng cluster",
    },
    {
        "num": 5,
        "query": "Cho tôi summary cloud security",
        "description": "Mixed — cần cả episodic + profile",
        "expected": "Gợi ý cloud security docs dựa trên cả memory lẫn profile",
    },
]

# ---------------------------------------------------------------------------
# Run demo
# ---------------------------------------------------------------------------

print("=" * 70)
print("BONUS DEMO: HybridMemoryAgent — 5-Query Showcase")
print("=" * 70)

for q in QUERIES:
    print(f"\n{'─' * 70}")
    print(f"QUERY {q['num']}: {q['query']}")
    print(f"Type: {q['description']}")
    print(f"Expected: {q['expected']}")
    print(f"{'─' * 70}")
    result = agent.recall(query=q["query"], user_id="u_001", top_k=3)
    print(result)
    print()

print("=" * 70)
print("Demo complete. Exit code: 0")
print("=" * 70)
sys.exit(0)
