# Day 19 Lab — Self-Grading Rubric

**Họ Tên:** Nguyễn Tuấn Phong | **MSSV:** 2A202601038 | **Path:** Lite

---

## Core — NB1–NB4 (100 pts)

| # | Tiêu chí | Pts tối đa | Tự chấm | Ghi chú |
|---|----------|------------|---------|---------|
| 1 | NB1: `client.count("lab19").count == 1000` | 5 | **5** | ✅ |
| 1 | NB1: Top-5 results visible (cell §5) | 5 | **5** | ✅ |
| 1 | NB1: Paraphrase query → `cloud` cluster | 10 | **10** | ✅ |
| 2 | NB2: `search_hybrid` RRF formula đúng `1/(k+rank)`, rank 1-based | 10 | **10** | ✅ |
| 2 | NB2: Precision@10: hybrid > kw AND hybrid > sem | 10 | **10** | ✅ |
| 2 | NB2: Slice table: hybrid wins `mixed`, vector wins `paraphrase`, BM25 wins `exact` | 5 | **5** | ✅ |
| 3 | NB3: API trả `SearchResponse` với `latency_ms` | 5 | **5** | ✅ |
| 3 | NB3: Bảng P50/P95/P99 server-side cho 3 modes | 10 | **10** | ✅ |
| 3 | NB3: Hybrid P99 < 50ms sau warm-up | 10 | **10** | ✅ (5.8ms) |
| 4 | NB4: `feast apply` — 3 feature views registered | 5 | **5** | ✅ |
| 4 | NB4: `materialize-incremental` — rows materialized | 5 | **5** | ✅ |
| 4 | NB4: `get_online_features()` cho `u_001` | 5 | **5** | ✅ |
| 4 | NB4: 100-call P99 reported | 5 | **5** | ✅ |
| 4 | NB4: PIT join trả về 3 rows × N features | 5 | **5** | ✅ |
| — | Reproducible: `make benchmark` chạy được | 5 | **5** | ✅ |
| | **Core total** | **100** | **100** | |

---

## Advanced — NB5–NB8 (50 pts)

| # | Tiêu chí | Pts tối đa | Tự chấm | Ghi chú |
|---|----------|------------|---------|---------|
| 5 | NB5: post-filter giảm recall, filtered-ANN giữ 1.00 | 5 | **5** | ✅ |
| 5 | NB5: `fetch_k` ≈ 50% corpus mới cứu recall | 5 | **5** | ✅ |
| 6 | NB6: 3 chiến lược cùng 16 doc; agentic > single-shot | 5 | **5** | ✅ |
| 6 | NB6: Giải thích `agentic (+filter)` < `agentic (no filter)` | 4 | **4** | ✅ |
| 6 | NB6: `build_context()` in feature + doc_ids | 3 | **3** | ✅ |
| 7 | NB7: Bảng sweep: tiết kiệm + trả lời sai | 5 | **5** | ✅ |
| 7 | NB7: Chọn ngưỡng + giải thích 0.75 chưa đủ | 4 | **4** | ✅ |
| 7 | NB7: Tenant leak: leak khi `False`, MISS khi `True` | 3 | **3** | ✅ |
| 8 | NB8: Leakage gap > 0.30 trên `session_id` | 4 | **4** | ✅ (gap 0.477) |
| 8 | NB8: PIT vs latest: % dòng rò + AUC diff | 4 | **4** | ✅ |
| 8 | NB8: ODFV: cùng user, hai amount → hai ratio | 4 | **4** | ✅ |
| 8 | `make test` và `make verify-lite` xanh | 4 | **4** | ✅ |
| | **Advanced total** | **50** | **50** | |

---

## Bonus (20 pts)

| Tiêu chí | Pts tối đa | Tự chấm | Ghi chú |
|----------|------------|---------|---------|
| `bonus/ARCHITECTURE.md` ≥600 words + diagram | 3 | **3** | ✅ |
| 3 decisions với explicit tradeoff | 6 | **6** | ✅ |
| Vietnamese-context awareness | 2 | **2** | ✅ |
| Rejected alternative với reason | 2 | **2** | ✅ |
| `bonus/agent.py` chạy được | 4 | **4** | ✅ |
| `bonus/demo.py` exits 0 + 5 queries | 3 | **3** | ✅ |
| **Bonus total** | **20** | **20** | |

---

## Tổng kết

| Phần | Tối đa | Đạt |
|------|---------|------|
| Core (NB1–NB4) | 100 | **100** |
| Advanced (NB5–NB8) | 50 | **50** |
| Bonus | 20 | **20** |
| **Tổng** | **170** | **170** |

---

## Screenshots

| Notebook | Screenshot |
|----------|------------|
| NB1 — Embeddings | ![NB1](screenshots/NB1.png) |
| NB2 — Hybrid Search | ![NB2](screenshots/NB2.png) |
| NB3 — API Benchmark | ![NB3](screenshots/NB3.png) |
| NB4 — Feast | ![NB4](screenshots/NB4.png) |
| NB5 — Filtered Search | ![NB5](screenshots/NB5.png) |
| NB6 — Agent | ![NB6](screenshots/NB6.png) |
| NB7 — Cache | ![NB7](screenshots/NB7.png) |
| NB8 — Features | ![NB8](screenshots/NB8.png) |
| `make benchmark` | ![benchmark](screenshots/make%20benchmark.png) |
| `make test` | ![test](screenshots/make%20test.png) |
