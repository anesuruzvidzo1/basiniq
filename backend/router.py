import os
import anthropic
from sentence_transformers import SentenceTransformer, CrossEncoder
from sqlalchemy import text
from db import AsyncSessionLocal
from retriever import hybrid_search

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SCHEMA_CONTEXT = """
Tables:
  wells: id, license_number, well_name, licensee, formation, field_name,
         well_type, well_status, latitude, longitude, license_date, substance, region
  well_production: id, well_id (FK to wells.id), year, month,
                   oil_volume_m3, gas_volume_e3m3, water_volume_m3

Sample values:
  formation: Montney, Duvernay, Cardium, Viking, Wabamun
  licensee: Cenovus Energy, Tourmaline Oil, ARC Resources, Spartan Delta,
            Headwater Exploration, Baytex Energy, Whitecap Resources, Vermilion Energy
  well_status: Active, Suspended, Abandoned
  well_type: Oil, Gas
  region: Peace River, Pembina, Red Deer, Foothills, Lloydminster
"""

TOOLS = [
    {
        "name": "query_wells",
        "description": (
            "Run a SQL SELECT query against the AER well database. "
            "Use for questions about well counts, production volumes, licensees, "
            "formations, status, or location."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A valid PostgreSQL SELECT query. Only SELECT is permitted.",
                }
            },
            "required": ["sql"],
        },
    },
    {
        "name": "search_documents",
        "description": (
            "Search AER regulatory directives for information about regulations, "
            "requirements, procedures, and compliance rules. "
            "Indexed directives: "
            "Directive 001 (Requirements for Controlling Emissions from Hydrocarbon Flaring), "
            "Directive 038 (Noise Control), "
            "Directive 047 (Oilfield Waste Management Facilities), "
            "Directive 050 (Drilling Waste Management), "
            "Directive 056 (Energy Conservation Requirements), "
            "Directive 060 (Upstream Petroleum Industry Flaring, Incinerating and Venting), "
            "Directive 071 (Emergency Preparedness and Response), "
            "Directive 083 (Measurement Requirements for Oil and Gas Operations)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query for regulatory documents.",
                }
            },
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = f"""You are BasinIQ, an AI assistant for Alberta energy sector data and regulation.

You have access to:
1. query_wells — queries a PostgreSQL database of AER well license and production data
2. search_documents — searches AER regulatory directives using hybrid retrieval

{SCHEMA_CONTEXT}

Guidelines:
- Begin every response with a direct answer in the first sentence. Never start with "Based on", "According to", "Based on the search results", or any similar preamble.
- Use query_wells for quantitative or structured questions about wells and production.
- Use search_documents for questions about regulations, directives, or compliance.
- Use both tools when a question requires both data and regulatory context.
- Generate only SELECT queries. Never mutate data.
- Always cite the directive name and section when referencing document search results.
- Be concise and specific. Ground every claim in tool results.
"""


async def run_sql(sql: str) -> str:
    if not sql.strip().upper().startswith("SELECT"):
        return "Error: only SELECT queries are permitted."
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            if not rows:
                return "Query returned no results."
            lines = [", ".join(columns)]
            for row in rows[:50]:
                lines.append(", ".join(str(v) if v is not None else "NULL" for v in row))
            return "\n".join(lines)
    except Exception as e:
        return f"SQL error: {e}"


async def route_query(
    question: str,
    bi_encoder: SentenceTransformer,
    cross_encoder: CrossEncoder,
    history: list[dict] | None = None,
) -> dict:
    messages = (history or []) + [{"role": "user", "content": question}]
    sources: list[str] = []
    tools_used: set[str] = set()

    while True:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            answer = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "",
            )
            return {"answer": answer, "sources": sources, "tools_used": list(tools_used)}

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "query_wells":
                tools_used.add("sql")
                result_text = await run_sql(block.input["sql"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

            elif block.name == "search_documents":
                tools_used.add("documents")
                chunks = await hybrid_search(
                    block.input["query"], bi_encoder, cross_encoder
                )
                formatted = "\n\n".join(
                    f"[{c['document_name']}, Page {c.get('page_number', 1)}]\n{c['chunk_text']}"
                    for c in chunks
                )
                for c in chunks:
                    citation = f"{c['document_name']}, Page {c.get('page_number', 1)}"
                    if citation not in sources:
                        sources.append(citation)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": formatted or "No relevant documents found.",
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return {"answer": "Unable to process query.", "sources": []}
