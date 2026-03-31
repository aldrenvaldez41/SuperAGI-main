import json
from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class N8nWebhookSchema(BaseModel):
    webhook_id: str = Field(
        ...,
        description="The n8n webhook ID or path (e.g., 'send-client-reply'). Get this from your n8n workflow webhook node."
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
