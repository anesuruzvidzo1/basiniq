# BasinIQ Pitch Guide

Practice talking about this out loud. Every section is written as speech, not prose.
Read it, then close it and say it in your own words. That is the drill.


## The simplest version (anyone, 20 seconds)

"It is a question answering system for Alberta's energy industry. You type a question in plain English, it searches AER regulatory directives and a well license database, and gives you an answer with the exact page it came from. So instead of spending 30 minutes searching through a 90-page directive, you ask and get the relevant section in 10 seconds with the citation."

If they ask what makes it different from ChatGPT: "ChatGPT makes up answers. BasinIQ only answers from the documents and database it has access to, and it shows you the source so you can verify it yourself. No hallucinations without a citation."


## What it is NOT (handle this early)

Not ChatGPT. ChatGPT generates from its training data. BasinIQ retrieves from specific documents and a specific database. The model cannot state a well count without running a real SQL query. It cannot cite a directive without finding the actual text. If it does not find something, it says so.

Not a search engine. A search engine gives you a list of documents to read. BasinIQ reads them and synthesizes the answer, then tells you where to go verify it.

Not a general assistant. It knows AER directives and Alberta well data. That is its domain. The specificity is a feature, not a limitation.


## CTO

What a CTO is really asking: do you actually understand what you built, or did you follow a tutorial?

**Open with the architecture, not the features:**

"BasinIQ is a hybrid retrieval system over two data sources. Eight AER regulatory directives chunked and indexed with pgvector for dense semantic search, and a PostgreSQL well license database. The AI layer is a Claude tool use loop with two tools: one that generates and runs parameterized SQL against the well data, and one that runs document retrieval. The model decides which tool to call based on the question, and can call both in sequence for compound queries."

**Go deeper when they lean in:**

"Retrieval is BM25 plus pgvector dense search running in parallel, merged via Reciprocal Rank Fusion, then reranked by a cross encoder. The cross encoder is what actually moves precision. It re-scores each retrieved chunk against the full query as a pair, not just embedding proximity. That is the step most tutorials skip and the one that matters most in production."

**Drop the production lesson when it feels right:**

"I built it with Elasticsearch for BM25. It crashed on Railway on first deploy, exit code 137, out of memory. Elasticsearch 8 needs around 1GB just for startup. Rather than work around it, I made BM25 fail gracefully and ran vector only in production. Accuracy held. The reason: AER regulatory text is precise by design. Terms like emergency planning zone and measurement methodology appear consistently across all 392 chunks. BM25 matters most when documents use different words for the same concept. In a technical corpus written to be unambiguous, vector search with a good reranker covers most of it."

**The takeaway they will remember:**

"The lesson was: match retrieval complexity to your corpus. The reranker is almost always worth adding. The second index depends on how variable your vocabulary is."

**Likely objection: "Why not LangChain?"**

"I built directly on the Anthropic SDK with raw tool use. LangChain abstracts over things I need to control: the exact prompt structure, how tool results get passed back, how many rounds happen. With raw tool use I can see exactly what the model is doing at every step. It is also simpler to instrument for observability, which matters in production."

**Likely objection: "How does it handle hallucinations?"**

"Every factual claim in the answer is grounded in a tool result. The model cannot state a well count without calling the SQL tool and receiving a real database response. Regulatory claims come with directive name and page number from the retrieval step. If nothing relevant is found, the model says so rather than generating from its training data."

**Likely objection: "How would this scale to real company data?"**

"The architecture is the same regardless of data size. You swap the AER PDFs for internal documents, the synthetic well data for the company's EDI or production database. The retrieval pipeline, tool use loop, and session management all stay the same. The main consideration at scale is the embedding pipeline for ingesting new documents and keeping the vector index current."


## CEO

What a CEO is really asking: what is the business case, can I trust the output, and what does it cost?

**Open with the time and liability problem:**

"In a regulated industry like upstream energy, your engineers spend a significant amount of time looking up what the rules say. Someone needs to check what Directive 071 requires before signing off on an emergency response plan. Someone needs to verify the noise measurement methodology before submitting a compliance report. BasinIQ gets them to the exact page in 10 seconds instead of 30 minutes."

**The trust argument (this is what closes for CEOs in regulated industries):**

"The output is not an AI opinion. Every regulatory answer shows the directive name and the page number it came from. The engineer is not trusting the AI. They are trusting the AER's published text, which the AI retrieved for them. That is a meaningful distinction when you are signing off on a compliance submission."

**The compound query argument:**

"The more interesting value is when a question requires both regulatory context and operational data at the same time. A question like 'what are the noise requirements for wells within 1500 metres of residences, and how many of our active Pembina wells are within that distance?' That query needs the directive text and the well database simultaneously. BasinIQ handles that in one question."

**On cost:**

"This is a demonstration system. In a production context the data would be the company's own well portfolio and internal operational documents alongside public AER content. The infrastructure is straightforward: PostgreSQL with a vector extension, a FastAPI backend, a Next.js interface. The main cost driver is API calls to the language model, which for query-response workloads is in the cents per query range."


## Energy Sector Contact (Reservoir Engineer, Compliance Officer, EHS Manager)

These are end users. They care whether it saves them time on a specific task they do every week.

**Reservoir Engineer:**

"You can ask it things like 'how many active Montney wells is Tourmaline operating in the Peace River area' and it runs the query and gives you the count with the underlying data it pulled. Or 'compare gas production volumes between Cenovus and ARC Resources in Pembina last year.' The well data in this demo is synthetic, but the architecture scales to a live EDI feed or AER production data."

**Compliance Officer:**

"The strongest use case for your work is the regulatory question answering. You ask 'what are the emergency planning requirements for a facility with H2S release potential above 0.1 cubic metres per second' and it returns the relevant Directive 071 sections with exact page citations. You still read and verify it yourself. The AI is not making the compliance decision. But it gets you to the right section immediately instead of manually searching through the directive."

**EHS Manager:**

"Directive 050 on drilling waste management and Directive 071 on emergency response are both indexed. You can ask cross-directive questions like 'what notification timelines apply to a spill event within 100 metres of a water body' and it will pull from whichever directives are relevant and cite the pages."

**Objection: "Our team already knows this material."**

"Yes, and they spend time looking it up anyway. This does not replace their expertise. It gives them faster access to the source so they can spend more time on judgment calls and less on document navigation. The engineer who knows Directive 071 well can use this to confirm a section in 5 seconds. The one who is new to a directive can find the relevant portion without reading 90 pages from the top."

**Objection: "How accurate is it?"**

"Every answer is grounded in the retrieved text. If the directive says a specific thing, the system quotes it and tells you the page. If the question is outside the indexed documents, the system says it does not have the information rather than guessing. The risk is not hallucination. The risk is that the relevant section was not retrieved, which is why the citation is always shown. You can verify in 10 seconds."


## Walking Someone Through the Live Demo

When you share your screen or show it on your phone, say this as you go:

Opening the landing page: "This is the landing page. It shows the three main user types this is built for: reservoir engineers, compliance officers, and EHS managers. You can see the data that is indexed here. Let me open the chat."

Starting a regulatory question: "I will start with a regulatory question. Ask something like: what are the noise control requirements for well sites within 300 metres of a residence." Wait for the answer. "You can see it pulled from Directive 038 on noise control, and it is citing page 12. If you click the citation it shows the source. The page number is real. You can open the actual directive and verify it."

Starting a data question: "Now a data question. Ask: which licensees are operating in the Duvernay formation right now." Wait. "That one hit the well database. You can see it ran a query across the well license data and returned the active licensees. The data is synthetic in this demo, but the query structure is the same as what you would use against a live EDI feed."

Compound question: "Now the interesting one. Ask: what are the measurement requirements for gas production, and how many active gas producers are there in the Foothills formation." Wait. "That question used both tools. It retrieved the measurement requirements from Directive 083 and queried the well database for the Foothills count. That is the part that is hard to do with a simple search tool."


## Recruiter or Hiring Manager

**How to open:**

"BasinIQ is a RAG system I built over AER regulatory directives and Alberta well license data. It is live. You can use it at basiniq-sigma.vercel.app. I can walk you through it."

**What it demonstrates, in plain terms:**

Full stack ownership end to end. I designed the data model, built the retrieval pipeline, wrote the FastAPI backend, handled the PostgreSQL schema with the pgvector extension, built the Next.js frontend, and deployed the whole stack to Railway and Vercel.

Production RAG. Not the tutorial version. Hybrid retrieval with dense search and keyword search, rank fusion, and cross encoder reranking. This is what teams actually use in production when they need precision retrieval, not just approximate nearest neighbors.

Agentic tool use. The AI does not just retrieve. It routes queries, calls SQL tools, calls retrieval tools, handles multi-turn conversation, and synthesizes across multiple tool results. That is the agentic pattern that shows up in every serious AI engineering job description right now.

Domain specificity. I chose the Alberta energy sector deliberately. I am targeting Canadian companies in that space and built a system that demonstrates domain knowledge of their industry, not a generic demo.

**What to say if they ask why energy:**

"I am focused on Canada for immigration reasons. Alberta has the largest concentration of upstream energy companies in Canada and a growing technology adoption curve. Building BasinIQ over AER data means every conversation I have with a company in that sector is grounded. I have something concrete and relevant to show them."

**What to say if they ask to walk through the stack:**

"FastAPI backend with async SQLAlchemy and asyncpg. PostgreSQL with pgvector for vector search, 384-dimensional embeddings using all-MiniLM-L6-v2. Cross encoder reranking with ms-marco-MiniLM-L-6-v2. Claude tool use loop on the Anthropic API. Next.js 16 App Router on the frontend with Tailwind CSS. Deployed on Railway for the backend and Vercel for the frontend."


## One-liner versions

Verbal in a networking conversation: "It is a question answering system for Alberta energy data. You ask a regulatory or well data question and it gives you a cited answer in plain English."

Cold email body: "I built BasinIQ, a RAG system over AER regulatory directives and Alberta well license data that answers regulatory and production questions with page-level citations."

LinkedIn comment or reply: "Hybrid retrieval over AER directives and Alberta well data. BM25 and pgvector merged via Reciprocal Rank Fusion, cross encoder reranking, Claude tool use for routing between SQL and document search."

GitHub bio or project description: "Natural language queries over Alberta Energy Regulator directives and well license data. Hybrid retrieval, cross encoder reranking, Claude agentic tool use."
