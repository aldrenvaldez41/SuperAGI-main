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
        username = get_config("LIGHTRAG_USERNAME", "")
        password = get_config("LIGHTRAG_PASSWORD", "")
        auth = (username, password) if username else None
        try:
            response = requests.post(
                f"{base_url}/query",
                json={"query": query, "mode": mode, "collection": collection},
                auth=auth,
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", data.get("result", str(data)))
            return f"Failed to query LightRAG: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to LightRAG: {str(e)}"
