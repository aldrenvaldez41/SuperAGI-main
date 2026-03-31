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
