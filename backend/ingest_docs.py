import asyncio
from pathlib import Path
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from db import AsyncSessionLocal, init_db, DocumentChunk
from es_client import es, init_es, INDEX_NAME

CHUNK_SIZE = 500
OVERLAP = 50


def parse_pdf_with_pages(path: str) -> list[dict]:
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        extracted = page.extract_text()
        if extracted and extracted.strip():
            pages.append({"page": i + 1, "text": extracted})
    return pages


def chunk_text_with_pages(pages: list[dict]) -> list[dict]:
    # build a flat list of (page_number, word) pairs
    word_pages = []
    for p in pages:
        for word in p["text"].split():
            word_pages.append((p["page"], word))

    chunks = []
    i = 0
    while i < len(word_pages):
        slice_ = word_pages[i : i + CHUNK_SIZE]
        text = " ".join(w for _, w in slice_)
        page_num = slice_[0][0] if slice_ else 1
        chunks.append({"page": page_num, "text": text})
        i += CHUNK_SIZE - OVERLAP

    return chunks


async def ingest_pdf(pdf_path: str, model: SentenceTransformer):
    doc_name = Path(pdf_path).stem
    print(f"Processing: {doc_name}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM document_chunks WHERE document_name = :name"),
            {"name": doc_name},
        )
        if result.scalar() > 0:
            print(f"  Already ingested — skipping.")
            return

    pages = parse_pdf_with_pages(pdf_path)
    chunks = chunk_text_with_pages(pages)
    print(f"  {len(chunks)} chunks across {len(pages)} pages. Generating embeddings...")

    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    async with AsyncSessionLocal() as session:
        pg_ids = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = DocumentChunk(
                document_name=doc_name,
                document_type="directive",
                chunk_index=i,
                page_number=chunk["page"],
                chunk_text=chunk["text"],
                embedding=embedding.tolist(),
            )
            session.add(db_chunk)
            await session.flush()
            pg_ids.append((db_chunk.id, chunk["page"]))
        await session.commit()

    for i, (chunk, (pg_id, page_num)) in enumerate(zip(chunks, pg_ids)):
        await es.index(
            index=INDEX_NAME,
            document={
                "document_name": doc_name,
                "document_type": "directive",
                "chunk_index": i,
                "page_number": page_num,
                "chunk_text": chunk["text"],
                "pg_chunk_id": pg_id,
            },
        )

    print(f"  Done. {len(chunks)} chunks stored with page numbers.")


async def main():
    await init_db()
    await init_es()

    model = SentenceTransformer("all-MiniLM-L6-v2")

    pdfs = sorted(Path("/data").glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in /data/.")
        return

    for pdf_path in pdfs:
        await ingest_pdf(str(pdf_path), model)

    print("\nIngestion complete.")


if __name__ == "__main__":
    asyncio.run(main())
