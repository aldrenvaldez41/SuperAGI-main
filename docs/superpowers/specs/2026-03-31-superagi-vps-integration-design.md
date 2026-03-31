# SuperAGI VPS Integration Design
**Date:** 2026-03-31
**Status:** Approved

---

## Overview

Deploy SuperAGI on a self-hosted VPS (Hostinger) and integrate it with existing self-hosted services to create an autonomous AI assistant for a part-time real estate agent in the Philippines. The system must minimize external API costs by defaulting to local LLMs, only using paid APIs as fallback.

---

## Architecture

**Pattern: Hybrid — n8n ingests, SuperAGI reasons and acts**

```
┌─────────────────────────────────────────────────────────────┐
│                          VPS                                │
│                                                             │
│  ┌──────────┐  scrape (developer site)  ┌───────────────┐  │
│  │   n8n    │ ────────────────────────▶ │  Browserless  │  │
│  │(pipelines│                           └───────────────┘  │
│  │& schedules)  search (competitors)    ┌───────────────┐  │
│  │          │ ────────────────────────▶ │  Serper.dev   │  │
│  │          │                           └───────────────┘  │
│  │          │  parse + ingest                  │            │
│  │          │ ◀────────────────────────────────┘            │
│  │          │ ──────────────────────▶  ┌───────────────┐   │
│  │          │                          │   LightRAG    │   │
│  │          │ ──────────────────────▶  │  (graph RAG)  │   │
│  └──────────┘                          └───────────────┘   │
│       ▲                                ┌───────────────┐   │
│       │ webhook/trigger                │    Qdrant     │   │
│  ┌────┴───────────────────────────────┤  (vector DB)  │   │
│  │            SuperAGI                └───────────────┘   │
│  │   Agents: Query → Reason → Act                          │
│  │   LLM: Ollama (primary) / OpenRouter (fallback)         │
│  └───────────────────┬─────────────────────────────────────┘
│                      │ outputs                              │
│         ┌────────────┼────────────┐                        │
│         ▼            ▼            ▼                        │
│      Postiz     n8n webhook   TriliumNext                  │
│    (social)      (actions)     (notes)                     │
└─────────────────────────────────────────────────────────────┘
```

**Separation of concerns:**
- **n8n** owns all scheduled/triggered ingestion pipelines
- **SuperAGI** owns all on-demand reasoning, querying, and action dispatch
- **LightRAG** is the primary knowledge graph (graph + vector hybrid RAG)
- **Qdrant** handles fast vector lookups as secondary store
- **Ollama** is the primary LLM — free, local, no API costs
- **OpenRouter** is the fallback LLM — used only when Ollama context is too small or task is complex

---

## Service Configuration

### SuperAGI `config_template.yaml` changes

```yaml
# PRIMARY LLM — Ollama (OpenAI-compatible endpoint, no cost)
# Model: llama3.1:8b (user preference). VPS is KVM 2 (8GB RAM) — leaves ~3GB for
# other services. Monitor memory usage; if OOM occurs, fall back to mistral:7b (~4GB).
# Run: ollama pull llama3.1:8b
OPENAI_API_BASE: "http://host.docker.internal:32768/v1"
OPENAI_API_KEY: "ollama"
MODEL_NAME: "llama3.1:8b"
RESOURCES_SUMMARY_MODEL_NAME: "llama3.1:8b"

# FALLBACK LLM — OpenRouter (configured as secondary model in models_config)
# OPENAI_API_BASE: "https://openrouter.ai/api/v1"
# OPENAI_API_KEY: YOUR_OPENROUTER_API_KEY

# DATABASE — SuperAGI's own built-in Postgres container (from its docker-compose)
# No changes needed — use SuperAGI's default docker-compose Postgres

# VECTOR STORE — existing Qdrant instance
RESOURCE_VECTOR_STORE: QDRANT
QDRANT_HOST_NAME: host.docker.internal
QDRANT_PORT: 32782
RESOURCE_VECTOR_STORE_INDEX_NAME: superagi_resources

# REDIS — new container to be added to VPS Docker stack
REDIS_URL: "host.docker.internal:6379"

# STORAGE
STORAGE_TYPE: "FILE"
TOOLS_DIR: "superagi/tools"

# SEARCH (existing SuperAGI tool, just needs key)
SERP_API_KEY: YOUR_SERPER_DEV_API_KEY
```

### Existing VPS services used by SuperAGI

| Service | Domain | Internal Port | Role |
|---|---|---|---|
| Ollama | — | `32768` | Primary LLM |
| Qdrant | `qdrant.buildwithaldren.com` | `32782` | Vector store |
| n8n | `n8n.buildwithaldren.com` | `32781` | Ingestion pipelines + webhook receiver |
| Browserless | `browsr.buildwithaldren.com` | `32783` | Scrape developer's own site |
| LightRAG | `rag.buildwithaldren.com` | `9621` | Graph RAG knowledge base |
| TriliumNext | `notes.buildwithaldren.com` | `32791` | Notes + client records |
| Postiz | `social.buildwithaldren.com` | `32796` | Social media scheduling |

### New services to add to VPS Docker stack

| Service | Purpose |
|---|---|
| `redis` | Required by SuperAGI's Celery task queue |
| `superagi` | Main application |
| `superagi-celery` | Background worker |

SuperAGI's own `docker-compose.yaml` includes Postgres, so no separate Postgres setup is needed.

---

## New SuperAGI Tool Plugins

Six new tool plugins to be created in `superagi/tools/`:

### 1. `lightrag_tool`
- **Purpose:** Ingest documents and query LightRAG's graph RAG API
- **Endpoint:** `http://rag.buildwithaldren.com`
- **Actions:** `ingest(text, metadata)`, `query(prompt)`

### 2. `qdrant_tool`
- **Purpose:** Direct vector similarity search against Qdrant
- **Endpoint:** `http://host.docker.internal:32782`
- **Actions:** `search(query, collection, top_k)`

### 3. `browserless_tool`
- **Purpose:** Scrape full page content from URLs via headless browser
- **Endpoint:** `http://browsr.buildwithaldren.com`
- **Actions:** `scrape(url)` → returns cleaned text
- **Limitation:** Only reliable on sites without anti-bot protection (e.g., developer's own site)

### 4. `n8n_tool`
- **Purpose:** Trigger n8n workflows via webhook
- **Endpoint:** `http://n8n.buildwithaldren.com`
- **Actions:** `trigger_webhook(webhook_id, payload)`

### 5. `trilium_tool`
- **Purpose:** Create and read notes in TriliumNext
- **Endpoint:** `http://notes.buildwithaldren.com`
- **Actions:** `create_note(title, content)`, `search_notes(query)`

### 6. `postiz_tool`
- **Purpose:** Schedule and publish social media posts
- **Endpoint:** `http://social.buildwithaldren.com`
- **Actions:** `schedule_post(content, platform, datetime)`

**Note:** `google_serp_search` tool already exists in SuperAGI — only needs `SERP_API_KEY` configured.

---

## Agent Configuration

### Agent 1 — Property Knowledge Agent
- **Goal:** Answer any question about the developer's properties — pricing, availability, inventory, floor plans, payment terms, requirements
- **Tools:** `lightrag_tool`, `qdrant_tool`, `file_tool`
- **LLM:** Ollama primary → OpenRouter fallback
- **Trigger:** On-demand (manual query)
- **Knowledge sources:** Developer brochures, price lists, inventory sheets, FAQs (ingested as PDFs or text files)

### Agent 2 — Content Creator Agent
- **Goal:** Generate social media posts, property descriptions, and personalized client follow-up messages
- **Tools:** `postiz_tool`, `trilium_tool`, `lightrag_tool`
- **LLM:** Ollama
- **Trigger:** Manual or n8n weekly schedule
- **Output:** Drafts saved to TriliumNext; posts scheduled via Postiz

### Agent 3 — Research & Ingestion Agent
- **Goal:** Keep the knowledge base current and build a market comparison layer from competitor/listing data
- **Tools:** `browserless_tool`, `google_serp_search`, `lightrag_tool`, `qdrant_tool`, `file_tool`
- **LLM:** Ollama
- **Trigger:** n8n scheduled (Sub-A: on file upload, Sub-B: weekly) + manual

**Developer context:** 8990 Holdings — focused projects: Urban Deca Homes Ortigas and Urban Deca Towers Cubao. Official sites have minimal structured data; primary knowledge source is documents shared by the broker (price lists, brochures, inventory sheets, reservation forms).

**Ingestion strategy:**
- **Sub-task A (primary — manual/on-upload):** Agent ingests documents you upload (PDFs, Excel, images of price lists) → parse and store in LightRAG `real_estate` collection + Qdrant. Triggered when new files land in the workspace input folder.
- **Sub-task B (weekly — Lamudi/competitor research):** Serper.dev → search "Urban Deca Homes Ortigas" and "Urban Deca Towers Cubao" on Lamudi, Property24, Facebook groups → extract buyer sentiment, competitor pricing, listing availability → ingest into LightRAG `real_estate` collection
- **Sub-task C (opportunistic):** Browserless → scrape 8990 Holdings or Urban Deca pages if a specific URL is provided — for any press releases or project announcements
- **Fallback chain:** Browserless fails → fall back to Serper.dev for same URL

### Agent 4 — Lead Response Agent
- **Goal:** Draft personalized replies to client inquiries based on their query and property knowledge base
- **Tools:** `lightrag_tool`, `trilium_tool`, `n8n_tool`
- **LLM:** Ollama primary → OpenRouter for complex multi-part queries
- **Trigger:** n8n webhook (incoming message from Facebook/email/form)
- **Output:** Draft reply returned to n8n → sent to client via original channel

---

## Data Flow

### Ingestion Flow (n8n-triggered)
```
n8n schedule
  → [Sub-A] Browserless scrape developer site
  → [Sub-B] Serper.dev search competitor listings
  → parse and clean text
  → POST /insert to LightRAG API
  → upsert embeddings to Qdrant collection
```

### Query Flow (SuperAGI on-demand)
```
User prompt → SuperAGI Agent 1
  → lightrag_tool.query()     (graph reasoning over knowledge base)
  → qdrant_tool.search()      (fast vector lookup for supporting facts)
  → synthesize answer
  → output: text response / save note / trigger n8n / schedule post
```

### Lead Response Flow
```
Incoming client message
  → n8n webhook → SuperAGI Agent 4
  → lightrag_tool.query() (find relevant property info)
  → trilium_tool.search_notes() (find client history if exists)
  → draft personalized reply
  → n8n_tool.trigger_webhook() → n8n sends reply via original channel
```

---

## Error Handling & Fallbacks

| Failure | Fallback |
|---|---|
| Ollama down or context too large | Retry via OpenRouter |
| LightRAG query fails | Fall back to Qdrant vector search |
| Browserless scrape blocked | Fall back to Serper.dev search |
| Postiz unavailable | Save draft to TriliumNext for manual posting |
| n8n webhook unreachable | Log error to TriliumNext note |

---

## Primary Use Cases

1. **Property Q&A** — ask about pricing, availability, inventory, floor plans, payment terms, reservation fees
2. **Inventory tracking** — "How many units are left in Tower 2?"
3. **Client follow-up drafting** — paste client notes → get a personalized follow-up message
4. **Social media content** — weekly batch of property posts auto-scheduled to Postiz
5. **Lead response automation** — incoming client messages answered and replied to automatically
6. **Market research** — weekly competitor comparison report stored in knowledge base

---

## Cost Profile

| Task | Model | Cost |
|---|---|---|
| Property Q&A, drafting, content | Ollama (llama3) | ₱0 |
| Market research ingestion | Ollama + Serper.dev free tier (2,500/mo) | ₱0 |
| Complex contract/legal analysis | OpenRouter (Claude/GPT-4) | ~$0.01–0.05/query |
| Web scraping | Browserless (self-hosted) | ₱0 |

**Target: 90%+ of daily tasks run at zero API cost.**

---

## Multi-Domain Architecture (Future Side Hustles)

The knowledge base and agent configuration are designed for domain separation from day one. Each side hustle gets its own isolated collection in LightRAG and Qdrant, and its own agent set sharing the same tool infrastructure.

```
LightRAG / Qdrant collections:
├── real_estate/          ← 8990 Holdings, Urban Deca Homes Ortigas, Urban Deca Towers Cubao
├── side_hustle_2/        ← future domain (e.g., freelancing, dropshipping, services)
└── general/              ← shared research, market data, general knowledge
```

**Adding a new side hustle = new collection + new agent config (no new code required).** All tool plugins are reusable across domains.

---

## Out of Scope (Phase 1)

- Developer workflow agents (code, GitHub, deployments)
- Calendar/scheduling integration
- ConvertX, Shlink, MaxKB integrations
- Multi-developer/multi-broker support
- Authentication/multi-user setup
- Side hustle domains beyond real estate

These are deferred to future phases once Phase 1 is stable.
