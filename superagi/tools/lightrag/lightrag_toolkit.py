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
