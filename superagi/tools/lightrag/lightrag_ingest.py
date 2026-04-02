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

    def _get_token(self, base_url: str) -> str:
        username = get_config("LIGHTRAG_USERNAME", "")
        password = get_config("LIGHTRAG_PASSWORD", "")
        response = requests.post(
            f"{base_url}/login",
            data={"username": username, "password": password},
            timeout=10
        )
        return response.json().get("access_token", "")

    def _execute(self, text: str, collection: str = "real_estate", source: str = "manual") -> str:
        base_url = get_config("LIGHTRAG_URL", "http://rag.buildwithaldren.com")
        try:
            token = self._get_token(base_url)
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{base_url}/documents/text",
                json={"text": text, "collection": collection, "source": source},
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                return f"Successfully ingested text into LightRAG collection: {collection}"
            return f"Failed to ingest into LightRAG: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to LightRAG: {str(e)}"
