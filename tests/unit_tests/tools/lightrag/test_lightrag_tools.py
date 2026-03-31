import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.lightrag.lightrag_ingest import LightRagIngestTool


class TestLightRagIngestTool:
    def setup_method(self):
        self.tool = LightRagIngestTool()

    @patch("superagi.tools.lightrag.lightrag_ingest.requests.post")
    @patch("superagi.tools.lightrag.lightrag_ingest.get_config")
    def test_ingest_success(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            text="Urban Deca Tower A has 500 units. 2BR starts at PHP 2.5M.",
            collection="real_estate",
            source="price_list_2026_q1"
        )

        assert result == "Successfully ingested text into LightRAG collection: real_estate"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "real_estate" in str(call_args)

    @patch("superagi.tools.lightrag.lightrag_ingest.requests.post")
    @patch("superagi.tools.lightrag.lightrag_ingest.get_config")
    def test_ingest_failure_returns_error(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = self.tool._execute(
            text="some text",
            collection="real_estate",
            source="test"
        )

        assert "Failed to ingest" in result

    @patch("superagi.tools.lightrag.lightrag_ingest.requests.post")
    @patch("superagi.tools.lightrag.lightrag_ingest.get_config")
    def test_ingest_network_error(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_post.side_effect = Exception("Connection refused")

        result = self.tool._execute(
            text="some text",
            collection="real_estate",
            source="test"
        )

        assert "Error" in result
