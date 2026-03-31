import pytest
from unittest.mock import patch, MagicMock
from superagi.tools.n8n.n8n_webhook import N8nWebhookTool


class TestN8nWebhookTool:
    def setup_method(self):
        self.tool = N8nWebhookTool()

    @patch("superagi.tools.n8n.n8n_webhook.requests.post")
    @patch("superagi.tools.n8n.n8n_webhook.get_config")
    def test_trigger_webhook_success(self, mock_config, mock_post):
        mock_config.return_value = "http://n8n.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Workflow executed"}
        mock_post.return_value = mock_response

        result = self.tool._execute(
            webhook_id="send-reply-abc123",
            payload='{"to": "client@email.com", "message": "Thank you for your inquiry."}'
        )

        assert "success" in result.lower() or "triggered" in result.lower()

    @patch("superagi.tools.n8n.n8n_webhook.requests.post")
    @patch("superagi.tools.n8n.n8n_webhook.get_config")
    def test_trigger_webhook_failure(self, mock_config, mock_post):
        mock_config.return_value = "http://n8n.buildwithaldren.com"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Webhook not found"
        mock_post.return_value = mock_response

        result = self.tool._execute(webhook_id="nonexistent", payload="{}")

        assert "Failed" in result or "404" in result

    @patch("superagi.tools.n8n.n8n_webhook.requests.post")
    @patch("superagi.tools.n8n.n8n_webhook.get_config")
    def test_trigger_webhook_invalid_json_payload(self, mock_config, mock_post):
        mock_config.return_value = "http://n8n.buildwithaldren.com"

        result = self.tool._execute(webhook_id="test-webhook", payload="not valid json")

        assert "invalid" in result.lower() or "error" in result.lower()
        mock_post.assert_not_called()
