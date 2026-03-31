import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.browserless.browserless_scrape import BrowserlessScrapeTool


class TestBrowserlessScrapeTool:
    def setup_method(self):
        self.tool = BrowserlessScrapeTool()

    @patch("superagi.tools.browserless.browserless_scrape.requests.post")
    @patch("superagi.tools.browserless.browserless_scrape.get_config")
    def test_scrape_success(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "BROWSERLESS_URL": "http://browsr.buildwithaldren.com",
            "BROWSERLESS_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"results": [{"text": "Urban Deca Tower - 2BR from PHP 2.5M"}]}]
        mock_post.return_value = mock_response

        result = self.tool._execute(url="https://8990holdings.com/urban-deca")

        assert len(result) > 0

    @patch("superagi.tools.browserless.browserless_scrape.requests.post")
    @patch("superagi.tools.browserless.browserless_scrape.get_config")
    def test_scrape_blocked_returns_error(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "BROWSERLESS_URL": "http://browsr.buildwithaldren.com",
            "BROWSERLESS_TOKEN": "test-token"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        result = self.tool._execute(url="https://lamudi.com.ph/some-listing")

        assert "Failed" in result or "blocked" in result.lower() or "403" in result

    @patch("superagi.tools.browserless.browserless_scrape.requests.post")
    @patch("superagi.tools.browserless.browserless_scrape.get_config")
    def test_scrape_network_error(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://browsr.buildwithaldren.com"
        mock_post.side_effect = Exception("Connection refused")

        result = self.tool._execute(url="https://example.com")

        assert "Error" in result
