from elasticsearch import AsyncElasticsearch, BadRequestError
import os

INDEX_NAME = "aer_documents"

es = AsyncElasticsearch(os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"))

MAPPINGS = {
    "properties": {
        "document_name": {"type": "keyword"},
        "document_type": {"type": "keyword"},
        "chunk_index": {"type": "integer"},
        "page_number": {"type": "integer"},
        "chunk_text": {"type": "text", "analyzer": "english"},
        "pg_chunk_id": {"type": "integer"},
    }
}


async def init_es():
    try:
        await es.indices.create(index=INDEX_NAME, mappings=MAPPINGS)
        print(f"Created Elasticsearch index: {INDEX_NAME}")
    except BadRequestError as e:
        if "resource_already_exists_exception" in str(e):
            pass
        else:
            raise
    except Exception as e:
        print(f"Elasticsearch unavailable — BM25 disabled, using vector search only: {e}")
