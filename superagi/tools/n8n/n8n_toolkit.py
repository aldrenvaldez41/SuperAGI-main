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
