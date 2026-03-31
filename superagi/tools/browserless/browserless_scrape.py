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
