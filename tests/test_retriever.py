"""Unit tests for retrieval functions that don't need a live DB."""
import pytest


def reciprocal_rank_fusion(
    bm25_results: list[dict], dense_results: list[dict], k: int = 60
) -> list[dict]:
    scores: dict[int, float] = {}
    chunks: dict[int, dict] = {}
    for rank, result in enumerate(bm25_results):
        pid = result["pg_chunk_id"]
        scores[pid] = scores.get(pid, 0.0) + 1 / (k + rank + 1)
        chunks[pid] = result
    for rank, result in enumerate(dense_results):
        pid = result["pg_chunk_id"]
        scores[pid] = scores.get(pid, 0.0) + 1 / (k + rank + 1)
        chunks[pid] = result
    ranked_ids = sorted(scores, key=lambda pid: scores[pid], reverse=True)
    return [chunks[pid] for pid in ranked_ids]


def _make_chunk(pg_id: int, doc: str = "directive-071") -> dict:
    return {
        "pg_chunk_id": pg_id,
        "chunk_text": f"chunk {pg_id}",
        "document_name": doc,
        "chunk_index": pg_id,
        "page_number": 1,
    }


class TestReciprocalRankFusion:
    def test_empty_both_lists(self):
        assert reciprocal_rank_fusion([], []) == []

    def test_empty_bm25_returns_dense(self):
        dense = [_make_chunk(1), _make_chunk(2)]
        result = reciprocal_rank_fusion([], dense)
        assert len(result) == 2

    def test_empty_dense_returns_bm25(self):
        bm25 = [_make_chunk(1), _make_chunk(2)]
        result = reciprocal_rank_fusion(bm25, [])
        assert len(result) == 2

    def test_chunk_in_both_lists_ranked_higher(self):
        shared = _make_chunk(1)
        bm25 = [shared, _make_chunk(2), _make_chunk(3)]
        dense = [_make_chunk(4), shared, _make_chunk(5)]
        result = reciprocal_rank_fusion(bm25, dense)
        assert result[0]["pg_chunk_id"] == 1

    def test_no_duplicates_in_output(self):
        chunks = [_make_chunk(i) for i in range(5)]
        result = reciprocal_rank_fusion(chunks, chunks)
        ids = [r["pg_chunk_id"] for r in result]
        assert len(ids) == len(set(ids))

    def test_output_length_equals_union(self):
        bm25 = [_make_chunk(1), _make_chunk(2)]
        dense = [_make_chunk(3), _make_chunk(4)]
        result = reciprocal_rank_fusion(bm25, dense)
        assert len(result) == 4

    def test_overlapping_lists_union_length(self):
        bm25 = [_make_chunk(1), _make_chunk(2), _make_chunk(3)]
        dense = [_make_chunk(2), _make_chunk(3), _make_chunk(4)]
        result = reciprocal_rank_fusion(bm25, dense)
        assert len(result) == 4

    def test_first_rank_gets_higher_score_than_last(self):
        bm25 = [_make_chunk(i) for i in range(10)]
        dense = [_make_chunk(i) for i in range(10)]
        result = reciprocal_rank_fusion(bm25, dense)
        assert result[0]["pg_chunk_id"] == 0

    def test_preserves_chunk_metadata(self):
        chunk = _make_chunk(99, doc="directive-056")
        result = reciprocal_rank_fusion([chunk], [])
        assert result[0]["document_name"] == "directive-056"
        assert result[0]["chunk_text"] == "chunk 99"
        assert result[0]["page_number"] == 1

    def test_single_item_each_list_different_chunks(self):
        result = reciprocal_rank_fusion([_make_chunk(1)], [_make_chunk(2)])
        assert len(result) == 2

    def test_k_parameter_affects_scores_not_order(self):
        bm25 = [_make_chunk(1), _make_chunk(2)]
        dense = [_make_chunk(1), _make_chunk(3)]
        result_default = reciprocal_rank_fusion(bm25, dense)
        result_small_k = reciprocal_rank_fusion(bm25, dense, k=1)
        assert result_default[0]["pg_chunk_id"] == result_small_k[0]["pg_chunk_id"]
