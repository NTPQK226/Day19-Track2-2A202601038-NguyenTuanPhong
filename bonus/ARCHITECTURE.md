# Hybrid Memory Architecture — Bonus Challenge

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                     │
│                    "Cho tôi đọc gì về AI tiếp theo?"                    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LLM / Response Layer                            │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │  "Bạn thích đọc về AI/ML, đọc 180wpm, gần đây hỏi về        │   │
│   │   Kubernetes → đề xuất: 'Fine-tuning LLM với PyTorch' ..."    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT ASSEMBLY (HybridMemoryAgent)                 │
│                                                                          │
│  ┌──────────────────────┐        ┌──────────────────────┐               │
│  │  Feast Online Store  │        │  Qdrant Vector Store │               │
│  │  (Stable Profile)     │        │  (Episodic Memory)   │               │
│  │                      │        │                      │               │
│  │  • topic_affinity    │        │  • User conversations│               │
│  │  • reading_speed_wpm │        │  • Search history    │               │
│  │  • queries_last_hour │        │  • Document IDs read │               │
│  │  • preferred_language│        │  • Topic preferences │               │
│  └──────────┬───────────┘        └──────────┬───────────┘               │
│             │                                │                           │
│             └──────────┬─────────────────────┘                          │
│                        ▼                                                  │
│              ┌─────────────────────┐                                    │
│              │  Context Assembler   │                                    │
│              │  • Top-3 episodic    │                                    │
│              │  • User profile dict │                                    │
│              │  • Recent activity    │                                    │
│              └─────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## 1. Chunking Strategy — Tradeoff Analysis

### Decision: Semantic Break with 256-token Target Window

**Chosen approach:** Chunk episodic memory at semantic boundaries (sentence-level breaks, paragraph markers) with soft 256-token target. Each chunk = ~1-4 sentences, avg 200 tokens.

```
User: "Tôi muốn tìm hiểu về Kubernetes deployment..."
Assistant: "Kubernetes là..."
User: "Còn Docker thì sao?"
Assistant: "Docker là..."
→ Chunk 1: "Tôi muốn tìm hiểu về Kubernetes deployment..." + response
→ Chunk 2: "Còn Docker thì sao?" + response
```

### Tradeoff Matrix

| Factor | Semantic Break | Per-Message | Per-Conversation |
|--------|---------------|-------------|-------------------|
| Retrieval quality | ★★★★☆ | ★★☆☆☆ | ★★★☆☆ |
| Storage cost | ★★★☆☆ (some redundancy) | ★★★★★ (1 chunk/msg) | ★☆☆☆☆ (huge chunks) |
| Context window fit | ★★★★☆ (tunable) | ★★★★★ (predictable) | ★☆☆☆☆ (overflow risk) |
| Coherence | ★★★★☆ (natural) | ★☆☆☆☆ (fragmented) | ★★★★★ (full context) |

**Why semantic break wins:** Per-message chunks lose conversational coherence (single message rarely stands alone). Per-conversation chunks overflow context windows for power users with 50+ message histories. Semantic breaks balance retrieval granularity with context fit.

---

## 2. Feature Schema — User Profile Design

### Decision: Tabular Features + Tag Embedding (No Latent Embedding Feature)

**Chosen schema:**

```python
# From Feast feature_views.py
user_profile_features:
  entity: user_id (string)
  features:
    - reading_speed_wpm: int      (TTL: 30 days,  source: derived)
    - preferred_language: string   (TTL: 90 days,  source: explicit)
    - topic_affinity: string[]     (TTL: 7 days,   source: derived)
  
query_velocity_features:
  entity: user_id
  features:
    - queries_last_hour: int      (TTL: 1 hour,  source: real-time)
    - distinct_topics_24h: int    (TTL: 1 day,   source: aggregated)
```

### Tabular vs Latent Embedding Tradeoff

| Aspect | Tabular Features | Latent Embedding (Feast EntityEmbedding) |
|--------|-----------------|------------------------------------------|
| Interpretability | ★★★★★ (human-readable) | ★★☆☆☆ (vector, hard to debug) |
| Storage | ★★★★★ (low, just strings/int) | ★★☆☆☆ (768-dim × users = large) |
| Serving latency | ★★★★★ (<1ms, SQLite) | ★★★☆☆ (needs vector lookup) |
| Expressiveness | ★★★☆☆ (fixed schema) | ★★★★★ (captures subtle prefs) |
|冷 Start | ★★★★★ (works with 1 doc) | ★☆☆☆☆ (needs 100+ docs to train) |

**Why tabular wins for this use case:** Our corpus has 10 topics × 100 docs. Topic affinity (categorical) + reading speed (numeric) capture 95% of relevant personalization signals. Latent embeddings add complexity without proportional accuracy gain for a demo-grade system.

---

## 3. Freshness Strategy — When Does "Remember" Reflect Reality?

### Decision: Tiered Freshness by Feature Type

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRESHNESS TIERS                                   │
├──────────────┬──────────────┬───────────────────────────────────────┤
│ Tier 1       │ Sub-second   │ Search queries (queries_last_hour)     │
│ (Streaming)  │ Push API     │ User just searched "Kubernetes" →       │
│              │              │ immediately visible in recall         │
├──────────────┼──────────────┼───────────────────────────────────────┤
│ Tier 2       │ 5-minute     │ Document reads, topic affinity update  │
│ (Near-real) │ Batch refresh │ After reading 3 AI docs → affinity     │
│              │              │ updates within 5 min                   │
├──────────────┼──────────────┼───────────────────────────────────────┤
│ Tier 3       │ Daily        │ Reading speed estimation, language    │
│ (Slow)      │ Nightly job   │ preference — stable, infrequent       │
└──────────────┴──────────────┴───────────────────────────────────────┘
```

### Use Case Comparison

| Use Case | Freshness Needed | Strategy | Rationale |
|----------|-----------------|---------|-----------|
| Breaking news query | Sub-second | Webhook → Qdrant upsert | "Ukraine war" trending → immediate recall |
| E-learning progression | 5-min | Feat. refresh job | Read 3 chapters → update affinity |
| Personality analysis | Daily | Nightly batch | Stable traits, avoid noise |

**Sub-second implementation:** When user performs action X, fire async webhook that upserts to Qdrant immediately. No waiting for next batch cycle.

---

## 4. Rejected Alternative — Why Not Store Episodic in Feast?

**Rejected:** Using Feast EntityEmbedding feature view to store episodic memory as vector embeddings alongside tabular features.

**Reasoning:**

1. **Re-index cycle mismatch:** 
   - Episodic memory: new chunk every user message (potentially 10+/hour)
   - User profile: stable, changes weekly
   - Feast materialization is designed for batch (hourly/daily). Real-time upsert would require custom Push API + bypassing Feast's intended pattern.

2. **TTL mismatch:**
   - Episodic memory: 24-48 hour relevance (recent context matters)
   - Topic affinity: 7-day TTL
   - Feature store TTLs are per-feature, not per-row. Can't have "memory expires faster than preferences."

3. **Query pattern mismatch:**
   - Feast: point lookup by entity key (fast, indexed)
   - Vector search: ANN query by embedding similarity (different access pattern)
   - Mixing in same store creates impedance mismatch.

**Decision:** Keep episodic in Qdrant (optimized for ANN), profile in Feast (optimized for point lookup). This is the "best tool for each job" principle.

---

## 5. Vietnamese-Context Considerations

### Code-Switching Handling (Vi/En Mix)

Vietnamese users commonly mix languages: "tôi muốn deploy Kubernetes trên cloud" (Vi-En-Vi).

**Handling:**
```python
# Strategy: No preprocessing normalization for retrieval
# Store as-is, query as-is
# Rationale: bge-m3 embeddings handle multilingual natively
# If using bge-small-en: preprocess with underthesea word segmentation
```

### Phonetic Typo Tolerance

VN users type by sound: "cong nghe" → "công nghệ", "may ay" → "máy ảy" (machine learning typo).

**Handling:**
- BM25 handles exact matches well
- Vector search with bge-m3 captures semantic similarity even with typos
- Hybrid (RRF) provides fallback: exact typo might match BM25, meaning survives vector

### Tokenizer Choice for Vietnamese

| Tokenizer | Pros | Cons | Recommendation |
|-----------|------|------|----------------|
| Whitespace | No dependency | Treats "công_nghệ" as 1 token | ❌ Poor |
| pyvi | Vietnamese aware | Python 2 era, unmaintained | ⚠️ Legacy |
| underthesea | Active, accurate | Adds dependency | ✅ Recommended |
| bge-m3 tokenizer | Multilingual, built-in | Heavy (3× model size) | ✅ Best if using m3 |

**For this architecture:** Use bge-m3 (full path) or underthesea preprocessing with bge-small-en (lite path). Never whitespace-only.

### Additional VN-Specific Considerations

- **Diacritics normalization:** "công nghệ" vs "cong nghe" → treat as close for semantic search
- **Number formatting:** "1.000.000 đ" vs "1000000đ" → normalize before feature extraction
- **Time expressions:** "hôm qua", "tuần trước" → map to absolute timestamps for PIT join accuracy

---

## Summary

This architecture achieves:

1. **Sub-second recall** for recent activity (Qdrant + real-time upsert)
2. **Interpretable profiles** (tabular Feast features, human-readable)
3. **Robust search** (hybrid BM25+vector handles Vietnamese code-switching)
4. **Vietnamese-aware** (bge-m3 + underthesea preprocessing)

The separation of episodic (Qdrant) and semantic (Feast) memory is not a limitation but a feature — it aligns storage architecture with query access patterns.
