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
