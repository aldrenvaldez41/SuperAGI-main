from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class TriliumCreateNoteSchema(BaseModel):
    title: str = Field(..., description="Note title (e.g., 'Client: Juan dela Cruz — Follow-up 2026-04-01')")
    content: str = Field(..., description="Note body content in plain text or HTML")
    parent_note_id: str = Field(
        default="root",
        description="Parent note ID in TriliumNext. Use 'root' to create at top level."
    )


class TriliumCreateNoteTool(BaseTool):
    """Create a note in TriliumNext for storing client records, follow-ups, drafts, or research."""
    name = "TriliumCreateNote"
    description = (
        "Create a note in TriliumNext. Use for saving client follow-up drafts, "
        "research summaries, error logs, or any content that should be stored for later review."
    )
    args_schema: Type[TriliumCreateNoteSchema] = TriliumCreateNoteSchema

    def _execute(self, title: str, content: str, parent_note_id: str = "root") -> str:
        base_url = get_config("TRILIUM_URL", "http://notes.buildwithaldren.com")
        token = get_config("TRILIUM_TOKEN", "")
        headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
        try:
            response = requests.post(
                f"{base_url}/api/create-note",
                headers=headers,
                json={
                    "parentNoteId": parent_note_id,
                    "title": title,
                    "content": content,
                    "type": "text"
                },
                timeout=15
            )
            if response.status_code in (200, 201):
                note_id = response.json().get("noteId", "unknown")
                return f"Successfully created note '{title}' in TriliumNext (ID: {note_id})"
            return f"Failed to create note in TriliumNext: HTTP {response.status_code} — {response.text}"
        except Exception as e:
            return f"Error connecting to TriliumNext: {str(e)}"
