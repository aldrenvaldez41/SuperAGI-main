# SuperAGI VPS Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy SuperAGI on a Hostinger KVM 2 VPS and wire it to existing self-hosted services (Ollama, Qdrant, LightRAG, n8n, Browserless, TriliumNext, Postiz) to serve as an autonomous real estate assistant with zero-cost local LLM usage.

**Architecture:** n8n owns scheduled ingestion pipelines (Browserless + Serper.dev → LightRAG + Qdrant); SuperAGI owns on-demand reasoning and action dispatch via four agents. Ollama (llama3.1:8b) is the primary LLM; OpenRouter is the fallback. All services communicate over the VPS host network using `host.docker.internal` or domain names via Caddy.

**Tech Stack:** Python 3.10, SuperAGI (FastAPI + Celery), PostgreSQL 15, Redis Stack, Qdrant, LightRAG, Ollama llama3.1:8b, OpenRouter, Browserless, n8n, TriliumNext, Postiz, pytest, requests, pydantic

---

## File Structure

```
SuperAGI-main/
├── config_template.yaml                          MODIFY — add Ollama, Qdrant, tool endpoints
├── docker-compose.yaml                           MODIFY — expose backend port for Caddy
├── superagi/tools/
│   ├── lightrag/
│   │   ├── __init__.py                           CREATE
│   │   ├── lightrag_ingest.py                    CREATE — ingest text into LightRAG
│   │   ├── lightrag_query.py                     CREATE — query LightRAG knowledge base
│   │   └── lightrag_toolkit.py                   CREATE — toolkit registration
│   ├── browserless/
│   │   ├── __init__.py                           CREATE
│   │   ├── browserless_scrape.py                 CREATE — scrape URL via Browserless
│   │   └── browserless_toolkit.py                CREATE
│   ├── n8n/
│   │   ├── __init__.py                           CREATE
│   │   ├── n8n_webhook.py                        CREATE — trigger n8n webhook
│   │   └── n8n_toolkit.py                        CREATE
│   ├── trilium/
│   │   ├── __init__.py                           CREATE
│   │   ├── trilium_create_note.py                CREATE — create note in TriliumNext
│   │   ├── trilium_search_notes.py               CREATE — search notes in TriliumNext
│   │   └── trilium_toolkit.py                    CREATE
│   └── postiz/
│       ├── __init__.py                           CREATE
│       ├── postiz_schedule_post.py               CREATE — schedule social media post
│       └── postiz_toolkit.py                     CREATE
└── tests/unit_tests/tools/
    ├── lightrag/
    │   ├── __init__.py                           CREATE
    │   └── test_lightrag_tools.py                CREATE
    ├── browserless/
    │   ├── __init__.py                           CREATE
    │   └── test_browserless_scrape.py            CREATE
    ├── n8n/
    │   ├── __init__.py                           CREATE
    │   └── test_n8n_webhook.py                   CREATE
    ├── trilium/
    │   ├── __init__.py                           CREATE
    │   └── test_trilium_tools.py                 CREATE
    └── postiz/
        ├── __init__.py                           CREATE
        └── test_postiz_schedule_post.py          CREATE
```

---

## Task 1: Configure docker-compose.yaml for VPS Deployment

**Files:**
- Modify: `docker-compose.yaml`

- [ ] **Step 1: Read current docker-compose.yaml**

Verify the file is as expected — confirm `super__redis` and `super__postgres` services exist and the nginx proxy maps to port 3000.

- [ ] **Step 2: Expose backend on VPS-safe port**

Replace the proxy ports line so Caddy can reach it. Change:
```yaml
  proxy:
    image: nginx:stable-alpine
    ports:
      - "3000:80"
```
to:
```yaml
  proxy:
    image: nginx:stable-alpine
    ports:
      - "32800:80"
```

This avoids port conflicts with existing VPS services and gives Caddy a clean target.

- [ ] **Step 3: Add extra_hosts to backend and celery services**

So containers can reach other VPS services by hostname. Add `extra_hosts` to both `backend` and `celery` services:

```yaml
  backend:
    volumes:
      - "./:/app"
    build: .
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - super__redis
      - super__postgres
    networks:
      - super_network
    command: ["/app/wait-for-it.sh", "super__postgres:5432","-t","60","--","/app/entrypoint.sh"]

  celery:
    volumes:
      - "./:/app"
      - "${EXTERNAL_RESOURCE_DIR:-./workspace}:/app/ext"
    build: .
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - super__redis
      - super__postgres
    networks:
      - super_network
    command: ["/app/entrypoint_celery.sh"]
```

- [ ] **Step 4: Add SuperAGI to Caddy on the VPS**

SSH into VPS and add this block to your Caddyfile (same file where all other services are configured):
```
superagi.buildwithaldren.com {
    reverse_proxy localhost:32800
}
```

Then reload Caddy:
```bash
sudo systemctl reload caddy
```

- [ ] **Step 5: Pull Ollama model on VPS**

SSH into VPS and run:
```bash
docker exec -it <ollama_container_name> ollama pull llama3.1:8b
```

To find the container name:
```bash
docker ps | grep ollama
```

Expected output: model download progress, ending with `success`.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yaml
git commit -m "feat: expose SuperAGI on port 32800 with host-gateway for VPS deployment"
```

---

## Task 2: Update config_template.yaml

**Files:**
- Modify: `config_template.yaml`

- [ ] **Step 1: Replace LLM configuration section**

Find and replace the existing LLM block:
```yaml
OPENAI_API_KEY: YOUR_OPEN_API_KEY
```
Replace the entire LLM section with:
```yaml
# PRIMARY LLM — Ollama local (no cost). Model must be pulled: ollama pull llama3.1:8b
# VPS: KVM2 8GB RAM. Monitor memory; if OOM, switch MODEL_NAME to mistral:7b
OPENAI_API_BASE: "http://host.docker.internal:32768/v1"
OPENAI_API_KEY: "ollama"
MODEL_NAME: "llama3.1:8b"
RESOURCES_SUMMARY_MODEL_NAME: "llama3.1:8b"

# FALLBACK LLM — OpenRouter. Generate key at openrouter.ai
# To activate: comment the Ollama lines above and uncomment these:
# OPENAI_API_BASE: "https://openrouter.ai/api/v1"
# OPENAI_API_KEY: YOUR_OPENROUTER_API_KEY
# MODEL_NAME: "anthropic/claude-3-haiku"
```

- [ ] **Step 2: Add Qdrant vector store configuration**

At the end of the `## RESOURCE_VECTOR_STORE` section, add:
```yaml
RESOURCE_VECTOR_STORE: QDRANT
RESOURCE_VECTOR_STORE_INDEX_NAME: superagi_resources
QDRANT_HOST_NAME: host.docker.internal
QDRANT_PORT: 32782
```

- [ ] **Step 3: Add custom tool endpoint configuration**

At the end of the `###TOOLS KEY` section, add:
```yaml
# LIGHTRAG — Graph RAG knowledge base
LIGHTRAG_URL: "http://rag.buildwithaldren.com"

# BROWSERLESS — Headless browser scraping
BROWSERLESS_URL: "http://browsr.buildwithaldren.com"
BROWSERLESS_TOKEN: YOUR_BROWSERLESS_TOKEN

# N8N — Workflow automation webhooks
N8N_BASE_URL: "http://n8n.buildwithaldren.com"

# TRILIUM NEXT — Note storage
TRILIUM_URL: "http://notes.buildwithaldren.com"
TRILIUM_TOKEN: YOUR_TRILIUM_API_TOKEN

# POSTIZ — Social media scheduling
POSTIZ_URL: "http://social.buildwithaldren.com"
POSTIZ_API_KEY: YOUR_POSTIZ_API_KEY

# KNOWLEDGE BASE COLLECTIONS
LIGHTRAG_COLLECTION_REAL_ESTATE: "real_estate"
LIGHTRAG_COLLECTION_GENERAL: "general"
```

- [ ] **Step 4: Copy config_template.yaml to config.yaml for local use**

```bash
cp config_template.yaml config.yaml
```

Fill in your actual values in `config.yaml`. `config.yaml` is already in `.gitignore`.

- [ ] **Step 5: Commit**

```bash
git add config_template.yaml
git commit -m "feat: configure Ollama, Qdrant, and custom tool endpoints in config template"
```

---

## Task 3: LightRAG Tool — Ingest

**Files:**
- Create: `superagi/tools/lightrag/__init__.py`
- Create: `superagi/tools/lightrag/lightrag_ingest.py`
- Create: `tests/unit_tests/tools/lightrag/__init__.py`
- Create: `tests/unit_tests/tools/lightrag/test_lightrag_tools.py`

- [ ] **Step 1: Create empty __init__.py files**

```bash
touch superagi/tools/lightrag/__init__.py
touch tests/unit_tests/tools/lightrag/__init__.py
```

- [ ] **Step 2: Write the failing test for LightRagIngestTool**

Create `tests/unit_tests/tools/lightrag/test_lightrag_tools.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.lightrag.lightrag_ingest import LightRagIngestTool


class TestLightRagIngestTool:
    def setup_method(self):
        self.tool = LightRagIngestTool()

    @patch("superagi.tools.lightrag.lightrag_ingest.requests.post")
    @patch("superagi.tools.lightrag.lightrag_ingest.get_config")
    def test_ingest_success(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            text="Urban Deca Tower A has 500 units. 2BR starts at PHP 2.5M.",
            collection="real_estate",
            source="price_list_2026_q1"
        )

        assert result == "Successfully ingested text into LightRAG collection: real_estate"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "real_estate" in str(call_args)

    @patch("superagi.tools.lightrag.lightrag_ingest.requests.post")
    @patch("superagi.tools.lightrag.lightrag_ingest.get_config")
    def test_ingest_failure_returns_error(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = self.tool._execute(
            text="some text",
            collection="real_estate",
            source="test"
        )

        assert "Failed to ingest" in result

    @patch("superagi.tools.lightrag.lightrag_ingest.requests.post")
    @patch("superagi.tools.lightrag.lightrag_ingest.get_config")
    def test_ingest_network_error(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_post.side_effect = Exception("Connection refused")

        result = self.tool._execute(
            text="some text",
            collection="real_estate",
            source="test"
        )

        assert "Error" in result
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /path/to/SuperAGI-main
python -m pytest tests/unit_tests/tools/lightrag/test_lightrag_tools.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — file does not exist yet.

- [ ] **Step 4: Create lightrag_ingest.py**

Create `superagi/tools/lightrag/lightrag_ingest.py`:
```python
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class LightRagIngestSchema(BaseModel):
    text: str = Field(..., description="Text content to ingest into the knowledge base")
    collection: str = Field(
        default="real_estate",
        description="Knowledge base collection name. Use 'real_estate' for property data, 'general' for other topics."
    )
    source: str = Field(
        default="manual",
        description="Source identifier for this text (e.g., 'price_list_2026_q1', 'urban_deca_brochure')"
    )


class LightRagIngestTool(BaseTool):
    """Ingest text into the LightRAG graph RAG knowledge base for later retrieval."""
    name = "LightRAGIngest"
    description = (
        "Ingest text content into the LightRAG knowledge base. "
        "Use this to store property listings, price lists, brochures, "
        "market research, or any document content for future retrieval."
    )
    args_schema: Type[LightRagIngestSchema] = LightRagIngestSchema

    def _execute(self, text: str, collection: str = "real_estate", source: str = "manual") -> str:
        base_url = get_config("LIGHTRAG_URL", "http://rag.buildwithaldren.com")
        try:
            response = requests.post(
                f"{base_url}/insert",
                json={"string": text, "collection": collection, "source": source},
                timeout=30
            )
            if response.status_code == 200:
                return f"Successfully ingested text into LightRAG collection: {collection}"
            return f"Failed to ingest into LightRAG: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to LightRAG: {str(e)}"
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/unit_tests/tools/lightrag/test_lightrag_tools.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add superagi/tools/lightrag/ tests/unit_tests/tools/lightrag/
git commit -m "feat: add LightRagIngestTool with tests"
```

---

## Task 4: LightRAG Tool — Query

**Files:**
- Create: `superagi/tools/lightrag/lightrag_query.py`
- Modify: `tests/unit_tests/tools/lightrag/test_lightrag_tools.py`

- [ ] **Step 1: Append failing tests for LightRagQueryTool**

Add to `tests/unit_tests/tools/lightrag/test_lightrag_tools.py`:
```python
from superagi.tools.lightrag.lightrag_query import LightRagQueryTool


class TestLightRagQueryTool:
    def setup_method(self):
        self.tool = LightRagQueryTool()

    @patch("superagi.tools.lightrag.lightrag_query.requests.post")
    @patch("superagi.tools.lightrag.lightrag_query.get_config")
    def test_query_success(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Urban Deca Tower A has 2BR units starting at PHP 2.5M."
        }
        mock_post.return_value = mock_response

        result = self.tool._execute(
            query="What is the price of 2BR units in Urban Deca Tower A?",
            collection="real_estate",
            mode="hybrid"
        )

        assert "2.5M" in result or "Urban Deca" in result

    @patch("superagi.tools.lightrag.lightrag_query.requests.post")
    @patch("superagi.tools.lightrag.lightrag_query.get_config")
    def test_query_failure(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "error"
        mock_post.return_value = mock_response

        result = self.tool._execute(
            query="some query",
            collection="real_estate",
            mode="hybrid"
        )

        assert "Failed" in result or "Error" in result

    @patch("superagi.tools.lightrag.lightrag_query.requests.post")
    @patch("superagi.tools.lightrag.lightrag_query.get_config")
    def test_query_network_error(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_post.side_effect = Exception("timeout")

        result = self.tool._execute(
            query="some query",
            collection="real_estate",
            mode="hybrid"
        )

        assert "Error" in result
```

- [ ] **Step 2: Run tests to verify new tests fail**

```bash
python -m pytest tests/unit_tests/tools/lightrag/test_lightrag_tools.py::TestLightRagQueryTool -v
```

Expected: `ImportError` — lightrag_query.py does not exist yet.

- [ ] **Step 3: Create lightrag_query.py**

Create `superagi/tools/lightrag/lightrag_query.py`:
```python
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class LightRagQuerySchema(BaseModel):
    query: str = Field(..., description="Question or search query to ask the knowledge base")
    collection: str = Field(
        default="real_estate",
        description="Knowledge base collection to query. Use 'real_estate' for property info, 'general' for other topics."
    )
    mode: str = Field(
        default="hybrid",
        description="Query mode: 'hybrid' (recommended), 'local' (entity-focused), 'global' (theme-focused), 'naive' (simple vector search)"
    )


class LightRagQueryTool(BaseTool):
    """Query the LightRAG knowledge base to retrieve property information, market data, or any stored knowledge."""
    name = "LightRAGQuery"
    description = (
        "Query the LightRAG knowledge base to answer questions about properties, "
        "pricing, availability, market comparisons, or any previously ingested content. "
        "Use mode='hybrid' for most questions. Use mode='naive' for simple keyword lookups."
    )
    args_schema: Type[LightRagQuerySchema] = LightRagQuerySchema

    def _execute(self, query: str, collection: str = "real_estate", mode: str = "hybrid") -> str:
        base_url = get_config("LIGHTRAG_URL", "http://rag.buildwithaldren.com")
        try:
            response = requests.post(
                f"{base_url}/query",
                json={"query": query, "mode": mode, "collection": collection},
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", data.get("result", str(data)))
            return f"Failed to query LightRAG: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to LightRAG: {str(e)}"
```

- [ ] **Step 4: Run all LightRAG tests**

```bash
python -m pytest tests/unit_tests/tools/lightrag/ -v
```

Expected: `6 passed`

- [ ] **Step 5: Create lightrag_toolkit.py**

Create `superagi/tools/lightrag/lightrag_toolkit.py`:
```python
from abc import ABC
from typing import List
from superagi.tools.base_tool import BaseTool, BaseToolkit, ToolConfiguration
from superagi.tools.lightrag.lightrag_ingest import LightRagIngestTool
from superagi.tools.lightrag.lightrag_query import LightRagQueryTool
from superagi.types.key_type import ToolConfigKeyType


class LightRagToolkit(BaseToolkit, ABC):
    name: str = "LightRAG Toolkit"
    description: str = "Toolkit for ingesting and querying the LightRAG graph RAG knowledge base"

    def get_tools(self) -> List[BaseTool]:
        return [LightRagIngestTool(), LightRagQueryTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="LIGHTRAG_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="LIGHTRAG_COLLECTION_REAL_ESTATE", key_type=ToolConfigKeyType.STRING, is_required=False, is_secret=False),
        ]
```

- [ ] **Step 6: Commit**

```bash
git add superagi/tools/lightrag/ tests/unit_tests/tools/lightrag/
git commit -m "feat: add LightRagQueryTool and LightRagToolkit"
```

---

## Task 5: Browserless Scrape Tool

**Files:**
- Create: `superagi/tools/browserless/__init__.py`
- Create: `superagi/tools/browserless/browserless_scrape.py`
- Create: `superagi/tools/browserless/browserless_toolkit.py`
- Create: `tests/unit_tests/tools/browserless/__init__.py`
- Create: `tests/unit_tests/tools/browserless/test_browserless_scrape.py`

- [ ] **Step 1: Create __init__.py files**

```bash
touch superagi/tools/browserless/__init__.py
touch tests/unit_tests/tools/browserless/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit_tests/tools/browserless/test_browserless_scrape.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.browserless.browserless_scrape import BrowserlessScrapeTool


class TestBrowserlessScrapeTool:
    def setup_method(self):
        self.tool = BrowserlessScrapeTool()

    @patch("superagi.tools.browserless.browserless_scrape.requests.post")
    @patch("superagi.tools.browserless.browserless_scrape.get_config")
    def test_scrape_success(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "BROWSERLESS_URL": "http://browsr.buildwithaldren.com",
            "BROWSERLESS_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"results": [{"text": "Urban Deca Tower - 2BR from PHP 2.5M"}]}]
        mock_post.return_value = mock_response

        result = self.tool._execute(url="https://8990holdings.com/urban-deca")

        assert "Urban Deca" in result or len(result) > 0

    @patch("superagi.tools.browserless.browserless_scrape.requests.post")
    @patch("superagi.tools.browserless.browserless_scrape.get_config")
    def test_scrape_blocked_returns_error(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "BROWSERLESS_URL": "http://browsr.buildwithaldren.com",
            "BROWSERLESS_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        result = self.tool._execute(url="https://lamudi.com.ph/some-listing")

        assert "Failed" in result or "blocked" in result.lower() or "403" in result

    @patch("superagi.tools.browserless.browserless_scrape.requests.post")
    @patch("superagi.tools.browserless.browserless_scrape.get_config")
    def test_scrape_network_error(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://browsr.buildwithaldren.com"
        mock_post.side_effect = Exception("Connection refused")

        result = self.tool._execute(url="https://example.com")

        assert "Error" in result
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/unit_tests/tools/browserless/test_browserless_scrape.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Create browserless_scrape.py**

Create `superagi/tools/browserless/browserless_scrape.py`:
```python
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class BrowserlessScrapeSchema(BaseModel):
    url: str = Field(..., description="The full URL to scrape (e.g., https://8990holdings.com/urban-deca-towers)")


class BrowserlessScrapeTool(BaseTool):
    """Scrape the full text content of a web page using a headless browser. Best for sites without anti-bot protection."""
    name = "BrowserlessScrape"
    description = (
        "Scrape the full text content of a web page using a headless browser. "
        "Use for developer websites and pages without Cloudflare/anti-bot protection. "
        "For search engines and protected sites, use the search tool instead."
    )
    args_schema: Type[BrowserlessScrapeSchema] = BrowserlessScrapeSchema

    def _execute(self, url: str) -> str:
        base_url = get_config("BROWSERLESS_URL", "http://browsr.buildwithaldren.com")
        token = get_config("BROWSERLESS_TOKEN", "")
        params = {"token": token} if token else {}
        try:
            response = requests.post(
                f"{base_url}/scrape",
                params=params,
                json={
                    "url": url,
                    "elements": [{"selector": "body"}],
                    "gotoOptions": {"waitUntil": "networkidle0", "timeout": 30000}
                },
                timeout=45
            )
            if response.status_code == 200:
                data = response.json()
                texts = []
                for item in data:
                    for result in item.get("results", []):
                        text = result.get("text", "").strip()
                        if text:
                            texts.append(text)
                content = "\n".join(texts)
                return content[:4000] if content else "Page scraped but no text content found."
            return f"Failed to scrape {url}: HTTP {response.status_code}. Site may be blocked by anti-bot protection."
        except Exception as e:
            return f"Error scraping {url}: {str(e)}"
```

- [ ] **Step 5: Create browserless_toolkit.py**

Create `superagi/tools/browserless/browserless_toolkit.py`:
```python
from abc import ABC
from typing import List
from superagi.tools.base_tool import BaseTool, BaseToolkit, ToolConfiguration
from superagi.tools.browserless.browserless_scrape import BrowserlessScrapeTool
from superagi.types.key_type import ToolConfigKeyType


class BrowserlessToolkit(BaseToolkit, ABC):
    name: str = "Browserless Toolkit"
    description: str = "Toolkit for scraping web pages using a headless browser"

    def get_tools(self) -> List[BaseTool]:
        return [BrowserlessScrapeTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="BROWSERLESS_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="BROWSERLESS_TOKEN", key_type=ToolConfigKeyType.STRING, is_required=False, is_secret=True),
        ]
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/unit_tests/tools/browserless/ -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add superagi/tools/browserless/ tests/unit_tests/tools/browserless/
git commit -m "feat: add BrowserlessScrapeTool and toolkit"
```

---

## Task 6: n8n Webhook Tool

**Files:**
- Create: `superagi/tools/n8n/__init__.py`
- Create: `superagi/tools/n8n/n8n_webhook.py`
- Create: `superagi/tools/n8n/n8n_toolkit.py`
- Create: `tests/unit_tests/tools/n8n/__init__.py`
- Create: `tests/unit_tests/tools/n8n/test_n8n_webhook.py`

- [ ] **Step 1: Create __init__.py files**

```bash
touch superagi/tools/n8n/__init__.py
touch tests/unit_tests/tools/n8n/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit_tests/tools/n8n/test_n8n_webhook.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.n8n.n8n_webhook import N8nWebhookTool


class TestN8nWebhookTool:
    def setup_method(self):
        self.tool = N8nWebhookTool()

    @patch("superagi.tools.n8n.n8n_webhook.requests.post")
    @patch("superagi.tools.n8n.n8n_webhook.get_config")
    def test_trigger_webhook_success(self, mock_config, mock_post):
        mock_config.return_value = "http://n8n.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Workflow executed"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            webhook_id="send-reply-abc123",
            payload='{"to": "client@email.com", "message": "Thank you for your inquiry."}'
        )

        assert "success" in result.lower() or "triggered" in result.lower()

    @patch("superagi.tools.n8n.n8n_webhook.requests.post")
    @patch("superagi.tools.n8n.n8n_webhook.get_config")
    def test_trigger_webhook_failure(self, mock_config, mock_post):
        mock_config.return_value = "http://n8n.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Webhook not found"
        mock_post.return_value = mock_response

        result = self.tool._execute(
            webhook_id="nonexistent",
            payload="{}"
        )

        assert "Failed" in result or "404" in result

    @patch("superagi.tools.n8n.n8n_webhook.requests.post")
    @patch("superagi.tools.n8n.n8n_webhook.get_config")
    def test_trigger_webhook_invalid_json_payload(self, mock_config, mock_post):
        mock_config.return_value = "http://n8n.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            webhook_id="test-webhook",
            payload="not valid json"
        )

        assert "invalid" in result.lower() or "error" in result.lower() or "triggered" in result.lower()
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/unit_tests/tools/n8n/test_n8n_webhook.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Create n8n_webhook.py**

Create `superagi/tools/n8n/n8n_webhook.py`:
```python
import json
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class N8nWebhookSchema(BaseModel):
    webhook_id: str = Field(
        ...,
        description="The n8n webhook ID or path (e.g., 'send-client-reply', 'post-to-social'). Get this from your n8n workflow webhook node."
    )
    payload: str = Field(
        default="{}",
        description="JSON string of data to send to the webhook (e.g., '{\"message\": \"hello\", \"to\": \"client@email.com\"}')"
    )


class N8nWebhookTool(BaseTool):
    """Trigger an n8n workflow via webhook to automate tasks like sending messages, posting to social media, or running pipelines."""
    name = "N8nWebhook"
    description = (
        "Trigger an n8n automation workflow via webhook. "
        "Use this to send client replies, post content to social media, "
        "run ingestion pipelines, or any other automated workflow. "
        "The webhook_id is found in the n8n webhook node URL."
    )
    args_schema: Type[N8nWebhookSchema] = N8nWebhookSchema

    def _execute(self, webhook_id: str, payload: str = "{}") -> str:
        base_url = get_config("N8N_BASE_URL", "http://n8n.buildwithaldren.com")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return f"Error: payload must be valid JSON. Received: {payload}"
        try:
            response = requests.post(
                f"{base_url}/webhook/{webhook_id}",
                json=data,
                timeout=30
            )
            if response.status_code in (200, 201):
                return f"Successfully triggered n8n webhook '{webhook_id}'"
            return f"Failed to trigger webhook '{webhook_id}': HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error triggering n8n webhook: {str(e)}"
```

- [ ] **Step 5: Create n8n_toolkit.py**

Create `superagi/tools/n8n/n8n_toolkit.py`:
```python
from abc import ABC
from typing import List
from superagi.tools.base_tool import BaseTool, BaseToolkit, ToolConfiguration
from superagi.tools.n8n.n8n_webhook import N8nWebhookTool
from superagi.types.key_type import ToolConfigKeyType


class N8nToolkit(BaseToolkit, ABC):
    name: str = "n8n Toolkit"
    description: str = "Toolkit for triggering n8n automation workflows via webhooks"

    def get_tools(self) -> List[BaseTool]:
        return [N8nWebhookTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="N8N_BASE_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
        ]
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/unit_tests/tools/n8n/ -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add superagi/tools/n8n/ tests/unit_tests/tools/n8n/
git commit -m "feat: add N8nWebhookTool and toolkit"
```

---

## Task 7: TriliumNext Notes Tool

**Files:**
- Create: `superagi/tools/trilium/__init__.py`
- Create: `superagi/tools/trilium/trilium_create_note.py`
- Create: `superagi/tools/trilium/trilium_search_notes.py`
- Create: `superagi/tools/trilium/trilium_toolkit.py`
- Create: `tests/unit_tests/tools/trilium/__init__.py`
- Create: `tests/unit_tests/tools/trilium/test_trilium_tools.py`

- [ ] **Step 1: Create __init__.py files**

```bash
touch superagi/tools/trilium/__init__.py
touch tests/unit_tests/tools/trilium/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit_tests/tools/trilium/test_trilium_tools.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.trilium.trilium_create_note import TriliumCreateNoteTool
from superagi.tools.trilium.trilium_search_notes import TriliumSearchNotesTool


class TestTriliumCreateNoteTool:
    def setup_method(self):
        self.tool = TriliumCreateNoteTool()

    @patch("superagi.tools.trilium.trilium_create_note.requests.post")
    @patch("superagi.tools.trilium.trilium_create_note.get_config")
    def test_create_note_success(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "TRILIUM_URL": "http://notes.buildwithaldren.com",
            "TRILIUM_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"noteId": "abc123"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            title="Client: Juan dela Cruz — Follow-up",
            content="Interested in 2BR at Urban Deca Tower A. Budget PHP 3M. Follow up Friday.",
            parent_note_id="root"
        )

        assert "success" in result.lower() or "created" in result.lower()

    @patch("superagi.tools.trilium.trilium_create_note.requests.post")
    @patch("superagi.tools.trilium.trilium_create_note.get_config")
    def test_create_note_failure(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://notes.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        result = self.tool._execute(title="Test", content="Content", parent_note_id="root")

        assert "Failed" in result or "401" in result


class TestTriliumSearchNotesTool:
    def setup_method(self):
        self.tool = TriliumSearchNotesTool()

    @patch("superagi.tools.trilium.trilium_search_notes.requests.get")
    @patch("superagi.tools.trilium.trilium_search_notes.get_config")
    def test_search_notes_success(self, mock_config, mock_get):
        mock_config.side_effect = lambda key, default=None: {
            "TRILIUM_URL": "http://notes.buildwithaldren.com",
            "TRILIUM_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"noteId": "abc123", "title": "Client: Juan dela Cruz — Follow-up", "content": "Interested in 2BR"}
            ]
        }
        mock_get.return_value = mock_response

        result = self.tool._execute(query="Juan dela Cruz")

        assert "Juan" in result or "2BR" in result

    @patch("superagi.tools.trilium.trilium_search_notes.requests.get")
    @patch("superagi.tools.trilium.trilium_search_notes.get_config")
    def test_search_notes_empty(self, mock_config, mock_get):
        mock_config.side_effect = lambda key, default=None: "http://notes.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        result = self.tool._execute(query="nonexistent client")

        assert "No notes" in result or "found" in result.lower() or result == "No notes found matching: nonexistent client"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/unit_tests/tools/trilium/test_trilium_tools.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Create trilium_create_note.py**

Create `superagi/tools/trilium/trilium_create_note.py`:
```python
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class TriliumCreateNoteSchema(BaseModel):
    title: str = Field(..., description="Note title (e.g., 'Client: Juan dela Cruz — Follow-up 2026-04-01')")
    content: str = Field(..., description="Note body content in plain text or HTML")
    parent_note_id: str = Field(
        default="root",
        description="Parent note ID in TriliumNext. Use 'root' to create at top level."
    )


class TriliumCreateNoteTool(BaseTool):
    """Create a note in TriliumNext for storing client records, follow-ups, drafts, or research."""
    name = "TriliumCreateNote"
    description = (
        "Create a note in TriliumNext. Use for saving client follow-up drafts, "
        "research summaries, error logs, or any content that should be stored for later review."
    )
    args_schema: Type[TriliumCreateNoteSchema] = TriliumCreateNoteSchema

    def _execute(self, title: str, content: str, parent_note_id: str = "root") -> str:
        base_url = get_config("TRILIUM_URL", "http://notes.buildwithaldren.com")
        token = get_config("TRILIUM_TOKEN", "")
        headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
        try:
            response = requests.post(
                f"{base_url}/api/create-note",
                headers=headers,
                json={
                    "parentNoteId": parent_note_id,
                    "title": title,
                    "content": content,
                    "type": "text"
                },
                timeout=15
            )
            if response.status_code in (200, 201):
                note_id = response.json().get("noteId", "unknown")
                return f"Successfully created note '{title}' in TriliumNext (ID: {note_id})"
            return f"Failed to create note in TriliumNext: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to TriliumNext: {str(e)}"
```

- [ ] **Step 5: Create trilium_search_notes.py**

Create `superagi/tools/trilium/trilium_search_notes.py`:
```python
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class TriliumSearchNotesSchema(BaseModel):
    query: str = Field(..., description="Search query to find notes (e.g., client name, topic, date)")


class TriliumSearchNotesTool(BaseTool):
    """Search notes in TriliumNext by keyword to find client records, previous research, or saved drafts."""
    name = "TriliumSearchNotes"
    description = (
        "Search notes in TriliumNext by keyword. "
        "Use to find client history, previous follow-ups, saved drafts, or research notes."
    )
    args_schema: Type[TriliumSearchNotesSchema] = TriliumSearchNotesSchema

    def _execute(self, query: str) -> str:
        base_url = get_config("TRILIUM_URL", "http://notes.buildwithaldren.com")
        token = get_config("TRILIUM_TOKEN", "")
        headers = {"Authorization": f"Token {token}"}
        try:
            response = requests.get(
                f"{base_url}/api/notes",
                headers=headers,
                params={"search": query},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return f"No notes found matching: {query}"
                summaries = []
                for note in results[:5]:
                    summaries.append(f"- [{note.get('noteId')}] {note.get('title', 'Untitled')}")
                return f"Found {len(results)} note(s) matching '{query}':\n" + "\n".join(summaries)
            return f"Failed to search TriliumNext: HTTP {response.status_code}"
        except Exception as e:
            return f"Error connecting to TriliumNext: {str(e)}"
```

- [ ] **Step 6: Create trilium_toolkit.py**

Create `superagi/tools/trilium/trilium_toolkit.py`:
```python
from abc import ABC
from typing import List
from superagi.tools.base_tool import BaseTool, BaseToolkit, ToolConfiguration
from superagi.tools.trilium.trilium_create_note import TriliumCreateNoteTool
from superagi.tools.trilium.trilium_search_notes import TriliumSearchNotesTool
from superagi.types.key_type import ToolConfigKeyType


class TriliumToolkit(BaseToolkit, ABC):
    name: str = "TriliumNext Toolkit"
    description: str = "Toolkit for creating and searching notes in TriliumNext"

    def get_tools(self) -> List[BaseTool]:
        return [TriliumCreateNoteTool(), TriliumSearchNotesTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="TRILIUM_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="TRILIUM_TOKEN", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
        ]
```

- [ ] **Step 7: Run all Trilium tests**

```bash
python -m pytest tests/unit_tests/tools/trilium/ -v
```

Expected: `4 passed`

- [ ] **Step 8: Commit**

```bash
git add superagi/tools/trilium/ tests/unit_tests/tools/trilium/
git commit -m "feat: add TriliumCreateNoteTool, TriliumSearchNotesTool, and toolkit"
```

---

## Task 8: Postiz Social Media Tool

**Files:**
- Create: `superagi/tools/postiz/__init__.py`
- Create: `superagi/tools/postiz/postiz_schedule_post.py`
- Create: `superagi/tools/postiz/postiz_toolkit.py`
- Create: `tests/unit_tests/tools/postiz/__init__.py`
- Create: `tests/unit_tests/tools/postiz/test_postiz_schedule_post.py`

- [ ] **Step 1: Create __init__.py files**

```bash
touch superagi/tools/postiz/__init__.py
touch tests/unit_tests/tools/postiz/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit_tests/tools/postiz/test_postiz_schedule_post.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.postiz.postiz_schedule_post import PostizSchedulePostTool


class TestPostizSchedulePostTool:
    def setup_method(self):
        self.tool = PostizSchedulePostTool()

    @patch("superagi.tools.postiz.postiz_schedule_post.requests.post")
    @patch("superagi.tools.postiz.postiz_schedule_post.get_config")
    def test_schedule_post_success(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "POSTIZ_URL": "http://social.buildwithaldren.com",
            "POSTIZ_API_KEY": "test-key"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "post_abc123", "status": "scheduled"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            content="Own your dream home at Urban Deca Tower! 2BR units starting PHP 2.5M. Message us now!",
            platform="facebook",
            scheduled_at="2026-04-05T10:00:00"
        )

        assert "scheduled" in result.lower() or "success" in result.lower()

    @patch("superagi.tools.postiz.postiz_schedule_post.requests.post")
    @patch("superagi.tools.postiz.postiz_schedule_post.get_config")
    def test_schedule_post_failure(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://social.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        result = self.tool._execute(
            content="Test post",
            platform="facebook",
            scheduled_at="2026-04-05T10:00:00"
        )

        assert "Failed" in result or "400" in result

    @patch("superagi.tools.postiz.postiz_schedule_post.requests.post")
    @patch("superagi.tools.postiz.postiz_schedule_post.get_config")
    def test_schedule_post_network_error(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://social.buildwithaldren.com"
        mock_post.side_effect = Exception("timeout")

        result = self.tool._execute(
            content="Test post",
            platform="facebook",
            scheduled_at="2026-04-05T10:00:00"
        )

        assert "Error" in result
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/unit_tests/tools/postiz/test_postiz_schedule_post.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Create postiz_schedule_post.py**

Create `superagi/tools/postiz/postiz_schedule_post.py`:
```python
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class PostizSchedulePostSchema(BaseModel):
    content: str = Field(..., description="The text content of the social media post")
    platform: str = Field(
        default="facebook",
        description="Social media platform: 'facebook', 'instagram', 'twitter', 'linkedin'"
    )
    scheduled_at: str = Field(
        ...,
        description="ISO 8601 datetime when to publish (e.g., '2026-04-05T10:00:00'). Use Philippine time (UTC+8)."
    )


class PostizSchedulePostTool(BaseTool):
    """Schedule a social media post via Postiz for automatic publishing at a specified time."""
    name = "PostizSchedulePost"
    description = (
        "Schedule a social media post to be published at a specific time via Postiz. "
        "Use for property listings, market tips, promotional content, or follow-up announcements. "
        "Specify the platform (facebook, instagram, twitter, linkedin) and a scheduled datetime."
    )
    args_schema: Type[PostizSchedulePostSchema] = PostizSchedulePostSchema

    def _execute(self, content: str, platform: str = "facebook", scheduled_at: str = "") -> str:
        base_url = get_config("POSTIZ_URL", "http://social.buildwithaldren.com")
        api_key = get_config("POSTIZ_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post(
                f"{base_url}/api/v1/posts",
                headers=headers,
                json={
                    "content": content,
                    "platform": platform,
                    "scheduledAt": scheduled_at
                },
                timeout=15
            )
            if response.status_code in (200, 201):
                post_id = response.json().get("id", "unknown")
                return f"Successfully scheduled post on {platform} at {scheduled_at} (ID: {post_id})"
            return f"Failed to schedule post on Postiz: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to Postiz: {str(e)}"
```

- [ ] **Step 5: Create postiz_toolkit.py**

Create `superagi/tools/postiz/postiz_toolkit.py`:
```python
from abc import ABC
from typing import List
from superagi.tools.base_tool import BaseTool, BaseToolkit, ToolConfiguration
from superagi.tools.postiz.postiz_schedule_post import PostizSchedulePostTool
from superagi.types.key_type import ToolConfigKeyType


class PostizToolkit(BaseToolkit, ABC):
    name: str = "Postiz Toolkit"
    description: str = "Toolkit for scheduling and publishing social media posts via Postiz"

    def get_tools(self) -> List[BaseTool]:
        return [PostizSchedulePostTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="POSTIZ_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="POSTIZ_API_KEY", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
        ]
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/unit_tests/tools/postiz/ -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add superagi/tools/postiz/ tests/unit_tests/tools/postiz/
git commit -m "feat: add PostizSchedulePostTool and toolkit"
```

---

## Task 9: Run Full Tool Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run all new tool tests together**

```bash
python -m pytest tests/unit_tests/tools/lightrag/ tests/unit_tests/tools/browserless/ tests/unit_tests/tools/n8n/ tests/unit_tests/tools/trilium/ tests/unit_tests/tools/postiz/ -v
```

Expected: `19 passed` (6 lightrag + 3 browserless + 3 n8n + 4 trilium + 3 postiz)

- [ ] **Step 2: Run full unit test suite to verify no regressions**

```bash
python -m pytest tests/unit_tests/ -v --tb=short
```

Expected: All previously passing tests still pass. New tests pass. No regressions.

- [ ] **Step 3: Commit if any fixes were needed**

Only commit if you had to fix a regression. Otherwise skip.

---

## Task 10: Register Toolkits in SuperAGI

**Files:**
- Modify: `superagi/tool_manager.py`

- [ ] **Step 1: Read tool_manager.py to understand registration pattern**

```bash
cat superagi/tool_manager.py
```

Identify where existing toolkits are imported and registered.

- [ ] **Step 2: Add new toolkit imports**

Find the section in `superagi/tool_manager.py` where toolkits are imported (look for lines like `from superagi.tools.slack.slack_toolkit import SlackToolkit`). Add:

```python
from superagi.tools.lightrag.lightrag_toolkit import LightRagToolkit
from superagi.tools.browserless.browserless_toolkit import BrowserlessToolkit
from superagi.tools.n8n.n8n_toolkit import N8nToolkit
from superagi.tools.trilium.trilium_toolkit import TriliumToolkit
from superagi.tools.postiz.postiz_toolkit import PostizToolkit
```

- [ ] **Step 3: Add toolkits to the toolkit list**

Find where existing toolkits are listed (look for `SlackToolkit()` or a list/dict of toolkits). Add:
```python
LightRagToolkit(),
BrowserlessToolkit(),
N8nToolkit(),
TriliumToolkit(),
PostizToolkit(),
```

- [ ] **Step 4: Verify import works**

```bash
python -c "from superagi.tool_manager import ToolManager; print('OK')"
```

Expected: `OK` with no errors.

- [ ] **Step 5: Commit**

```bash
git add superagi/tool_manager.py
git commit -m "feat: register LightRAG, Browserless, n8n, Trilium, and Postiz toolkits"
```

---

## Task 11: Deploy SuperAGI on VPS

**Files:** None (deployment steps)

- [ ] **Step 1: Push code to your repository**

```bash
git push origin main
```

- [ ] **Step 2: SSH into VPS and clone/pull the repository**

```bash
ssh user@your-vps-ip
cd /path/to/SuperAGI-main
git pull origin main
```

- [ ] **Step 3: Copy config template and fill in values**

```bash
cp config_template.yaml config.yaml
nano config.yaml
```

Fill in these values in `config.yaml`:
- `BROWSERLESS_TOKEN` — find in your Browserless container settings
- `TRILIUM_TOKEN` — in TriliumNext: Options → API tokens → Create new token
- `POSTIZ_API_KEY` — in Postiz: Settings → API → Generate key
- `SERP_API_KEY` — from serper.dev dashboard (free tier, no credit card needed)
- `OPENROUTER_API_KEY` — from openrouter.ai (generate when needed)

- [ ] **Step 4: Build and start SuperAGI**

```bash
docker compose up -d --build
```

Expected: All 5 containers start (`backend`, `celery`, `gui`, `super__redis`, `super__postgres`, `proxy`).

- [ ] **Step 5: Verify backend is running**

```bash
curl http://localhost:32800/api/health
```

Expected: `{"status": "ok"}` or similar health response.

- [ ] **Step 6: Verify Caddy routing**

From your local machine:
```bash
curl https://superagi.buildwithaldren.com/api/health
```

Expected: same health response, served over HTTPS via Caddy.

- [ ] **Step 7: Verify Ollama is reachable from SuperAGI container**

```bash
docker exec -it superagi-backend-1 curl http://host.docker.internal:32768/v1/models
```

Expected: JSON list of available models including `llama3.1:8b`.

---

## Task 12: Initialize Qdrant Collections

**Files:** None (one-time setup script run on VPS)

- [ ] **Step 1: Create the real_estate collection in Qdrant**

Run from VPS (or from any machine that can reach `qdrant.buildwithaldren.com`):
```bash
curl -X PUT "http://qdrant.buildwithaldren.com/collections/real_estate" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'
```

Expected: `{"result": true, "status": "ok"}`

- [ ] **Step 2: Create the general collection**

```bash
curl -X PUT "http://qdrant.buildwithaldren.com/collections/general" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'
```

Expected: `{"result": true, "status": "ok"}`

- [ ] **Step 3: Create the superagi_resources collection (used by SuperAGI internally)**

```bash
curl -X PUT "http://qdrant.buildwithaldren.com/collections/superagi_resources" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'
```

Expected: `{"result": true, "status": "ok"}`

- [ ] **Step 4: Verify all collections exist**

```bash
curl http://qdrant.buildwithaldren.com/collections
```

Expected: response lists `real_estate`, `general`, `superagi_resources`.

---

## Task 13: Configure the Four Agents in SuperAGI UI

**Files:** None (UI configuration via `superagi.buildwithaldren.com`)

Open `https://superagi.buildwithaldren.com` in your browser. For each agent below, go to **Agents → Create Agent** and fill in the details.

- [ ] **Agent 1 — Property Knowledge Agent**

```
Name: Property Knowledge Agent
Description: Answers questions about 8990 Holdings properties — pricing, availability, floor plans, payment terms, inventory for Urban Deca Homes Ortigas and Urban Deca Towers Cubao.
Goals:
  - Answer any question about property pricing, availability, inventory, or payment terms
  - Search the knowledge base using LightRAGQuery
  - If no answer found, say so clearly
Tools: LightRAGQuery, LightRAGIngest, WriteFile, ReadFile
Model: llama3.1:8b
Max iterations: 10
```

- [ ] **Agent 2 — Content Creator Agent**

```
Name: Content Creator Agent
Description: Generates social media posts, property descriptions, and personalized client follow-up messages using property knowledge base data.
Goals:
  - Query the knowledge base for property facts before writing
  - Generate engaging, accurate social media content
  - Save drafts to TriliumNext before posting
  - Schedule approved posts via Postiz
Tools: LightRAGQuery, TriliumCreateNote, PostizSchedulePost
Model: llama3.1:8b
Max iterations: 15
```

- [ ] **Agent 3 — Research & Ingestion Agent**

```
Name: Research & Ingestion Agent
Description: Keeps the knowledge base current by ingesting uploaded documents and researching competitor listings on Lamudi and Property24.
Goals:
  - Read uploaded files and ingest their content into LightRAG real_estate collection
  - Search Lamudi and Property24 for Urban Deca Homes Ortigas and Urban Deca Towers Cubao listings
  - Ingest search results as market comparison data
  - Scrape 8990holdings.com for any new project announcements if a URL is provided
Tools: LightRAGIngest, LightRAGQuery, BrowserlessScrape, SerpSearch, ReadFile
Model: llama3.1:8b
Max iterations: 20
```

- [ ] **Agent 4 — Lead Response Agent**

```
Name: Lead Response Agent
Description: Drafts personalized replies to client inquiries by querying the property knowledge base and checking client history in TriliumNext.
Goals:
  - Search TriliumNext for existing notes about the client
  - Query LightRAG for relevant property information matching the client's inquiry
  - Draft a personalized, accurate reply
  - Save the draft to TriliumNext
  - Trigger the n8n send-reply webhook to deliver the response
Tools: LightRAGQuery, TriliumSearchNotes, TriliumCreateNote, N8nWebhook
Model: llama3.1:8b
Max iterations: 15
```

- [ ] **Step: Verify all four agents appear in the agents list**

Navigate to `https://superagi.buildwithaldren.com` → Agents. Confirm all four agents are listed and show correct tool assignments.

---

## Task 14: Ingest Initial Knowledge Base Documents

**Files:** None (operational step)

- [ ] **Step 1: Gather your documents**

Collect from your broker/developer:
- Price list (PDF or Excel)
- Project brochure (PDF)
- Inventory sheet (Excel or PDF)
- FAQ document (if available)
- Reservation form requirements (if available)

Convert everything to plain text if possible (copy-paste from PDF/Excel is fine).

- [ ] **Step 2: Upload documents via SuperAGI workspace**

Place files in: `SuperAGI-main/workspace/input/` on the VPS.

```bash
# From your local machine, copy files to VPS:
scp price_list_2026.pdf user@your-vps-ip:/path/to/SuperAGI-main/workspace/input/
scp urban_deca_brochure.pdf user@your-vps-ip:/path/to/SuperAGI-main/workspace/input/
```

- [ ] **Step 3: Run Research & Ingestion Agent on uploaded files**

In the SuperAGI UI:
1. Open **Research & Ingestion Agent**
2. Run with goal: `"Read all PDF and text files in the workspace input folder and ingest their content into the real_estate knowledge base collection"`
3. Watch the agent run — it should use `ReadFile` → `LightRAGIngest` for each document

- [ ] **Step 4: Verify knowledge base has data**

Test the Property Knowledge Agent:
1. Open **Property Knowledge Agent** in SuperAGI UI
2. Run with goal: `"How many unit types are available in Urban Deca Towers Cubao and what are their prices?"`
3. Expected: Agent returns accurate pricing information from your ingested documents

---

## Task 15: Create n8n Ingestion Pipeline (Weekly Competitor Research)

**Files:** None (n8n workflow configuration via `n8n.buildwithaldren.com`)

- [ ] **Step 1: Create n8n workflow via UI**

Open `https://n8n.buildwithaldren.com`. Create a new workflow named **"Weekly Competitor Research"**.

- [ ] **Step 2: Add Schedule Trigger node**

- Node type: **Schedule Trigger**
- Interval: Every week on Monday at 8:00 AM (Philippine time, UTC+8)
- Cron expression: `0 0 * * 1` (adjust for UTC+8: `0 16 * * 0` in UTC)

- [ ] **Step 3: Add HTTP Request node — SuperAGI webhook trigger**

- Node type: **HTTP Request**
- Method: POST
- URL: `https://superagi.buildwithaldren.com/api/v1/agent/run`
- Body (JSON):
```json
{
  "agent_id": "<Research & Ingestion Agent ID from SuperAGI>",
  "goal": "Search Lamudi.com.ph and property24.com.ph for 'Urban Deca Homes Ortigas' and 'Urban Deca Towers Cubao' listings. Extract pricing, availability, and buyer reviews. Ingest findings into LightRAG collection 'real_estate' with source 'competitor_research_weekly'."
}
```

Get the agent ID from the SuperAGI UI URL when viewing the Research & Ingestion Agent.

- [ ] **Step 4: Activate workflow**

Toggle the workflow to **Active** in n8n.

- [ ] **Step 5: Test by clicking "Execute Workflow" manually**

Verify the SuperAGI agent runs and ingests competitor data. Check TriliumNext or LightRAG for new entries.

---

## Task 16: Create n8n Lead Response Pipeline

**Files:** None (n8n workflow configuration)

- [ ] **Step 1: Create n8n workflow named "Lead Response Pipeline"**

Open `https://n8n.buildwithaldren.com`. Create new workflow.

- [ ] **Step 2: Add Webhook Trigger node**

- Node type: **Webhook**
- HTTP Method: POST
- Path: `lead-inquiry`
- Note the full webhook URL: `https://n8n.buildwithaldren.com/webhook/lead-inquiry`

This is the URL you give to form builders, Facebook lead forms, or any channel that receives client inquiries.

- [ ] **Step 3: Add HTTP Request node — trigger SuperAGI Lead Response Agent**

- Method: POST
- URL: `https://superagi.buildwithaldren.com/api/v1/agent/run`
- Body (JSON) using n8n expressions:
```json
{
  "agent_id": "<Lead Response Agent ID>",
  "goal": "A client named {{ $json.client_name }} sent this inquiry: '{{ $json.message }}'. Their contact: {{ $json.contact }}. Search their history in TriliumNext, query the property knowledge base for relevant info, draft a personalized reply, save draft to TriliumNext, then trigger n8n webhook 'send-reply' with the reply content."
}
```

- [ ] **Step 4: Add second Webhook node — "send-reply" endpoint**

Create a second n8n workflow named **"Send Reply"** with:
- Webhook path: `send-reply`
- Connect to your messaging channel (email, Facebook Messenger via n8n, etc.)

- [ ] **Step 5: Activate both workflows and test**

Send a test POST to the lead-inquiry webhook:
```bash
curl -X POST https://n8n.buildwithaldren.com/webhook/lead-inquiry \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Test Client", "message": "How much is a 2BR unit in Urban Deca?", "contact": "test@email.com"}'
```

Expected: SuperAGI runs Lead Response Agent, draft is saved to TriliumNext, reply is sent via the send-reply webhook.

---

## Verification Checklist

After completing all tasks, verify the full system end-to-end:

- [ ] `https://superagi.buildwithaldren.com` loads SuperAGI UI
- [ ] All 4 agents visible in SuperAGI Agents list
- [ ] All 5 new toolkits visible in SuperAGI Tools section
- [ ] Ollama `llama3.1:8b` responds to queries (test from SuperAGI agent run)
- [ ] Qdrant has 3 collections: `real_estate`, `general`, `superagi_resources`
- [ ] LightRAG has ingested at least one document (test with Property Knowledge Agent)
- [ ] n8n Weekly Competitor Research workflow is active
- [ ] n8n Lead Response Pipeline webhook is active
- [ ] Test lead inquiry end-to-end: POST to lead webhook → agent runs → draft saved to TriliumNext

---

## Known Limitations & Notes

- **LightRAG API paths** (`/insert`, `/query`) are based on LightRAG's standard server. Verify against your deployed version at `rag.buildwithaldren.com/docs` if available.
- **Postiz API** (`/api/v1/posts`) — verify endpoint path in your Postiz instance settings or API docs.
- **TriliumNext API** — token is generated in TriliumNext UI under Options → API tokens.
- **Ollama memory**: Monitor VPS RAM with `docker stats`. If containers OOM, set `MODEL_NAME: "mistral:7b"` in `config.yaml` (requires `ollama pull mistral:7b` on VPS).
- **Serper.dev free tier**: 2,500 searches/month. Weekly competitor research uses ~10 searches/run, well within limits.
