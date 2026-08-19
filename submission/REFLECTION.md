# Reflection — Lab 19

**Tên:** Nguyễn Tuấn Phong
**MSSV:** 2A202601038
**Cohort:** K3B
**Lớp:** E403
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

**Hybrid thắng trung bình** (78.6% Precision@10) nhờ robust trên mọi loại query:
- `exact`: BM25 thắng — khi query chứa từ verbatim trong corpus, term frequency × IDF cho score cao
- `paraphrase`: Semantic thắng — vector embedding bắt semantic similarity dù không có từ chung
- `mixed` (user thật): **Hybrid thắng rõ** — RRF k=60 cộng điểm từ cả hai retrievers

**Không dùng hybrid khi:**
1. **Latency <10ms SLA** — hybrid cần 2 searches sequential, double latency
2. **Corpus ngắn, vocabulary diverse** — BM25 noise, dùng pure semantic
3. **Memory constraints** — duy trì 2 indexes tốn gấp đôi storage
4. **Streaming ingestion** — BM25 rebuild đắt, vector hỗ trợ incremental upsert tốt hơn

---

## Điều ngạc nhiên nhất khi làm lab này

Hybrid dù chỉ thắng hybrid trên "mixed" nhưng vẫn là lựa chọn production đúng vì user thật hiếm khi viết query 100% exact hoặc 100% paraphrase — họ mix cả hai, và hybrid xử lý tốt nhất pattern đó.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<tên đồng đội nếu có>_
