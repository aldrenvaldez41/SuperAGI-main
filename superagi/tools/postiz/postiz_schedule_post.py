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
