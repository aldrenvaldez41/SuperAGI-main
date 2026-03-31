import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.postiz.postiz_schedule_post import PostizSchedulePostTool


class TestPostizSchedulePostTool:
    def setup_method(self):
        self.tool = PostizSchedulePostTool()

    @patch("superagi.tools.postiz.postiz_schedule_post.requests.post")
    @patch("superagi.tools.postiz.postiz_schedule_post.get_config")
    def test_schedule_post_success(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: {
            "POSTIZ_URL": "http://social.buildwithaldren.com",
            "POSTIZ_API_KEY": "test-key"
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "post_abc123", "status": "scheduled"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            content="Own your dream home at Urban Deca Tower! 2BR units starting PHP 2.5M.",
            platform="facebook",
            scheduled_at="2026-04-05T10:00:00"
        )

        assert "scheduled" in result.lower() or "success" in result.lower()

    @patch("superagi.tools.postiz.postiz_schedule_post.requests.post")
    @patch("superagi.tools.postiz.postiz_schedule_post.get_config")
    def test_schedule_post_failure(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://social.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        result = self.tool._execute(
            content="Test post",
            platform="facebook",
            scheduled_at="2026-04-05T10:00:00"
        )

        assert "Failed" in result or "400" in result

    @patch("superagi.tools.postiz.postiz_schedule_post.requests.post")
    @patch("superagi.tools.postiz.postiz_schedule_post.get_config")
    def test_schedule_post_network_error(self, mock_config, mock_post):
        mock_config.side_effect = lambda key, default=None: "http://social.buildwithaldren.com"
        mock_post.side_effect = Exception("timeout")

        result = self.tool._execute(
            content="Test post",
            platform="facebook",
            scheduled_at="2026-04-05T10:00:00"
        )

        assert "Error" in result
