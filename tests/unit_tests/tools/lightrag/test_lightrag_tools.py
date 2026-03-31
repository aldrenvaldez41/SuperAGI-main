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


from superagi.tools.lightrag.lightrag_query import LightRagQueryTool


class TestLightRagQueryTool:
    def setup_method(self):
        self.tool = LightRagQueryTool()

    @patch("superagi.tools.lightrag.lightrag_query.requests.post")
    @patch("superagi.tools.lightrag.lightrag_query.get_config")
    def test_query_success(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Urban Deca Tower A has 2BR units starting at PHP 2.5M."
        }
        mock_post.return_value = mock_response

        result = self.tool._execute(
            query="What is the price of 2BR units in Urban Deca Tower A?",
            collection="real_estate",
            mode="hybrid"
        )

        assert "2.5M" in result or "Urban Deca" in result

    @patch("superagi.tools.lightrag.lightrag_query.requests.post")
    @patch("superagi.tools.lightrag.lightrag_query.get_config")
    def test_query_failure(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "error"
        mock_post.return_value = mock_response

        result = self.tool._execute(query="some query", collection="real_estate", mode="hybrid")

        assert "Failed" in result or "Error" in result

    @patch("superagi.tools.lightrag.lightrag_query.requests.post")
    @patch("superagi.tools.lightrag.lightrag_query.get_config")
    def test_query_network_error(self, mock_config, mock_post):
        mock_config.return_value = "http://rag.buildwithaldren.com"
        mock_post.side_effect = Exception("timeout")

        result = self.tool._execute(query="some query", collection="real_estate", mode="hybrid")

        assert "Error" in result
