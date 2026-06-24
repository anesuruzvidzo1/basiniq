"""
Retrieval evaluation for BasinIQ hybrid search.

Metrics computed:
  Recall@5  — did any relevant chunk appear in the top 5 results?
  MRR       — mean reciprocal rank of the first relevant result
  NDCG@5    — normalised discounted cumulative gain at rank 5

Run with:  python eval.py
Requires the DATABASE_URL env var and a running PostgreSQL instance with
document_chunks populated (i.e. after auto-setup completes).
"""

import asyncio
import math
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder
from retriever import hybrid_search

load_dotenv()

EVAL_QUERIES = [
    {
        "query": "H2S emergency planning requirements",
        "relevant_docs": ["directive-071"],
    },
    {
        "query": "flaring restrictions upstream petroleum",
        "relevant_docs": ["directive-060", "Directive001"],
    },
    {
        "query": "noise control requirements near residences",
        "relevant_docs": ["directive-038"],
    },
    {
        "query": "drilling waste management disposal",
        "relevant_docs": ["directive-050"],
    },
    {
        "query": "oilfield waste management facilities",
        "relevant_docs": ["directive-047"],
    },
    {
        "query": "energy conservation requirements oil gas",
        "relevant_docs": ["directive-056"],
    },
    {
        "query": "measurement requirements oil gas operations",
        "relevant_docs": ["directive-083"],
    },
    {
        "query": "emergency response plan notification",
        "relevant_docs": ["directive-071"],
    },
    {
        "query": "flare incinerator venting requirements",
        "relevant_docs": ["directive-060", "Directive001"],
    },
    {
        "query": "waste disposal requirements drilling fluids",
        "relevant_docs": ["directive-050", "directive-047"],
    },
]


def reciprocal_rank(results: list[dict], relevant_docs: list[str]) -> float:
    for rank, r in enumerate(results, start=1):
        doc = r.get("document_name", "").lower()
        if any(rel.lower() in doc or doc in rel.lower() for rel in relevant_docs):
            return 1.0 / rank
    return 0.0


def recall_at_k(results: list[dict], relevant_docs: list[str], k: int = 5) -> float:
    top_k = results[:k]
    for r in top_k:
        doc = r.get("document_name", "").lower()
        if any(rel.lower() in doc or doc in rel.lower() for rel in relevant_docs):
            return 1.0
    return 0.0


def ndcg_at_k(results: list[dict], relevant_docs: list[str], k: int = 5) -> float:
    top_k = results[:k]
    dcg = 0.0
    for rank, r in enumerate(top_k, start=1):
        doc = r.get("document_name", "").lower()
        rel = 1.0 if any(rd.lower() in doc or doc in rd.lower() for rd in relevant_docs) else 0.0
        dcg += rel / math.log2(rank + 1)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant_docs), k)))
    return dcg / idcg if idcg > 0 else 0.0


async def run_eval():
    print("Loading models...")
    bi_encoder = SentenceTransformer("all-MiniLM-L6-v2")
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    recall_scores = []
    mrr_scores = []
    ndcg_scores = []

    print(f"\nEvaluating {len(EVAL_QUERIES)} queries...\n")
    print(f"{'Query':<50} {'Recall@5':>10} {'MRR':>8} {'NDCG@5':>8}")
    print("-" * 78)

    for item in EVAL_QUERIES:
        results = await hybrid_search(item["query"], bi_encoder, cross_encoder, top_k=20, top_n=5)
        r5 = recall_at_k(results, item["relevant_docs"], k=5)
        mrr = reciprocal_rank(results, item["relevant_docs"])
        ndcg = ndcg_at_k(results, item["relevant_docs"], k=5)

        recall_scores.append(r5)
        mrr_scores.append(mrr)
        ndcg_scores.append(ndcg)

        label = item["query"][:48] + ".." if len(item["query"]) > 48 else item["query"]
        print(f"{label:<50} {r5:>10.2f} {mrr:>8.2f} {ndcg:>8.2f}")

    print("-" * 78)
    print(f"{'MEAN':<50} {sum(recall_scores)/len(recall_scores):>10.2f} "
          f"{sum(mrr_scores)/len(mrr_scores):>8.2f} "
          f"{sum(ndcg_scores)/len(ndcg_scores):>8.2f}")
    print()


if __name__ == "__main__":
    asyncio.run(run_eval())
