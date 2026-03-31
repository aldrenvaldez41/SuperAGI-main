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
