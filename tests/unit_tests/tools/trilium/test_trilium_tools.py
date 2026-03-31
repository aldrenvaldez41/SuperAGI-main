import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.trilium.trilium_create_note import TriliumCreateNoteTool
from superagi.tools.trilium.trilium_search_notes import TriliumSearchNotesTool


class TestTriliumCreateNoteTool:
    def setup_method(self):
        self.tool = TriliumCreateNoteTool()

    @patch("superagi.tools.trilium.trilium_create_note.requests.post")
    @patch("superagi.tools.trilium.trilium_create_note.get_config")
    def test_create_note_success(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "TRILIUM_URL": "http://notes.buildwithaldren.com",
            "TRILIUM_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"noteId": "abc123"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            title="Client: Juan dela Cruz — Follow-up",
            content="Interested in 2BR at Urban Deca Tower A. Budget PHP 3M.",
            parent_note_id="root"
        )

        assert "success" in result.lower() or "created" in result.lower()

    @patch("superagi.tools.trilium.trilium_create_note.requests.post")
    @patch("superagi.tools.trilium.trilium_create_note.get_config")
    def test_create_note_failure(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://notes.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        result = self.tool._execute(title="Test", content="Content", parent_note_id="root")

        assert "Failed" in result or "401" in result


class TestTriliumSearchNotesTool:
    def setup_method(self):
        self.tool = TriliumSearchNotesTool()

    @patch("superagi.tools.trilium.trilium_search_notes.requests.get")
    @patch("superagi.tools.trilium.trilium_search_notes.get_config")
    def test_search_notes_success(self, mock_config, mock_get):
        mock_config.side_effect = lambda key, default=None: {
            "TRILIUM_URL": "http://notes.buildwithaldren.com",
            "TRILIUM_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"noteId": "abc123", "title": "Client: Juan dela Cruz — Follow-up"}]
        }
        mock_get.return_value = mock_response

        result = self.tool._execute(query="Juan dela Cruz")

        assert "Juan" in result or "found" in result.lower()

    @patch("superagi.tools.trilium.trilium_search_notes.requests.get")
    @patch("superagi.tools.trilium.trilium_search_notes.get_config")
    def test_search_notes_empty(self, mock_config, mock_get):
        mock_config.side_effect = lambda key, default=None: "http://notes.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        result = self.tool._execute(query="nonexistent client")

        assert result == "No notes found matching: nonexistent client"
