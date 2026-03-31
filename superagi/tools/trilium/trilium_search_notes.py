from typing import Type
import requests
from pydantic import Field, BaseModel
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class TriliumSearchNotesSchema(BaseModel):
    query: str = Field(..., description="Search query to find notes (e.g., client name, topic, date)")


class TriliumSearchNotesTool(BaseTool):
    """Search notes in TriliumNext by keyword to find client records, previous research, or saved drafts."""
    name = "TriliumSearchNotes"
    description = (
        "Search notes in TriliumNext by keyword. "
        "Use to find client history, previous follow-ups, saved drafts, or research notes."
    )
    args_schema: Type[TriliumSearchNotesSchema] = TriliumSearchNotesSchema

    def _execute(self, query: str) -> str:
        base_url = get_config("TRILIUM_URL", "http://notes.buildwithaldren.com")
        token = get_config("TRILIUM_TOKEN", "")
        headers = {"Authorization": f"Token {token}"}
        try:
            response = requests.get(
                f"{base_url}/api/notes",
                headers=headers,
                params={"search": query},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return f"No notes found matching: {query}"
                summaries = []
                for note in results[:5]:
                    summaries.append(f"- [{note.get('noteId')}] {note.get('title', 'Untitled')}")
                return f"Found {len(results)} note(s) matching '{query}':\n" + "\n".join(summaries)
            return f"Failed to search TriliumNext: HTTP {response.status_code}"
        except Exception as e:
            return f"Error connecting to TriliumNext: {str(e)}"
